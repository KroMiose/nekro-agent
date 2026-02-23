"""轻量化数据库迁移脚本

直接读取 DB 配置，避免加载完整 NA 模块（跳过 os_env 的 chmod 等启动副作用）。

DB 配置解析优先级：
  1. NEKRO_USE_ENV_DATABASE=true 或 NEKRO_RUN_IN_DOCKER=true → 读 NEKRO_POSTGRES_* 环境变量
  2. 否则 → 读 {NEKRO_DATA_DIR}/configs/nekro-agent.yaml 配置文件

执行顺序：
  1. fix_migrations  —— 自动修复 aerich 旧格式迁移文件（补充 MODELS_STATE 字段）
  2. init            —— 初始化 aerich 迁移状态
  3. upgrade         —— 执行所有未应用的迁移 SQL
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import quote_plus


def _load_env_file(env_file: str = ".env.dev") -> None:
    """简单解析 .env 文件并写入 os.environ（不覆盖已有变量）。"""
    p = Path(env_file)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), val)


def _build_db_url() -> str:
    """解析数据库连接 URL，不依赖任何 nekro_agent 模块。"""
    # poe 已经通过 envfile 加载了 .env.dev；脚本直接运行时手动加载
    _load_env_file(".env.dev")

    use_env = os.environ.get("NEKRO_USE_ENV_DATABASE", "false").lower() == "true"
    run_in_docker = os.environ.get("NEKRO_RUN_IN_DOCKER", "") != ""

    if use_env or run_in_docker:
        # 从环境变量读取（Docker / dev 模式）
        host = os.environ.get("NEKRO_POSTGRES_HOST", "localhost")
        port = os.environ.get("NEKRO_POSTGRES_PORT", "5432")
        user = os.environ.get("NEKRO_POSTGRES_USER", "nekro_agent")
        password = os.environ.get("NEKRO_POSTGRES_PASSWORD", "nekro_agent")
        db = os.environ.get("NEKRO_POSTGRES_DATABASE", "nekro_agent")
    else:
        # 从配置文件读取（生产模式）
        data_dir = os.environ.get("NEKRO_DATA_DIR", "./data/nekro_agent")
        config_path = Path(data_dir) / "configs" / "nekro-agent.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {config_path}，"
                "请设置 NEKRO_USE_ENV_DATABASE=true 或确认配置文件路径"
            )
        import yaml  # pyyaml 是项目依赖，可以直接使用

        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        host = cfg.get("POSTGRES_HOST", "127.0.0.1")
        port = str(cfg.get("POSTGRES_PORT", 5432))
        user = cfg.get("POSTGRES_USER", "nekro_agent")
        password = cfg.get("POSTGRES_PASSWORD", "nekro_agent")
        db = cfg.get("POSTGRES_DATABASE", "nekro_agent")

    return f"postgres://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


def _build_tortoise_config() -> dict:
    """构建最小化 Tortoise ORM 配置。

    upgrade 只执行迁移 SQL，aerich.models 仅用于追踪版本记录，
    无需导入完整的 nekro_agent.models。
    """
    try:
        from tzlocal import get_localzone

        tz = str(get_localzone())
    except Exception:
        tz = "UTC"

    return {
        "connections": {"default": _build_db_url()},
        "apps": {
            "models": {
                "models": ["aerich.models"],
                "default_connection": "default",
            },
        },
        "timezone": tz,
    }


async def _ensure_aerich_table(conn) -> None:
    await conn.execute_script(
        """
        CREATE TABLE IF NOT EXISTS "aerich" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "version" VARCHAR(255) NOT NULL,
            "app" VARCHAR(100) NOT NULL,
            "content" JSONB NOT NULL
        );
        """
    )


async def main() -> None:
    from aerich import Command
    from tortoise import Tortoise

    config = _build_tortoise_config()
    await Tortoise.init(config=config)

    conn = Tortoise.get_connection("default")
    migrations_dir = Path("migrations/models")
    if not migrations_dir.exists() or not any(migrations_dir.iterdir()):
        print("[db-migrate] 未检测到迁移文件，跳过")
        await Tortoise.close_connections()
        return

    command = Command(config, app="models", location="./migrations")

    # 1. 修复旧格式迁移文件（补充 aerich 0.6+ 所需的 MODELS_STATE 字段）
    try:
        fixed = await command.fix_migrations()
        if fixed:
            print(f"[db-migrate] 已修复旧格式迁移文件: {fixed}")
    except Exception as e:
        print(f"[db-migrate] fix_migrations 跳过: {e}")

    # 2. 初始化 aerich
    await command.init()

    # 3. 确保 aerich 追踪表存在
    await _ensure_aerich_table(conn)

    # 4. 执行待应用的迁移
    migrated = await command.upgrade()
    if migrated:
        print(f"[db-migrate] 已应用迁移: {migrated}")
    else:
        print("[db-migrate] 无待执行迁移，数据库已是最新")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
