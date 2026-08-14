from nekro_agent.routers.mcp import _apply_server_owned_validation


def test_auto_inject_update_preserves_validation_when_connection_config_unchanged() -> None:
    entry = {
        "name": "fetch",
        "type": "http",
        "url": "https://example.test/mcp",
        "headers": {"Authorization": "Bearer client"},
        "auto_inject": False,
        "validation": {"status": "validated", "server_name": "client-spoof"},
    }
    prev = {
        "name": "fetch",
        "type": "http",
        "url": "https://example.test/mcp",
        "headers": {"Authorization": "Bearer client"},
        "auto_inject": True,
        "validation": {"status": "validated", "server_name": "fetch", "tools_count": 3},
    }

    _apply_server_owned_validation(entry, prev)

    assert entry["validation"] == {"status": "validated", "server_name": "fetch", "tools_count": 3}


def test_auto_inject_update_resets_validation_when_url_changes() -> None:
    entry = {
        "name": "fetch",
        "type": "http",
        "url": "https://new.example.test/mcp",
        "headers": {"Authorization": "Bearer client"},
        "validation": {"status": "validated", "server_name": "client-spoof"},
    }
    prev = {
        "name": "fetch",
        "type": "http",
        "url": "https://old.example.test/mcp",
        "headers": {"Authorization": "Bearer client"},
        "validation": {"status": "validated", "server_name": "fetch", "tools_count": 3},
    }

    _apply_server_owned_validation(entry, prev)

    assert entry["validation"] == {"status": "unvalidated"}


def test_auto_inject_update_resets_validation_when_stdio_command_changes() -> None:
    entry = {
        "name": "local-tools",
        "type": "stdio",
        "command": "uvx",
        "args": ["new-package"],
        "env": {},
        "validation": {"status": "validated", "server_name": "client-spoof"},
    }
    prev = {
        "name": "local-tools",
        "type": "stdio",
        "command": "npx",
        "args": ["old-package"],
        "env": {},
        "validation": {"status": "validated", "server_name": "old-package"},
    }

    _apply_server_owned_validation(entry, prev)

    assert entry["validation"] == {"status": "unvalidated"}
