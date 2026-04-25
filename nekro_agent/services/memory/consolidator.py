"""情景记忆沉淀器

从聊天消息中提取、压缩、沉淀情景记忆。
使用第三人称视角，结合人设上下文。
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import json5

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import APP_LOG_DIR
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_mem_entity import DBMemEntity, EntityType, MemorySource
from nekro_agent.models.db_mem_paragraph import (
    CognitiveType,
    DBMemParagraph,
    KnowledgeType,
    OriginKind,
)
from nekro_agent.models.db_mem_relation import DBMemRelation
from nekro_agent.services.memory.embedding_service import embed_text
from nekro_agent.services.memory.feature_flags import is_memory_system_enabled
from nekro_agent.services.memory.qdrant_manager import memory_qdrant_manager

logger = get_sub_logger("memory.consolidator")
MEMORY_PARSE_LOG_DIR = Path(APP_LOG_DIR) / "memory_parse_failures"
MEMORY_PARSE_LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PersonaContext:
    """人设身份上下文"""

    bot_sender_id: str  # Bot 在消息中的 sender_id
    persona_name: str  # 人设名称
    persona_brief: str  # 人设简述
    relationship_hint: str | None = None  # 与用户的关系提示


@dataclass
class ConsolidationResult:
    """沉淀结果"""

    paragraphs_created: int = 0
    entities_created: int = 0
    entities_updated: int = 0
    relations_created: int = 0
    relations_updated: int = 0
    messages_processed: int = 0
    last_processed_message_db_id: int = 0
    errors: list[str] | None = None


class MemoryResponseParseError(RuntimeError):
    """记忆提取响应解析失败。"""

    def __init__(self, classification: str, message: str):
        super().__init__(message)
        self.classification = classification


class EpisodicConsolidator:
    """情景记忆沉淀器

    职责：
    1. 读取未沉淀的聊天消息
    2. 使用 LLM 提炼情景记忆
    3. 提取实体和关系
    4. 生成向量并存储
    """

    def __init__(self, workspace_id: int):
        self.workspace_id = workspace_id
        self.persona_context: PersonaContext | None = None

    async def _load_channel(self, chat_key: str) -> DBChatChannel | None:
        """加载聊天频道对象。"""
        return await DBChatChannel.filter(chat_key=chat_key).first()

    def _read_memory_state(self, channel: DBChatChannel) -> dict[str, Any]:
        """从频道 data 中读取记忆状态。"""
        try:
            data = json.loads(channel.data or "{}")
            if not isinstance(data, dict):
                return {}
            memory_state = data.get("memory_state", {})
            return memory_state if isinstance(memory_state, dict) else {}
        except json.JSONDecodeError:
            return {}

    async def _mark_consolidated(self, chat_key: str, last_message_db_id: int) -> None:
        """记录最近一次已沉淀到的消息边界。"""
        channel = await self._load_channel(chat_key)
        if channel is None:
            return

        try:
            data = json.loads(channel.data or "{}")
            if not isinstance(data, dict):
                data = {}
        except json.JSONDecodeError:
            data = {}

        memory_state = data.get("memory_state", {})
        if not isinstance(memory_state, dict):
            memory_state = {}
        memory_state["last_consolidated_message_db_id"] = last_message_db_id
        memory_state["last_consolidated_at"] = datetime.now().isoformat()
        data["memory_state"] = memory_state

        channel.data = json.dumps(data, ensure_ascii=False)
        await channel.save(update_fields=["data", "update_time"])

    async def load_persona_context(self, chat_key: str) -> PersonaContext | None:
        """加载人设上下文

        Args:
            chat_key: 聊天频道标识

        Returns:
            人设上下文，或 None
        """
        try:
            channel = await self._load_channel(chat_key)
            if not channel:
                return None

            # 获取频道有效配置
            channel_config = await channel.get_effective_config()

            # 提取人设名称
            preset = channel_config.AI_CHAT_PRESET_SETTING or ""
            persona_name = self._extract_persona_name(preset)

            self.persona_context = PersonaContext(
                bot_sender_id="-1",  # Bot 消息的 sender_id
                persona_name=persona_name,
                persona_brief=preset[:100] if preset else "AI 助手",
            )
            return self.persona_context

        except Exception as e:
            logger.warning(f"加载人设上下文失败: {e}")
            return None

    def _extract_persona_name(self, preset: str) -> str:
        """从人设文本中提取名称"""
        if not preset:
            return "Assistant"

        # 尝试匹配常见的名称声明模式
        import re

        patterns = [
            r"我(?:的名字)?(?:是|叫)[：:\s]*([^\s,，。.!！]+)",
            r"名(?:字|称)[：:\s]*([^\s,，。.!！]+)",
            r"\[(?:角色|名称|name)[：:\s]*([^\]]+)\]",
        ]

        for pattern in patterns:
            match = re.search(pattern, preset, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # 默认返回
        return "Assistant"

    async def consolidate(
        self,
        chat_key: str,
        max_message_db_id: int | None = None,
        start_after_db_id: int | None = None,
        persist_progress: bool = True,
    ) -> ConsolidationResult:
        """执行沉淀

        Args:
            chat_key: 聊天频道标识

        Returns:
            沉淀结果
        """
        result = ConsolidationResult()

        try:
            # 加载人设上下文
            await self.load_persona_context(chat_key)

            # 获取待处理消息
            messages = await self._fetch_messages(
                chat_key,
                max_message_db_id=max_message_db_id,
                start_after_db_id=start_after_db_id,
            )
            if not messages:
                logger.debug(f"没有待处理消息: chat_key={chat_key}")
                return result

            result.messages_processed = len(messages)
            result.last_processed_message_db_id = messages[-1].id
            logger.info(f"开始沉淀 {len(messages)} 条消息: chat_key={chat_key}")
            last_message_db_id = messages[-1].id

            # 提炼记忆
            memory_items = await self._extract_memories(messages)
            if not memory_items:
                if persist_progress:
                    await self._mark_consolidated(chat_key, last_message_db_id)
                logger.debug("没有提取到有价值的记忆")
                return result

            # 存储记忆
            for item in memory_items:
                try:
                    paragraph, entities, relations = await self._store_memory(item, chat_key, messages)
                    if paragraph:
                        result.paragraphs_created += 1
                    result.entities_created += len([e for e, created in entities if created])
                    result.entities_updated += len([e for e, created in entities if not created])
                    result.relations_created += len([r for r, created in relations if created])
                    result.relations_updated += len([r for r, created in relations if not created])
                except Exception as e:
                    logger.exception(f"存储记忆失败: {e}")
                    if result.errors is None:
                        result.errors = []
                        result.errors.append(str(e))
                # 主动让出事件循环，避免长批次沉淀连续占用处理时机。
                await asyncio.sleep(0)

            logger.info(
                f"沉淀完成: paragraphs={result.paragraphs_created}, "
                f"entities={result.entities_created}+{result.entities_updated}, "
                f"relations={result.relations_created}+{result.relations_updated}",
            )
            if result.paragraphs_created > 0:
                try:
                    from nekro_agent.services.memory.episode_aggregator import aggregate_workspace_episodes

                    await aggregate_workspace_episodes(self.workspace_id, chat_key)
                except Exception as e:
                    logger.warning(f"Episode 自动聚合失败: {e}")
            if persist_progress:
                await self._mark_consolidated(chat_key, last_message_db_id)
            cooldown = max(0.0, float(config.MEMORY_CONSOLIDATION_BATCH_COOLDOWN_SECONDS))
            if cooldown > 0:
                await asyncio.sleep(cooldown)
            return result

        except Exception as e:
            logger.exception(f"沉淀过程失败: {e}")
            result.errors = [str(e)]
            return result

    async def _fetch_messages(
        self,
        chat_key: str,
        max_message_db_id: int | None = None,
        start_after_db_id: int | None = None,
    ) -> list[DBChatMessage]:
        """获取待处理消息"""
        if isinstance(start_after_db_id, int) and start_after_db_id >= 0:
            last_consolidated_db_id = start_after_db_id
        else:
            channel = await self._load_channel(chat_key)
            last_consolidated_db_id = 0
            if channel is not None:
                memory_state = self._read_memory_state(channel)
                raw_db_id = memory_state.get("last_consolidated_message_db_id", 0)
                if isinstance(raw_db_id, int) and raw_db_id >= 0:
                    last_consolidated_db_id = raw_db_id

        query = DBChatMessage.filter(
            chat_key=chat_key,
            id__gt=last_consolidated_db_id,
        )
        if isinstance(max_message_db_id, int) and max_message_db_id > 0:
            query = query.filter(id__lte=max_message_db_id)
        return await query.order_by("id").limit(config.MEMORY_CONSOLIDATION_BATCH_SIZE)

    async def _extract_memories(
        self,
        messages: list[DBChatMessage],
    ) -> list[dict[str, Any]]:
        """使用 LLM 提取记忆

        Returns:
            记忆项列表，每项包含 content, summary, entities, knowledge_type
        """
        if not messages:
            return []

        # 构建对话文本
        conversation_text = self._build_conversation_text(messages)
        if len(conversation_text) < config.MEMORY_CONSOLIDATION_MIN_CONTENT_LENGTH:
            return []

        # 构建 prompt
        persona_hint = ""
        if self.persona_context:
            persona_hint = (
                f"\n注意：对话中 sender_id 为 -1 的消息是 '{self.persona_context.persona_name}' "
                f"（{self.persona_context.persona_brief}）发送的，请在记忆中使用该名称而非 'AI' 或 '机器人'。"
            )

        prompt = f"""请分析以下对话，提取值得记住的重要信息。

要求：
1. 使用第三人称视角描述
2. 只提取有价值的信息（事实、偏好、重要讨论、决策等）
3. 过滤掉闲聊和无意义内容
4. 每条记忆应该简洁但完整{persona_hint}

对话内容：
{conversation_text}

请以 JSON 格式返回，格式如下：
```json
{{
  "memories": [
    {{
      "content": "第三人称的记忆描述，必须保留关键对象、行为、结论，不要写成过短标签",
      "summary": "可读性摘要（建议 20-40 字，必须能独立看懂）",
      "knowledge_type": "conversation|preference|fact|experience|decision|emotion",
      "entities": ["涉及的人名或概念"],
      "relations": [
        {{
          "subject": "实体A",
          "predicate": "喜欢|使用|创建|提到|讨论|属于",
          "object": "实体B"
        }}
      ]
    }}
  ]
}}
```

额外要求：
1. 不要输出“某人提到某事”“讨论了某话题”这种空泛句，必须带上具体内容。
2. 优先保留可复用的信息：能力、偏好、决策、结论、承诺、计划、问题定位、技术事实。
3. summary 不能只是项目名或动词短语，单独展示时必须有参考价值。
4. 如果多条信息属于同一事件，优先合并成一条更完整的记忆，而不是切成多个碎片。

如果没有值得记住的内容，返回空数组：{{"memories": []}}"""

        parse_retries = max(0, int(config.MEMORY_CONSOLIDATION_PARSE_MAX_RETRIES))
        for attempt in range(parse_retries + 1):
            try:
                use_fallback_model = attempt == parse_retries and parse_retries > 0
                if attempt > 0:
                    logger.info(
                        "记忆解析重试开始: attempt=%s/%s, use_fallback_model=%s",
                        attempt + 1,
                        parse_retries + 1,
                        use_fallback_model,
                    )
                response = await self._call_llm(prompt, use_fallback_model=use_fallback_model)
                return self._parse_memory_response(response)
            except MemoryResponseParseError as e:
                if attempt >= parse_retries:
                    logger.warning(
                        f"记忆响应解析在重试后仍失败: classification={e.classification}, attempts={attempt + 1}"
                    )
                    return []
                delay = min(2.0, 0.5 * (attempt + 1))
                logger.warning(
                    f"记忆响应解析失败，准备重新请求 LLM: classification={e.classification}, "
                    f"attempt={attempt + 1}/{parse_retries + 1}, "
                    f"next_use_fallback_model={attempt + 1 == parse_retries}, delay={delay}s"
                )
                await asyncio.sleep(delay)
            except Exception as e:
                logger.exception(f"LLM 提取记忆失败: {e}")
                return []
        return []

    def _build_conversation_text(self, messages: list[DBChatMessage]) -> str:
        """构建对话文本"""
        lines = []
        for msg in messages:
            time_str = datetime.fromtimestamp(msg.send_timestamp).strftime("%H:%M")
            sender = msg.sender_nickname or msg.sender_name or f"User_{msg.sender_id}"

            # 标记 bot 消息
            if msg.sender_id == "-1" and self.persona_context:
                sender = self.persona_context.persona_name

            content = msg.content_text[:500]  # 限制单条长度
            lines.append(f"[{time_str}] {sender}: {content}")

        return "\n".join(lines)

    async def _call_llm(self, prompt: str, *, use_fallback_model: bool = False) -> str:
        """调用 LLM（带重试机制）

        使用指数退避策略重试，处理临时性错误（网络、速率限制等）。
        """
        from nekro_agent.services.agent.openai import gen_openai_chat_response, parse_extra_body

        primary_model_group_name = config.MEMORY_CONSOLIDATION_MODEL_GROUP or config.USE_MODEL_GROUP
        fallback_model_group_name = config.MEMORY_CONSOLIDATION_FALLBACK_MODEL_GROUP or primary_model_group_name
        model_group_name = fallback_model_group_name if use_fallback_model else primary_model_group_name
        model_group = config.get_model_group_info(model_group_name)
        max_retries = config.MEMORY_LLM_MAX_RETRIES
        last_error: Exception | None = None
        extra_body = parse_extra_body(
            model_group.EXTRA_BODY,
            source_hint=f"Memory consolidation model group: {model_group_name}",
        ) or {}
        enable_force_json = config.MEMORY_CONSOLIDATION_FORCE_JSON_OUTPUT
        if enable_force_json:
            extra_body.setdefault("response_format", {"type": "json_object"})

        for attempt in range(max_retries + 1):
            try:
                if attempt == 0:
                    logger.info(
                        "开始记忆沉淀模型请求: model_group=%s, model=%s, use_fallback_model=%s",
                        model_group_name,
                        model_group.CHAT_MODEL,
                        use_fallback_model,
                    )
                response = await gen_openai_chat_response(
                    model=model_group.CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": "你是一个记忆提取助手，负责从对话中提取重要信息。"},
                        {"role": "user", "content": prompt},
                    ],
                    api_key=model_group.API_KEY,
                    base_url=model_group.BASE_URL,
                    temperature=0.3,
                    max_tokens=3000,
                    extra_body=extra_body or None,
                )
                return response.response_content
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if enable_force_json and "response_format" in error_str:
                    enable_force_json = False
                    extra_body.pop("response_format", None)
                    logger.warning(
                        f"记忆沉淀模型组 {model_group_name} 不支持 response_format，已自动回退普通输出模式: {e}",
                    )
                    continue

                # 判断是否为可重试的错误
                is_retryable = any(
                    keyword in error_str
                    for keyword in [
                        "timeout",
                        "rate limit",
                        "rate_limit",
                        "429",
                        "503",
                        "502",
                        "connection",
                        "network",
                        "temporarily",
                        "overloaded",
                    ]
                )

                if not is_retryable or attempt >= max_retries:
                    logger.warning(
                        f"LLM 调用失败（模型组={model_group_name}，不可重试或已达重试上限）: {e}"
                    )
                    raise

                # 指数退避：1s, 2s, 4s, ...
                delay = 2**attempt
                logger.info(
                    f"LLM 调用失败（模型组={model_group_name}），{delay}s 后重试"
                    f"（第 {attempt + 1}/{max_retries} 次）: {e}"
                )
                await asyncio.sleep(delay)

        # 理论上不会执行到这里，但为类型安全添加
        if last_error:
            raise last_error
        raise RuntimeError("LLM 调用失败")

    def _parse_memory_response(self, response: str) -> list[dict[str, Any]]:
        """解析 LLM 返回的记忆"""
        normalized = (response or "").strip().lstrip("\ufeff")
        if not normalized:
            logger.warning("解析记忆 JSON 失败: LLM 返回为空响应")
            raise MemoryResponseParseError("empty", "LLM 返回为空响应")

        json_match = re.search(r"```json\s*(.*?)\s*```", normalized, re.DOTALL | re.IGNORECASE)
        if json_match:
            candidate = json_match.group(1)
        else:
            object_match = re.search(r"(\{[\s\S]*\})", normalized)
            candidate = object_match.group(1) if object_match else normalized

        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as json_error:
            try:
                data = json5.loads(candidate)
                logger.warning(f"记忆 JSON 标准解析失败，已使用 JSON5 容错解析: {json_error}")
            except Exception as json5_error:
                classification = self._classify_parse_failure(normalized, candidate, json_error)
                failure_path = self._dump_parse_failure(
                    normalized_response=normalized,
                    candidate_response=candidate,
                    classification=classification,
                    json_error=json_error,
                    json5_error=json5_error,
                )
                preview = re.sub(r"\s+", " ", normalized)[:240]
                logger.warning(
                    f"解析记忆 JSON 失败[{classification}]: {json_error}; "
                    f"json5_error={json5_error}; failure_log={failure_path}; 响应预览={preview!r}"
                )
                raise MemoryResponseParseError(classification, f"{json_error}; failure_log={failure_path}")

        try:
            memories = data.get("memories", [])

            # 验证格式
            valid_memories = []
            for mem in memories:
                if isinstance(mem, dict) and "content" in mem:
                    valid_memories.append(
                        {
                            "content": mem["content"],
                            "summary": mem.get("summary", mem["content"][:50]),
                            "knowledge_type": mem.get("knowledge_type", "conversation"),
                            "entities": mem.get("entities", []),
                            "relations": mem.get("relations", []),
                        },
                    )
            return valid_memories

        except Exception as e:
            failure_path = self._dump_parse_failure(
                normalized_response=normalized,
                candidate_response=candidate,
                classification="schema_invalid",
                json_error=e,
                json5_error=None,
            )
            preview = re.sub(r"\s+", " ", normalized)[:240]
            logger.warning(f"解析记忆结构失败[schema_invalid]: {e}; failure_log={failure_path}; 响应预览={preview!r}")
            raise MemoryResponseParseError("schema_invalid", f"{e}; failure_log={failure_path}")

    def _classify_parse_failure(self, normalized: str, candidate: str, error: Exception) -> str:
        lowered = normalized.lower()
        error_text = str(error).lower()
        if not normalized:
            return "empty"
        if lowered.startswith("**") or "extracting" in lowered or "i'm now focusing" in lowered:
            return "reasoning_text"
        if "unterminated string" in error_text:
            return "unterminated_string"
        if "expecting ',' delimiter" in error_text:
            return "truncated_or_missing_delimiter"
        if not candidate.startswith("{"):
            return "non_json_prefix"
        return "invalid_json"

    def _dump_parse_failure(
        self,
        normalized_response: str,
        candidate_response: str,
        classification: str,
        json_error: Exception,
        json5_error: Exception | None,
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = MEMORY_PARSE_LOG_DIR / f"{timestamp}_{classification}.log"
        path.write_text(
            "\n".join(
                [
                    f"classification: {classification}",
                    f"json_error: {json_error!r}",
                    f"json5_error: {json5_error!r}",
                    "===== normalized_response =====",
                    normalized_response,
                    "===== candidate_response =====",
                    candidate_response,
                ]
            ),
            encoding="utf-8",
        )
        return str(path)

    async def _store_memory(
        self,
        memory_item: dict[str, Any],
        chat_key: str,
        messages: list[DBChatMessage],
    ) -> tuple[DBMemParagraph | None, list[tuple[DBMemEntity, bool]], list[tuple[DBMemRelation, bool]]]:
        """存储单条记忆

        Returns:
            (paragraph, [(entity, created), ...])
        """
        content = memory_item["content"]
        summary = memory_item["summary"][: config.MEMORY_CONSOLIDATION_MAX_SUMMARY_LENGTH]
        knowledge_type = memory_item.get("knowledge_type", "conversation")
        entity_names = memory_item.get("entities", [])
        relation_items = memory_item.get("relations", [])

        # 映射 knowledge_type
        kt_map = {
            "conversation": KnowledgeType.CONVERSATION,
            "preference": KnowledgeType.PREFERENCE,
            "fact": KnowledgeType.FACT,
            "experience": KnowledgeType.EXPERIENCE,
            "decision": KnowledgeType.DECISION,
            "emotion": KnowledgeType.EMOTION,
        }
        kt = kt_map.get(knowledge_type, KnowledgeType.CONVERSATION)

        # 计算锚定信息
        anchor_start = messages[0] if messages else None
        anchor_end = messages[-1] if messages else None

        # 去重检查：防止崩溃恢复后重复创建相同的记忆段落
        # 使用消息锚点范围 + 内容前缀匹配来判断是否已存在
        if anchor_start and anchor_end:
            existing = await DBMemParagraph.filter(
                workspace_id=self.workspace_id,
                origin_chat_key=chat_key,
                anchor_msg_id_start=anchor_start.message_id,
                anchor_msg_id_end=anchor_end.message_id,
            ).first()
            if existing and existing.content[:100] == content[:100]:
                logger.debug(f"跳过重复记忆段落: anchor={anchor_start.message_id}-{anchor_end.message_id}")
                return existing, [], []

        # 创建段落
        paragraph = await DBMemParagraph.create(
            workspace_id=self.workspace_id,
            memory_source="na",
            cognitive_type=CognitiveType.EPISODIC,
            knowledge_type=kt,
            content=content,
            summary=summary,
            event_time=datetime.fromtimestamp(anchor_end.send_timestamp) if anchor_end else datetime.now(),
            origin_kind=OriginKind.CONSOLIDATION,
            origin_chat_key=chat_key,
            anchor_msg_id_start=anchor_start.message_id if anchor_start else None,
            anchor_msg_id_end=anchor_end.message_id if anchor_end else None,
            anchor_timestamp_start=anchor_start.send_timestamp if anchor_start else None,
            anchor_timestamp_end=anchor_end.send_timestamp if anchor_end else None,
        )

        # 生成向量并存储
        try:
            embedding = await embed_text(content)
            await memory_qdrant_manager.upsert_paragraph(
                paragraph_id=paragraph.id,
                embedding=embedding,
                payload=paragraph.to_qdrant_payload(),
            )
            paragraph.embedding_ref = str(paragraph.id)
            await paragraph.save(update_fields=["embedding_ref"])
        except Exception as e:
            logger.warning(f"向量化失败，记忆仍已保存: {e}")

        # 创建/更新实体
        entities: list[tuple[DBMemEntity, bool]] = []
        entity_map: dict[str, DBMemEntity] = {}
        for name in entity_names:
            if not name or len(name) < 2:
                continue
            try:
                # 简单判断实体类型
                entity_type = EntityType.PERSON if self._is_person_name(name) else EntityType.CONCEPT
                entity, created = await DBMemEntity.find_or_create(
                    workspace_id=self.workspace_id,
                    entity_type=entity_type,
                    name=name,
                    source=MemorySource.NA,
                )
                entities.append((entity, created))
                entity_map[name.strip().lower()] = entity
            except Exception as e:
                logger.warning(f"创建实体失败: {name}, {e}")

        relations: list[tuple[DBMemRelation, bool]] = []
        for rel in relation_items:
            try:
                if not isinstance(rel, dict):
                    continue
                subject_name = str(rel.get("subject", "")).strip()
                predicate = str(rel.get("predicate", "")).strip()
                object_name = str(rel.get("object", "")).strip()
                if not subject_name or not predicate or not object_name:
                    continue

                subject = entity_map.get(subject_name.lower())
                if subject is None:
                    subject_type = EntityType.PERSON if self._is_person_name(subject_name) else EntityType.CONCEPT
                    subject, _ = await DBMemEntity.find_or_create(
                        workspace_id=self.workspace_id,
                        entity_type=subject_type,
                        name=subject_name,
                        source=MemorySource.NA,
                    )
                    entity_map[subject_name.lower()] = subject

                obj = entity_map.get(object_name.lower())
                if obj is None:
                    object_type = EntityType.PERSON if self._is_person_name(object_name) else EntityType.CONCEPT
                    obj, _ = await DBMemEntity.find_or_create(
                        workspace_id=self.workspace_id,
                        entity_type=object_type,
                        name=object_name,
                        source=MemorySource.NA,
                    )
                    entity_map[object_name.lower()] = obj

                if subject.id == obj.id:
                    continue

                relation, created = await DBMemRelation.find_or_create(
                    workspace_id=self.workspace_id,
                    subject_entity_id=subject.id,
                    predicate=predicate,
                    object_entity_id=obj.id,
                    paragraph_id=paragraph.id,
                    memory_source="na",
                    cognitive_type=CognitiveType.EPISODIC.value,
                )
                if created:
                    relation.half_life_seconds = config.MEMORY_RELATION_HALF_LIFE_SECONDS
                    await relation.save(update_fields=["half_life_seconds", "update_time"])
                relations.append((relation, created))
            except Exception as e:
                logger.warning(f"创建关系失败: {rel}, {e}")

        return paragraph, entities, relations

    def _is_person_name(self, name: str) -> bool:
        """简单判断是否为人名"""
        # 如果是人设名称，返回 True
        if self.persona_context and name == self.persona_context.persona_name:
            return True
        # 简单启发式：中文名通常 2-4 字，英文名首字母大写
        if 2 <= len(name) <= 4 and all("\u4e00" <= c <= "\u9fff" for c in name):
            return True
        if name[0].isupper() and name.isalpha():
            return True
        return False


async def consolidate_workspace(
    workspace_id: int,
    chat_key: str,
    max_message_db_id: int | None = None,
    start_after_db_id: int | None = None,
    persist_progress: bool = True,
) -> ConsolidationResult:
    """便捷函数：执行工作区沉淀"""
    if not is_memory_system_enabled():
        return ConsolidationResult()

    consolidator = EpisodicConsolidator(workspace_id)
    return await consolidator.consolidate(
        chat_key,
        max_message_db_id=max_message_db_id,
        start_after_db_id=start_after_db_id,
        persist_progress=persist_progress,
    )
