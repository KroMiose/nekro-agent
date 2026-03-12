from __future__ import annotations

import asyncio
import logging
import signal

_shutdown_event = asyncio.Event()
_signal_handlers_installed = False
_logger = logging.getLogger(__name__)


def mark_started() -> None:
    """Clear the shutdown flag when a new worker process starts."""
    _shutdown_event.clear()


def mark_shutting_down() -> None:
    """Signal long-lived tasks and stream handlers to exit quickly."""
    _shutdown_event.set()


def is_shutting_down() -> bool:
    return _shutdown_event.is_set()


def ensure_shutdown_signal_handlers() -> None:
    """Install process signal hooks so long-lived streams can exit early."""
    global _signal_handlers_installed

    if _signal_handlers_installed:
        return

    def _handle_shutdown_signal(signum: int) -> None:
        _logger.info("Received shutdown signal %s, marking runtime as shutting down", signum)
        mark_shutting_down()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            if loop is not None:
                loop.add_signal_handler(sig, _handle_shutdown_signal, sig)
            else:
                signal.signal(sig, lambda _signum, _frame, s=sig: _handle_shutdown_signal(s))
        except (NotImplementedError, RuntimeError, ValueError):
            continue

    _signal_handlers_installed = True
