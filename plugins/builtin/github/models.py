from datetime import datetime
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field


class RepoSubscription(BaseModel):
    """仓库订阅信息"""

    repo_name: str
    events: Set[str] = Field(default_factory=set)  # 订阅的事件类型，如 "push", "issues", "issue_comment" 等
    created_at: float
    last_updated: float

    @classmethod
    def create(cls, repo_name: str, events: Optional[List[str]] = None):
        """创建仓库订阅信息"""
        now = datetime.now().timestamp()
        # 默认支持的事件类型更多了
        default_events = ["push", "issues", "pull_request", "release", "star"]
        return cls(
            repo_name=repo_name,
            events=set(events or default_events),  # 默认订阅更多类型的事件
            created_at=now,
            last_updated=now,
        )

    def update_events(self, events: List[str]):
        """更新订阅事件"""
        self.events = set(events)
        self.last_updated = datetime.now().timestamp()

    def add_event(self, event: str):
        """添加订阅事件"""
        self.events.add(event)
        self.last_updated = datetime.now().timestamp()

    def remove_event(self, event: str):
        """移除订阅事件"""
        if event in self.events:
            self.events.remove(event)
            self.last_updated = datetime.now().timestamp()

    def render(self) -> str:
        """渲染订阅信息"""
        events_str = ", ".join(sorted(self.events))
        created_time = datetime.fromtimestamp(self.created_at).strftime("%Y-%m-%d %H:%M:%S")
        return f"* {self.repo_name} (订阅事件: {events_str}, 创建时间: {created_time})"


class ChatSubscriptions(BaseModel):
    """会话订阅数据"""

    subscriptions: Dict[str, RepoSubscription] = Field(default_factory=dict)

    class Config:
        extra = "ignore"

    async def subscribe_repo(self, repo_name: str, events: Optional[List[str]] = None) -> RepoSubscription:
        """订阅仓库"""
        if repo_name in self.subscriptions:
            if events:
                self.subscriptions[repo_name].update_events(events)
            return self.subscriptions[repo_name]

        sub = RepoSubscription.create(repo_name, events)
        self.subscriptions[repo_name] = sub
        return sub

    async def unsubscribe_repo(self, repo_name: str) -> bool:
        """取消订阅仓库"""
        if repo_name in self.subscriptions:
            del self.subscriptions[repo_name]
            return True
        return False

    def get_subscription(self, repo_name: str) -> Optional[RepoSubscription]:
        """获取仓库订阅信息"""
        return self.subscriptions.get(repo_name)

    def is_subscribed(self, repo_name: str, event: Optional[str] = None) -> bool:
        """检查是否订阅了仓库的指定事件"""
        if repo_name not in self.subscriptions:
            return False
        if event is None:
            return True
        return event in self.subscriptions[repo_name].events

    def render_prompts(self) -> str:
        """渲染提示词"""
        if not self.subscriptions:
            return "当前没有GitHub仓库订阅 (使用 `subscribe_github_repo` 添加订阅)"

        subscriptions_str = "\n".join([sub.render() for sub in self.subscriptions.values()])
        return f"GitHub订阅仓库列表:\n{subscriptions_str}"
