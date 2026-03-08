from __future__ import annotations

import asyncio

_shutdown_event = asyncio.Event()


def mark_started() -> None:
    """Clear the shutdown flag when a new worker process starts."""
    _shutdown_event.clear()


def mark_shutting_down() -> None:
    """Signal long-lived tasks and stream handlers to exit quickly."""
    _shutdown_event.set()


def is_shutting_down() -> bool:
    return _shutdown_event.is_set()
