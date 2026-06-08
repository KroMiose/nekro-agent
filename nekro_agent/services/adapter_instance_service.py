import json
import time
from datetime import datetime, timedelta
from typing import Any

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_adapter_instance import DBAdapterInstance
from nekro_agent.models.db_adapter_instance_event import DBAdapterInstanceEvent
from nekro_agent.models.db_adapter_instance_session import DBAdapterInstanceSession
from nekro_agent.services.system_broadcast import publish_adapter_instance_status

logger = get_sub_logger("adapter_instance")


class AdapterInstanceService:
    """适配器实例服务，管理实例生命周期、状态转换、会话与审计事件。

    设计原则:
    - 所有写入操作均为异步，使用 Tortoise ORM 原生 API
    - 状态变更自动记录审计事件 (DBAdapterInstanceEvent)
    - 支持幂等创建与软删除，审计行永不硬删除
    - 不涉及任何具体适配器协议代码，保持通用性
    """

    # ------------------------------------------------------------------
    # Instance CRUD
    # ------------------------------------------------------------------

    async def create_instance(
        self,
        adapter_key: str,
        instance_key: str,
        display_name: str,
        provider: str,
        metadata: dict[str, Any] | None = None,
    ) -> DBAdapterInstance:
        """幂等创建或更新适配器实例。

        若 (adapter_key, instance_key) 已存在，则更新 display_name、provider
        与 metadata_json，其余字段保持不变；否则新建实例。

        Args:
            adapter_key: 适配器唯一标识
            instance_key: 实例唯一标识
            display_name: 实例显示名称
            provider: 服务提供方
            metadata: 实例元数据字典，序列化为 JSON 字符串存储

        Returns:
            DBAdapterInstance: 创建或更新后的实例对象
        """
        metadata_json: str = json.dumps(metadata, ensure_ascii=False) if metadata else ""

        existing: DBAdapterInstance | None = await DBAdapterInstance.get_or_none(
            adapter_key=adapter_key,
            instance_key=instance_key,
        )

        if existing is not None:
            existing.display_name = display_name
            existing.provider = provider
            existing.metadata_json = metadata_json
            revived = existing.status == "deleted"
            if revived:
                # 复活软删实例：否则该 (adapter_key, instance_key) 将因唯一约束永久占用为 deleted 僵尸
                existing.status = "pending"
                existing.enabled = True
                existing.last_error = ""
            await existing.save()
            if revived:
                await self.record_event(
                    instance=existing,
                    event_type="status_change",
                    status_from="deleted",
                    status_to="pending",
                    message="软删实例被重新创建并复活",
                )
            logger.info(
                f"[AdapterInstanceService] {'复活' if revived else '更新'}实例: adapter={adapter_key}, "
                f"instance={instance_key}, id={existing.id}",
            )
            return existing

        instance: DBAdapterInstance = await DBAdapterInstance.create(
            adapter_key=adapter_key,
            instance_key=instance_key,
            display_name=display_name,
            provider=provider,
            metadata_json=metadata_json,
        )
        logger.info(
            f"[AdapterInstanceService] 创建实例: adapter={adapter_key}, "
            f"instance={instance_key}, id={instance.id}",
        )
        return instance

    async def list_instances(self, adapter_key: str | None = None) -> list[DBAdapterInstance]:
        """获取实例列表。

        Args:
            adapter_key: 可选，按适配器键筛选

        Returns:
            list[DBAdapterInstance]: 实例列表
        """
        query = DBAdapterInstance.all()
        if adapter_key is not None:
            query = query.filter(adapter_key=adapter_key)
        return await query

    async def get_instance(self, adapter_key: str, instance_key: str) -> DBAdapterInstance | None:
        """获取单个适配器实例。

        Args:
            adapter_key: 适配器唯一标识
            instance_key: 实例唯一标识

        Returns:
            DBAdapterInstance | None: 实例对象，若不存在则返回 None
        """
        return await DBAdapterInstance.get_or_none(
            adapter_key=adapter_key,
            instance_key=instance_key,
        )

    # ------------------------------------------------------------------
    # Status & Session State
    # ------------------------------------------------------------------

    async def set_status(
        self,
        instance: DBAdapterInstance,
        new_status: str,
        message: str = "",
        payload: dict[str, Any] | None = None,
    ) -> DBAdapterInstance:
        """设置实例主生命周期状态并记录审计事件。

        Args:
            instance: 目标实例对象
            new_status: 新状态值
            message: 状态变更说明
            payload: 附加载荷字典，序列化为 JSON 字符串存储

        Returns:
            DBAdapterInstance: 更新后的实例对象
        """
        old_status: str = instance.status
        instance.status = new_status
        instance.last_error = message if new_status in ("error", "deleted") else ""
        await instance.save()

        await self.record_event(
            instance=instance,
            event_type="status_change",
            status_from=old_status,
            status_to=new_status,
            message=message,
            payload_json=json.dumps(payload, ensure_ascii=False) if payload else "",
        )

        await publish_adapter_instance_status(
            adapter_key=instance.adapter_key,
            instance_key=instance.instance_key,
            status=new_status,
            previous_status=old_status,
            message=message,
            last_error=instance.last_error,
            updated_at=int(time.time() * 1000),
        )

        logger.info(
            f"[AdapterInstanceService] 实例状态变更: id={instance.id}, "
            f"{old_status} -> {new_status}",
        )
        return instance

    async def set_session_state(
        self,
        instance: DBAdapterInstance,
        session_state: str,
        payload: dict[str, Any] | None = None,
    ) -> DBAdapterInstanceSession:
        """设置实例会话子状态（如 bind_status）。

        若实例尚无关联会话，则自动创建一条空会话记录。

        Args:
            instance: 目标实例对象
            session_state: 会话子状态值
            payload: 附加同步状态字典，覆盖 sync_state_json

        Returns:
            DBAdapterInstanceSession: 更新后的会话对象
        """
        session: DBAdapterInstanceSession | None = await DBAdapterInstanceSession.get_or_none(
            instance_id=instance.id,
        )

        sync_state_json: str = json.dumps(payload, ensure_ascii=False) if payload else ""

        if session is None:
            created = await DBAdapterInstanceSession.create(
                instance_id=instance.id,
                session_state=session_state,
                sync_state_json=sync_state_json,
            )
            logger.info(
                f"[AdapterInstanceService] 会话状态创建: instance_id={instance.id}, "
                f"state={session_state}",
            )
            return created

        session.session_state = session_state
        if payload is not None:
            session.sync_state_json = sync_state_json
        await session.save()

        # 不在此处广播 SSE：会话子状态(bind_status)是绑定内部细节，且其 status==previous_status
        # 会产生 from==to 的无意义“状态转换”事件。主生命周期状态变更已由 set_status 正确广播；
        # 绑定子状态通过 bind/status API 查询。

        logger.info(
            f"[AdapterInstanceService] 会话状态更新: instance_id={instance.id}, "
            f"state={session_state}",
        )
        return session

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    async def upsert_session(
        self,
        instance: DBAdapterInstance,
        credentials_json: str,
        sync_state_json: str,
        expires_at: datetime | None,
        last_cursor: str = "",
    ) -> DBAdapterInstanceSession:
        """创建或更新实例会话。

        Args:
            instance: 目标实例对象
            credentials_json: 凭据 JSON 字符串
            sync_state_json: 同步状态 JSON 字符串
            expires_at: 会话过期时间
            last_cursor: 最近同步游标

        Returns:
            DBAdapterInstanceSession: 创建或更新后的会话对象
        """
        session: DBAdapterInstanceSession | None = await DBAdapterInstanceSession.get_or_none(
            instance_id=instance.id,
        )

        if session is None:
            created = await DBAdapterInstanceSession.create(
                instance_id=instance.id,
                credentials_json=credentials_json,
                sync_state_json=sync_state_json,
                expires_at=expires_at,
                last_cursor=last_cursor,
            )
            logger.info(
                f"[AdapterInstanceService] 会话创建: instance_id={instance.id}, "
                f"session_id={created.id}",
            )
            return created

        session.credentials_json = credentials_json
        session.sync_state_json = sync_state_json
        session.expires_at = expires_at
        session.last_cursor = last_cursor
        await session.save()

        logger.info(
            f"[AdapterInstanceService] 会话更新: instance_id={instance.id}, "
            f"session_id={session.id}",
        )
        return session

    # ------------------------------------------------------------------
    # Renew Scheduling
    # ------------------------------------------------------------------

    async def schedule_renew(
        self,
        instance: DBAdapterInstance,
        expires_at: datetime | None,
        renew_before_minutes: int,
    ) -> DBAdapterInstance:
        """设置实例续期计划。

        计算 next_renew_at = expires_at - renew_before_minutes，并持久化。
        对于不会过期的会话 (expires_at 为 None)，直接返回、不安排续期。

        Args:
            instance: 目标实例对象
            expires_at: 凭据过期时间；None 表示会话不过期，跳过续期安排
            renew_before_minutes: 提前续期的分钟数

        Returns:
            DBAdapterInstance: 更新后的实例对象
        """
        if expires_at is None:
            logger.debug(
                f"[AdapterInstanceService] 会话不过期，跳过续期安排: instance_id={instance.id}",
            )
            return instance

        next_renew_at: datetime = expires_at - timedelta(minutes=renew_before_minutes)
        instance.next_renew_at = next_renew_at
        instance.renew_before_minutes = renew_before_minutes
        await instance.save()

        logger.info(
            f"[AdapterInstanceService] 续期计划: instance_id={instance.id}, "
            f"next_renew_at={next_renew_at.isoformat()}",
        )
        return instance

    # ------------------------------------------------------------------
    # Event Recording
    # ------------------------------------------------------------------

    async def record_event(
        self,
        instance: DBAdapterInstance,
        event_type: str,
        status_from: str,
        status_to: str,
        message: str,
        payload_json: str = "",
    ) -> DBAdapterInstanceEvent:
        """追加审计事件行。

        Args:
            instance: 目标实例对象
            event_type: 事件类型标识
            status_from: 变更前状态
            status_to: 变更后状态
            message: 事件说明
            payload_json: 事件载荷 JSON 字符串

        Returns:
            DBAdapterInstanceEvent: 创建的事件对象
        """
        event: DBAdapterInstanceEvent = await DBAdapterInstanceEvent.create(
            instance_id=instance.id,
            event_type=event_type,
            status_from=status_from,
            status_to=status_to,
            message=message,
            payload_json=payload_json,
        )
        return event

    # ------------------------------------------------------------------
    # Soft Delete
    # ------------------------------------------------------------------

    async def soft_delete_instance(self, instance: DBAdapterInstance) -> DBAdapterInstance:
        """软删除实例。

        统一经 set_status 变更为 "deleted"：记录审计事件、复用 last_error 逻辑，
        并广播 AdapterInstanceStatusEvent，使 SSE 订阅者与数据库状态保持同步。
        额外禁用实例 (enabled=False)。不会删除关联的审计行与会话记录。

        Args:
            instance: 目标实例对象

        Returns:
            DBAdapterInstance: 更新后的实例对象
        """
        # 先置 enabled=False，再交由 set_status 落库 + 广播：set_status 内部的
        # instance.save() 会一并持久化 enabled，避免直改状态导致 SSE 消费者漏掉删除事件。
        instance.enabled = False
        instance = await self.set_status(instance, "deleted", message="实例已软删除")
        logger.info(f"[AdapterInstanceService] 实例软删除: id={instance.id}")
        return instance


# 全局适配器实例服务
adapter_instance_service = AdapterInstanceService()
