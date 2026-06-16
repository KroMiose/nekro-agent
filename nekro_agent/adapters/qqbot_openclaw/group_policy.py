from __future__ import annotations

from dataclasses import dataclass

from .config import QQBotOpenClawConfig
from .ref_index_store import RefIndexEntry
from .schemas import QQBotGroupMessageEvent


@dataclass(slots=True)
class GroupDecision:
    collect: bool
    trigger: bool
    reason: str


class GroupPolicyResolver:
    def __init__(self, config: QQBotOpenClawConfig, self_user_id: str = "") -> None:
        self.config = config
        self.self_user_id = self_user_id

    def set_self_user_id(self, self_user_id: str) -> None:
        self.self_user_id = self_user_id

    def decide(
        self,
        *,
        event_type: str,
        event: QQBotGroupMessageEvent,
        ref_entry: RefIndexEntry | None,
    ) -> GroupDecision:
        group_openid = event.group_openid or event.group_id
        if not self._is_group_allowed(group_openid):
            return GroupDecision(collect=False, trigger=False, reason="group-not-allowed")

        if event_type == "GROUP_AT_MESSAGE_CREATE":
            return GroupDecision(collect=True, trigger=True, reason="group-at")

        if event_type != "GROUP_MESSAGE_CREATE":
            return GroupDecision(collect=False, trigger=False, reason="unsupported-group-event")

        if ref_entry and ref_entry.is_bot:
            return GroupDecision(collect=True, trigger=True, reason="reply-to-bot")

        has_mentions = bool(event.mentions)
        mentions_bot = self._mentions_self(event)
        if self.config.IGNORE_OTHER_MENTIONS and has_mentions and not mentions_bot:
            return GroupDecision(collect=True, trigger=False, reason="other-mentions")

        if mentions_bot:
            return GroupDecision(collect=True, trigger=True, reason="mentions-bot")

        if self.config.DEFAULT_REQUIRE_MENTION:
            return GroupDecision(collect=True, trigger=False, reason="context-only")

        return GroupDecision(collect=True, trigger=True, reason="mention-not-required")

    def _is_group_allowed(self, group_openid: str) -> bool:
        policy = self.config.GROUP_POLICY
        if policy == "disabled":
            return False
        if policy == "open":
            return True
        allowed = {item.strip() for item in self.config.GROUP_ALLOW_FROM if item.strip()}
        return "*" in allowed or group_openid in allowed

    def _mentions_self(self, event: QQBotGroupMessageEvent) -> bool:
        candidates = {self.config.APP_ID.strip(), self.self_user_id.strip()}
        candidates.discard("")
        for mention in event.mentions:
            if mention.bot:
                return True
            mention_ids = {mention.id, mention.user_openid, mention.member_openid}
            if candidates.intersection(mention_ids):
                return True
        content = event.content or ""
        return any(candidate and f"@{candidate}" in content for candidate in candidates)
