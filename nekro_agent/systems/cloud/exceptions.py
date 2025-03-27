class NekroCloudDisabled(Exception):
    """Nekro Cloud 未启用异常"""

    def __init__(self, message: str = "Nekro Cloud 未启用"):
        self.message = message
        super().__init__(self.message)
