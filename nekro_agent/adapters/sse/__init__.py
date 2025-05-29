"""
SSE 适配器
========

基于SSE (Server-Sent Events)实现双向通信的通用适配器，
支持各种平台客户端通过HTTP与NekroAgent交互。
"""

from .adapter import SSEAdapter

__all__ = ["SSEAdapter"]
