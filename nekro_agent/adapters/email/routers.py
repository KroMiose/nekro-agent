from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import os

from nekro_agent.core.os_env import OsEnv

# 全局变量存储适配器实例
_email_adapter = None

def set_email_adapter(adapter):
    """设置邮箱适配器实例"""
    global _email_adapter
    _email_adapter = adapter

# 注意：这里不应该设置prefix，因为在外层已经设置了
router = APIRouter(tags=["Adapter:email"])

@router.get("/status")
async def get_email_status():
    """获取邮箱适配器状态"""
    return {"status": "ok", "message": "Email adapter is running"}

@router.get("/accounts")
async def get_email_accounts():
    """获取邮箱账户列表"""
    return {"accounts": []}

@router.get("/polling-status")
async def get_polling_status():
    """获取邮箱适配器轮询状态"""
    if _email_adapter:
        return _email_adapter.get_polling_status()
    return {"error": "Adapter not initialized"}

@router.get("/folders/{account_username}")
async def get_account_folders(account_username: str):
    """获取指定账户的文件夹列表"""
    if not _email_adapter:
        raise HTTPException(status_code=500, detail="Adapter not initialized")
    
    # 查找账户对应的IMAP连接
    if account_username not in _email_adapter.imap_connections:
        raise HTTPException(status_code=404, detail=f"Account {account_username} not found or not connected")
    
    conn = _email_adapter.imap_connections[account_username]
    try:
        # 获取文件夹列表
        folders = await _email_adapter._get_mailbox_folders(account_username, conn)
        return {"account": account_username, "folders": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get folders: {str(e)}")

@router.get("/folders")
async def get_all_account_folders():
    """获取所有账户的文件夹列表"""
    if not _email_adapter:
        raise HTTPException(status_code=500, detail="Adapter not initialized")
    
    result = {}
    for account_username, conn in _email_adapter.imap_connections.items():
        try:
            folders = await _email_adapter._get_mailbox_folders(account_username, conn)
            result[account_username] = folders
        except Exception as e:
            result[account_username] = {"error": str(e)}
    
    return {"accounts": result}

@router.get("/attachments/status")
async def get_attachments_status():
    """获取附件下载状态"""
    if not _email_adapter:
        raise HTTPException(status_code=500, detail="Adapter not initialized")
    
    try:
        save_path = os.path.join(OsEnv.DATA_DIR, "uploads")
        
        # 统计附件数量和总大小
        attachment_count = 0
        total_size = 0
        email_count = 0
        
        if os.path.exists(save_path):
            # 遍历所有邮箱账户目录
            for account_dir in os.listdir(save_path):
                account_path = os.path.join(save_path, account_dir)
                if os.path.isdir(account_path):
                    # 遍历该账户下的所有邮件目录
                    for email_dir in os.listdir(account_path):
                        email_path = os.path.join(account_path, email_dir)
                        if os.path.isdir(email_path):
                            email_count += 1
                            # 统计该邮件目录下的附件
                            for root, dirs, files in os.walk(email_path):
                                for file in files:
                                    attachment_count += 1
                                    file_path = os.path.join(root, file)
                                    total_size += os.path.getsize(file_path)
        
        return {
            "save_path": save_path,
            "account_count": len(os.listdir(save_path)) if os.path.exists(save_path) else 0,
            "email_count": email_count,
            "attachment_count": attachment_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attachments status: {str(e)}")

@router.post("/raw-email")
async def get_raw_email_content(request: dict):
    """获取邮件原始内容"""
    if not _email_adapter:
        raise HTTPException(status_code=500, detail="Adapter not initialized")
    
    try:
        account_username = request.get("account_username")
        email_id = request.get("email_id")
        
        if not account_username or not email_id:
            raise HTTPException(status_code=400, detail="Missing account_username or email_id")
        
        # 调用适配器方法获取原始邮件内容
        result = await _email_adapter.get_raw_email_content(account_username, email_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get raw email content: {str(e)}")

# 同时支持PUT方法，避免405错误
@router.put("/raw-email")
async def get_raw_email_content_put(request: dict):
    """获取邮件原始内容 (PUT方法)"""
    return await get_raw_email_content(request)