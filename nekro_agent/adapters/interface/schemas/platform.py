from pydantic import BaseModel


class PlatformUser(BaseModel):
    user_id: str
    user_name: str
    user_avatar: str


class PlatformChannel(BaseModel):
    channel_id: str
    channel_name: str
    channel_avatar: str
