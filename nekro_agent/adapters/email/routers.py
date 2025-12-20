from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import os

from nekro_agent.core.os_env import OsEnv

# 适配器注册器
_email_adapter = None

def set_email_adapter(adapter):
    """设置邮箱适配器实例"""
    global _email_adapter
    _email_adapter = adapter

def get_email_adapter():
    """获取邮箱适配器实例（用于FastAPI依赖注入）"""
    if _email_adapter is None:
        raise HTTPException(status_code=500, detail="Adapter not initialized")
    return _email_adapter

# 注意：这里不应该设置prefix，因为在外层已经设置了
router = APIRouter(tags=["Adapter:email"])

@router.get("/status")
async def get_email_status():
    """获取邮箱适配器状态"""
    return {"status": "ok", "message": "Email adapter is running"}

@router.get("/accounts")
async def get_email_accounts(adapter = Depends(get_email_adapter)):
    """获取邮箱账户列表（基于适配器配置，移除敏感字段）"""
    if not getattr(adapter, "config", None):
        return {"error": "Adapter not initialized"}

    receive_accounts = getattr(adapter.config, "RECEIVE_ACCOUNTS", []) or []

    sanitized_accounts = []
    for account in receive_accounts:
        # 尝试处理 dict 类型配置
        if isinstance(account, dict):
            # 移除明显敏感字段
            sanitized = {
                k: v
                for k, v in account.items()
                if k.lower() not in {"password", "secret", "token", "access_token", "refresh_token"}
            }
            sanitized_accounts.append(sanitized)
        # 尝试处理具有 dict()/model_dump() 的对象类型配置（例如 Pydantic 模型）
        elif hasattr(account, "dict") or hasattr(account, "model_dump"):
            dump_fn = getattr(account, "model_dump", None) or getattr(account, "dict", None)
            if dump_fn is not None:
                sanitized = dump_fn(
                    exclude={"password", "secret", "token", "access_token", "refresh_token"},
                )
                sanitized_accounts.append(sanitized)
            else:
                # 如果两个方法都不存在，转为字符串
                sanitized_accounts.append(str(account))
        else:
            # 不可识别类型，直接转为字符串，避免暴露内部实现/敏感信息
            sanitized_accounts.append(str(account))

    return {"accounts": sanitized_accounts}

@router.get("/polling-status")
async def get_polling_status(adapter = Depends(get_email_adapter)):
    """获取邮箱适配器轮询状态"""
    return adapter.get_polling_status()

@router.get("/folders/{account_username}")
async def get_account_folders(account_username: str, adapter = Depends(get_email_adapter)):
    """获取指定账户的文件夹列表"""
    # 查找账户对应的IMAP连接
    if account_username not in adapter.imap_connections:
        raise HTTPException(status_code=404, detail=f"Account {account_username} not found or not connected")

    conn = adapter.imap_connections[account_username]
    try:
        # 获取文件夹列表
        folders = await adapter._get_mailbox_folders(account_username, conn)
        return {"account": account_username, "folders": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get folders: {str(e)}")

@router.get("/folders")
async def get_all_account_folders(adapter = Depends(get_email_adapter)):
    """获取所有账户的文件夹列表"""
    result = {}
    for account_username, conn in adapter.imap_connections.items():
        try:
            folders = await adapter._get_mailbox_folders(account_username, conn)
            result[account_username] = folders
        except Exception as e:
            result[account_username] = {"error": str(e)}

    return {"accounts": result}

@router.get("/attachments/status")
async def get_attachments_status(adapter = Depends(get_email_adapter)):
    """获取附件下载状态"""
    try:
        # 仅统计实际的邮件附件目录，避免将非邮件上传目录计入统计
        save_path = os.path.join(OsEnv.DATA_DIR, "uploads", "email_attachment")

        # 统计附件数量和总大小
        attachment_count = 0
        total_size = 0
        email_count = 0
        account_count = 0

        if os.path.exists(save_path):
            # 遍历所有邮箱账户目录
            for account_dir in os.listdir(save_path):
                account_path = os.path.join(save_path, account_dir)
                if not os.path.isdir(account_path):
                    continue
                account_count += 1

                # 遍历该账户下的所有邮件目录（按 email_uid）
                for email_uid_dir in os.listdir(account_path):
                    email_path = os.path.join(account_path, email_uid_dir)
                    if not os.path.isdir(email_path):
                        continue

                    # 统计该邮件目录下的附件
                    has_attachments = False
                    for root, _, files in os.walk(email_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                total_size += os.path.getsize(file_path)
                                attachment_count += 1
                                has_attachments = True
                            except OSError:
                                # 文件可能已被删除或无法访问
                                continue

                    if has_attachments:
                        email_count += 1

        return {
            "save_path": save_path,
            "account_count": account_count,
            "email_count": email_count,
            "attachment_count": attachment_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attachments status: {str(e)}")

@router.post("/raw-email")
async def get_raw_email_content(request: dict, adapter = Depends(get_email_adapter)):
    """获取邮件原始内容"""
    try:
        account_username = request.get("account_username")
        email_id = request.get("email_id")

        if not account_username or not email_id:
            raise HTTPException(status_code=400, detail="Missing account_username or email_id")

        # 调用适配器方法获取原始邮件内容
        result = await adapter.get_raw_email_content(account_username, email_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get raw email content: {str(e)}")

# 同时支持PUT方法，避免405错误
@router.put("/raw-email")
async def get_raw_email_content_put(request: dict, adapter = Depends(get_email_adapter)):
    """获取邮件原始内容 (PUT方法)"""
    return await get_raw_email_content(request, adapter)