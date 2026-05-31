import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from nekro_agent.adapters import load_adapter_config, loaded_adapters
from nekro_agent.adapters.email.clients.oauth import build_oauth_authorize_url, exchange_oauth_code
from nekro_agent.adapters.email.config import EmailAccount

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv

logger = get_sub_logger("adapter.email.router")

# 适配器注册器
_email_adapter = None


def set_email_adapter(adapter):
    """设置邮箱适配器实例"""
    global _email_adapter
    _email_adapter = adapter


class _EmailConfigAdapter:
    def __init__(self):
        self.config = load_adapter_config("email")


def get_email_adapter():
    """获取邮箱适配器实例；未启用时回退到配置对象，保证账户配置页可用。"""
    adapter = _email_adapter or loaded_adapters.get("email")
    return adapter or _EmailConfigAdapter()


# 注意：这里不应该设置prefix，因为在外层已经设置了
router = APIRouter(tags=["Adapter:email"])


def _get_accounts(adapter) -> List[EmailAccount]:
    return list(getattr(adapter.config, "RECEIVE_ACCOUNTS", []) or [])


def _save_email_config(adapter) -> None:
    adapter.config.dump_config()


async def _sync_runtime_account(adapter, account: EmailAccount) -> None:
    reconnect_success = True
    reconnect = getattr(adapter, "_reconnect_email_client", None)
    if reconnect:
        reconnect_success = bool(await reconnect(account))
    mapping = getattr(adapter, "account_chat_mapping", None)
    if not isinstance(mapping, dict):
        return
    if account.ENABLED and account.RECEIVE_ENABLED and reconnect_success:
        mapping[account.USERNAME] = account.USERNAME
    else:
        mapping.pop(account.USERNAME, None)


async def _remove_runtime_account(adapter, account: EmailAccount) -> None:
    remove = getattr(adapter, "_remove_email_client", None)
    if remove:
        await remove(account.USERNAME)


def _normalize_default_sender(accounts: List[EmailAccount], selected_index: int | None = None) -> None:
    default_indexes = [index for index, account in enumerate(accounts) if account.IS_DEFAULT_SENDER]
    if selected_index is not None and 0 <= selected_index < len(accounts) and accounts[selected_index].IS_DEFAULT_SENDER:
        default_indexes = [selected_index]
    if not default_indexes:
        return
    selected = default_indexes[-1]
    for index, account in enumerate(accounts):
        account.IS_DEFAULT_SENDER = index == selected


def _sanitize_account(account: EmailAccount, index: int) -> dict:
    data = account.model_dump()
    has_password = bool(data.get("PASSWORD"))
    has_client_secret = bool(data.get("CLIENT_SECRET"))
    has_refresh_token = bool(data.get("REFRESH_TOKEN"))
    data["PASSWORD"] = ""
    data["CLIENT_SECRET"] = ""
    data["ACCESS_TOKEN"] = ""
    data["REFRESH_TOKEN"] = ""
    data["HAS_PASSWORD"] = has_password
    data["HAS_CLIENT_SECRET"] = has_client_secret
    data["OAUTH_CONNECTED"] = has_refresh_token
    data["index"] = index
    return data


def _validate_index(accounts: List[EmailAccount], index: int) -> None:
    if index < 0 or index >= len(accounts):
        raise HTTPException(status_code=404, detail="Email account not found")


@router.get("/status")
async def get_email_status():
    """获取邮箱适配器状态"""
    return {"status": "ok", "message": "Email adapter is running"}


@router.get("/accounts")
async def get_email_accounts(adapter=Depends(get_email_adapter)):
    """获取邮箱账户列表（基于适配器配置，移除敏感字段）"""
    if not getattr(adapter, "config", None):
        return {"error": "Adapter not initialized"}

    accounts = _get_accounts(adapter)
    return {"accounts": [_sanitize_account(account, index) for index, account in enumerate(accounts)]}


@router.post("/accounts")
async def create_email_account(request: dict, adapter=Depends(get_email_adapter)):
    """新增邮箱账户，数据写入 Email 适配器配置。"""
    try:
        account = EmailAccount.model_validate(request)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e

    accounts = _get_accounts(adapter)
    accounts.append(account)
    _normalize_default_sender(accounts, len(accounts) - 1)
    adapter.config.RECEIVE_ACCOUNTS = accounts
    _save_email_config(adapter)
    await _sync_runtime_account(adapter, account)
    return {"success": True, "index": len(accounts) - 1}


@router.put("/accounts/{index}")
async def update_email_account(index: int, request: dict, adapter=Depends(get_email_adapter)):
    """更新邮箱账户；未传 PASSWORD 时保留旧密码。"""
    accounts = _get_accounts(adapter)
    _validate_index(accounts, index)

    current = accounts[index].model_dump()
    payload = dict(request)
    if "PASSWORD" not in payload:
        payload["PASSWORD"] = current.get("PASSWORD", "")
    for secret_key in ("CLIENT_SECRET", "ACCESS_TOKEN", "REFRESH_TOKEN"):
        if secret_key not in payload:
            payload[secret_key] = current.get(secret_key, "")

    try:
        accounts[index] = EmailAccount.model_validate({**current, **payload})
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e

    _normalize_default_sender(accounts, index)
    adapter.config.RECEIVE_ACCOUNTS = accounts
    _save_email_config(adapter)
    await _sync_runtime_account(adapter, accounts[index])
    return {"success": True}


@router.post("/accounts/{index}/test")
async def test_email_account(index: int, adapter=Depends(get_email_adapter)):
    """测试邮箱账户连接并记录最近一次测试结果。"""
    accounts = _get_accounts(adapter)
    _validate_index(accounts, index)
    account = accounts[index]

    success = False
    stage = "创建客户端"
    message = ""
    client = None
    try:
        create_client = getattr(adapter, "_create_email_client")
        client = create_client(account)
        client_name = client.__class__.__name__
        log_message = (
            f"测试邮箱账户连接: index={index}, username={account.USERNAME}, provider={account.EMAIL_ACCOUNT}, "
            f"auth_type={account.AUTH_TYPE}, transport_type={account.TRANSPORT_TYPE}, oauth_provider={account.OAUTH_PROVIDER}, "
            f"has_password={bool(account.PASSWORD)}, has_refresh_token={bool(account.REFRESH_TOKEN)}, "
            f"token_expires_at={account.TOKEN_EXPIRES_AT}, client={client_name}"
        )
        logger.info(log_message)

        stage = "连接服务器"
        await client.connect()
        logger.info(f"测试邮箱账户连接成功进入选择邮箱阶段: username={account.USERNAME}, client={client_name}")

        stage = "选择邮箱文件夹"
        mailbox = await client.select_mailbox()
        success = True
        message = f"连接成功，已选择邮箱文件夹: {mailbox}"
        logger.info(f"测试邮箱账户连接成功: username={account.USERNAME}, mailbox={mailbox}")
    except Exception as e:
        message = f"{stage}失败: {e!s}"
        logger.exception(
            f"测试邮箱账户连接失败: index={index}, username={account.USERNAME}, provider={account.EMAIL_ACCOUNT}, "
            f"auth_type={account.AUTH_TYPE}, transport_type={account.TRANSPORT_TYPE}, oauth_provider={account.OAUTH_PROVIDER}, "
            f"has_password={bool(account.PASSWORD)}, has_refresh_token={bool(account.REFRESH_TOKEN)}, "
            f"token_expires_at={account.TOKEN_EXPIRES_AT}, stage={stage}"
        )
    finally:
        if client:
            try:
                await client.close()
            except Exception:
                pass

    account.LAST_TEST_SUCCESS = success
    account.LAST_TEST_MESSAGE = message
    account.LAST_TEST_TIME = int(time.time())
    accounts[index] = account
    adapter.config.RECEIVE_ACCOUNTS = accounts
    _save_email_config(adapter)
    return {"success": success, "message": message, "tested_at": account.LAST_TEST_TIME}


@router.post("/accounts/{index}/pull")
async def pull_email_account(index: int, request: Optional[dict] = None, adapter=Depends(get_email_adapter)):
    """手动拉取指定账户的未读收件箱，并返回诊断统计。"""
    accounts = _get_accounts(adapter)
    _validate_index(accounts, index)
    account = accounts[index]

    manual_pull = getattr(adapter, "manual_pull_account", None)
    if not manual_pull:
        raise HTTPException(status_code=503, detail="Email adapter runtime is not initialized")

    payload = request or {}
    unseen_only = payload.get("unseen_only", True)
    if not isinstance(unseen_only, bool):
        raise HTTPException(status_code=400, detail="unseen_only must be a boolean")

    limit_value = payload.get("limit")
    limit: int | None = None
    if limit_value is not None:
        try:
            limit = int(limit_value)
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=400, detail="limit must be an integer") from e
        if limit <= 0:
            raise HTTPException(status_code=400, detail="limit must be greater than 0")

    try:
        result = await manual_pull(account, unseen_only=unseen_only, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"account_index": index, **result}


@router.delete("/accounts/{index}")
async def delete_email_account(index: int, adapter=Depends(get_email_adapter)):
    """删除邮箱账户，数据写回 Email 适配器配置。"""
    accounts = _get_accounts(adapter)
    _validate_index(accounts, index)
    removed_account = accounts.pop(index)
    _normalize_default_sender(accounts)
    adapter.config.RECEIVE_ACCOUNTS = accounts
    _save_email_config(adapter)
    await _remove_runtime_account(adapter, removed_account)
    return {"success": True}


@router.post("/accounts/{index}/oauth/authorize-url")
async def create_oauth_authorize_url(index: int, request: dict, adapter=Depends(get_email_adapter)):
    """生成 Gmail/Outlook 官方 OAuth 授权跳转链接。"""
    accounts = _get_accounts(adapter)
    _validate_index(accounts, index)
    account = accounts[index]
    if account.EMAIL_ACCOUNT not in {"Gmail", "Outlook"}:
        raise HTTPException(status_code=400, detail="Only Gmail and Outlook support OAuth authorization")
    redirect_uri = str(request.get("redirect_uri") or "")
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="Missing redirect_uri")
    state = str(request.get("state") or f"email:{index}")
    try:
        authorize_url = build_oauth_authorize_url(account, redirect_uri, state)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"authorize_url": authorize_url, "state": state}


@router.post("/accounts/{index}/oauth/callback")
async def handle_oauth_callback(index: int, request: dict, adapter=Depends(get_email_adapter)):
    """处理 Gmail/Outlook OAuth 回调 code，并把 token 写回账户配置。"""
    accounts = _get_accounts(adapter)
    _validate_index(accounts, index)
    account = accounts[index]
    if account.EMAIL_ACCOUNT not in {"Gmail", "Outlook"}:
        raise HTTPException(status_code=400, detail="Only Gmail and Outlook support OAuth authorization")
    code = str(request.get("code") or "")
    redirect_uri = str(request.get("redirect_uri") or "")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="Missing redirect_uri")
    try:
        await exchange_oauth_code(account, code, redirect_uri, getattr(adapter.config, "OAUTH_PROXY", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    accounts[index] = account
    adapter.config.RECEIVE_ACCOUNTS = accounts
    _save_email_config(adapter)
    await _sync_runtime_account(adapter, account)
    return {"success": True}


@router.get("/polling-status")
async def get_polling_status(adapter=Depends(get_email_adapter)):
    """获取邮箱适配器轮询状态"""
    return adapter.get_polling_status()


@router.get("/attachments/status")
async def get_attachments_status(_adapter=Depends(get_email_adapter)):
    """获取附件下载状态"""
    try:
        # 仅统计实际的邮件附件目录，避免将非邮件上传目录计入统计
        save_path = Path(OsEnv.DATA_DIR) / "uploads" / "email_attachment"

        # 统计附件数量和总大小
        attachment_count = 0
        total_size = 0
        email_count = 0
        account_count = 0

        if save_path.exists():
            # 遍历所有邮箱账户目录
            for account_dir in save_path.iterdir():
                if not account_dir.is_dir():
                    continue
                account_count += 1

                # 遍历该账户下的所有邮件目录（按 email_uid）
                for email_uid_dir in account_dir.iterdir():
                    if not email_uid_dir.is_dir():
                        continue

                    # 统计该邮件目录下的附件
                    has_attachments = False
                    for file_path in email_uid_dir.rglob("*"):
                        if file_path.is_file():
                            try:
                                total_size += file_path.stat().st_size
                                attachment_count += 1
                                has_attachments = True
                            except OSError:
                                # 文件可能已被删除或无法访问
                                continue

                    if has_attachments:
                        email_count += 1

        return {
            "save_path": str(save_path),
            "account_count": account_count,
            "email_count": email_count,
            "attachment_count": attachment_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attachments status: {e!s}") from e


@router.post("/raw-email")
async def get_raw_email_content(request: dict, adapter=Depends(get_email_adapter)):
    """获取邮件原始内容"""

    def _validate_request(req: dict) -> None:
        if not req.get("account_username") or not req.get("email_id"):
            raise HTTPException(status_code=400, detail="Missing account_username or email_id")

    try:
        _validate_request(request)
        account_username = request.get("account_username")
        email_id = request.get("email_id")

        # 调用适配器方法获取原始邮件内容
        return await adapter.get_raw_email_content(account_username, email_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get raw email content: {e!s}") from e


# 同时支持PUT方法，避免405错误
@router.put("/raw-email")
async def get_raw_email_content_put(request: dict, adapter=Depends(get_email_adapter)):
    """获取邮件原始内容 (PUT方法)"""
    return await get_raw_email_content(request, adapter)
