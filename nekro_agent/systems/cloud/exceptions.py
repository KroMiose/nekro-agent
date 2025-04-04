class NekroCloudDisabled(Exception):
    """Nekro Cloud 未启用异常"""

    def __init__(self, message: str = "Nekro Cloud 未启用"):
        self.message = message
        super().__init__(self.message)


class NekroCloudAPIKeyInvalid(Exception):
    """Nekro Cloud API Key 无效异常"""

    def __init__(self, message: str = "Nekro Cloud API Key 无效，请前往 NekroAI 社区获取并配置"):
        self.message = message
        super().__init__(self.message)
