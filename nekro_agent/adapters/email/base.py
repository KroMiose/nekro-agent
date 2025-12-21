"""邮箱适配器基础类和提供商接口"""

from typing import Dict, Optional

# 邮箱提供商配置映射
EMAIL_PROVIDER_CONFIGS: Dict[str, Dict[str, str]] = {
    "QQ邮箱": {
        "imap_host": "imap.qq.com",
        "imap_port": "993",
        "smtp_host": "smtp.qq.com",
        "smtp_port": "587",
        "smtp_ssl_port": "465",
        "smtp_use_ssl": "true",  # QQ 邮箱推荐使用 SSL
    },
    "163邮箱": {
        "imap_host": "imap.163.com",
        "imap_port": "993",
        "smtp_host": "smtp.163.com",
        "smtp_port": "587",
        "smtp_ssl_port": "465",
    },
    "Gmail": {
        "imap_host": "imap.gmail.com",
        "imap_port": "993",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": "587",
        "smtp_ssl_port": "465",
    },
    "Outlook": {
        "imap_host": "outlook.office365.com",
        "imap_port": "993",
        "smtp_host": "smtp-mail.outlook.com",
        "smtp_port": "587",
        "smtp_ssl_port": "587",
    },
}
