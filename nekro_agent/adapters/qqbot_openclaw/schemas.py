from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QQBotMessageScene(BaseModel):
    model_config = ConfigDict(extra="allow")

    ext: Any = None


class QQBotMsgElement(BaseModel):
    model_config = ConfigDict(extra="allow")

    msg_idx: str | int | None = None


class QQBotAttachment(BaseModel):
    model_config = ConfigDict(extra="allow")

    content_type: str = ""
    filename: str = ""
    height: int | None = None
    width: int | None = None
    size: int | None = None
    url: str = ""
    voice_wav_url: str = ""
    asr_refer_text: str = ""


class QQBotC2CAuthor(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    union_openid: str = ""
    user_openid: str = ""
    username: str = ""
    nickname: str = ""
    nick: str = ""
    name: str = ""


class QQBotGroupAuthor(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    member_openid: str = ""
    username: str = ""
    nickname: str = ""
    nick: str = ""
    name: str = ""
    bot: bool = False


class QQBotMention(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    user_openid: str = ""
    member_openid: str = ""
    bot: bool = False
    username: str = ""


class QQBotBaseMessageEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    content: str = ""
    timestamp: str | int | float | None = None
    message_scene: QQBotMessageScene | None = None
    attachments: list[QQBotAttachment] = Field(default_factory=list)
    message_type: int | None = None
    msg_elements: list[QQBotMsgElement] = Field(default_factory=list)

    @field_validator("message_scene", mode="before")
    @classmethod
    def _normalize_message_scene(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return None
        return value

    @field_validator("attachments", "msg_elements", mode="before")
    @classmethod
    def _normalize_list_fields(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return []
        return value


class QQBotC2CMessageEvent(QQBotBaseMessageEvent):
    author: QQBotC2CAuthor = Field(default_factory=QQBotC2CAuthor)


class QQBotGroupMessageEvent(QQBotBaseMessageEvent):
    author: QQBotGroupAuthor = Field(default_factory=QQBotGroupAuthor)
    group_id: str = ""
    group_openid: str = ""
    group_name: str = ""
    group_nick: str = ""
    group_title: str = ""
    mentions: list[QQBotMention] = Field(default_factory=list)

    @field_validator("mentions", mode="before")
    @classmethod
    def _normalize_mentions(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return []
        return value


class QQBotGatewayPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    op: int
    d: Any = None
    s: int | None = None
    t: str | None = None


class QQBotMessageResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    msg_id: str | None = None
    ext_info: dict[str, Any] | None = None

    @property
    def response_message_id(self) -> str:
        return str(self.id or self.msg_id or "")

    @property
    def ref_idx(self) -> str:
        ext_info = self.ext_info or {}
        return str(ext_info.get("ref_idx") or "")


class QQBotUploadPreparePart(BaseModel):
    model_config = ConfigDict(extra="allow")

    index: int | None = None
    part_number: int | None = None
    offset: int | None = None
    size: int | None = None
    presigned_url: str | None = None
    upload_url: str | None = None
    url: str | None = None


class QQBotUploadPrepareResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    upload_id: str
    block_size: int | str | None = None
    concurrency: int | str | None = None
    retry_timeout: int | str | None = None
    parts: list[QQBotUploadPreparePart] = Field(default_factory=list)


class QQBotMediaUploadResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    file_info: str | dict[str, Any] | None = None
    file_uuid: str | None = None
    ttl: int | None = None
