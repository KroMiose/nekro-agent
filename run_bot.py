<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# 解析命令行参数
parser = argparse.ArgumentParser(description="NekroAgent Bot Runner")
parser.add_argument("--env", type=str, help="指定环境配置文件后缀，如 --env=dev 将使用 .env.dev")
parser.add_argument("--reload", action="store_true", help="启用自动重载功能")
parser.add_argument("--reload-dirs", nargs="*", help="指定要监控的重载目录")
parser.add_argument("--reload-excludes", nargs="*", help="指定要排除的文件/目录模式")
parser.add_argument("--docs", action="store_true", help="启用文档功能")
parser.add_argument("--load-test", action="store_true", help="启用加载测试功能")
parser.add_argument("--verbose", action="store_true", help="启用详细日志功能")
args = parser.parse_args()

# 🔧 准备 FastAPI 配置参数
fastapi_config = {}
if args.reload:
    fastapi_config.update(
        {
            "fastapi_reload": True,
            "fastapi_reload_dirs": args.reload_dirs or ["./nekro_agent", "./plugins"],
            "fastapi_reload_excludes": args.reload_excludes
            or [
                "*.pyc",
                "*.pyo",
                "*__pycache__*",
                "*.git*",
                "*/data/*",
                "*/logs/*",
                "*/sandboxes/*",
                "*/uploads/*",
                "*/frontend/*",
                "*/docker/*",
                "*/.venv/*",
                "*/node_modules/*",
            ],
            "fastapi_reload_delay": 0.5,
        },
    )

if args.docs:
    fastapi_config.update(
        {
            "fastapi_docs_url": "/docs",
            "fastapi_redoc_url": "/redoc",
            "fastapi_openapi_url": "/openapi.json",
        },
    )

env_file: Optional[Path] = None

# 处理环境文件参数
if args.env:
    env_file = Path(f".env.{args.env}")
    if not env_file.exists():
        raise FileNotFoundError(f"环境文件不存在: {env_file}")  # noqa: TRY301

# 向后兼容：检查旧的 --env= 格式
if not args.env:
    for arg in sys.argv:
        if arg.startswith("--env="):
            env_file = Path(f".env.{arg.split('=')[1]}")
            break

if env_file and not env_file.exists():
    raise FileNotFoundError(f"环境文件不存在: {env_file}")  # noqa: TRY301

# 添加 Nekro 环境变量到系统环境变量
if env_file:
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            if key.startswith("NEKRO_"):
                os.environ[key] = value

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
try:
    import nonebot
    from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

<<<<<<< HEAD
    # 🎯 使用 NoneBot 原生方式初始化，传入 FastAPI 配置
    nonebot.init(_env_file=env_file, **fastapi_config)
=======
<<<<<<< HEAD
    # 🎯 使用 NoneBot 原生方式初始化，传入 FastAPI 配置
    nonebot.init(_env_file=env_file, **fastapi_config)
=======
<<<<<<< HEAD
    # 🎯 使用 NoneBot 原生方式初始化，传入 FastAPI 配置
    nonebot.init(_env_file=env_file, **fastapi_config)
=======
    nonebot.init()
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

    driver = nonebot.get_driver()
    driver.register_adapter(ONEBOT_V11Adapter)
    nonebot.load_from_toml("pyproject.toml")
except Exception as e:
    import traceback

    traceback.print_exc()
    print(f"Nonebot Init Error: {e}")
    raise

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
# 创建应用实例供 uvicorn 导入（仅在 reload 模式下需要）
if args.reload:
    app = nonebot.get_asgi()


def main():
    try:
        # 🚀 显示启动信息
        if args.reload:
            print("🔄 自动重载模式已启用")
            print(f"📁 监控目录: {args.reload_dirs or ['./nekro_agent', './plugins']}")
            if args.reload_excludes:
                print(f"🚫 排除模式: {args.reload_excludes}")

            # 在 reload 模式下使用 uvicorn 直接启动
            import uvicorn

            uvicorn.run(
                "run_bot:app",
                host=str(driver.config.host) or "0.0.0.0",
                port=int(driver.config.port) or 8021,
                reload=True,
                reload_dirs=args.reload_dirs or ["./nekro_agent", "./plugins"],
                reload_excludes=args.reload_excludes
                or [
                    "*.pyc",
                    "*.pyo",
                    "*__pycache__*",
                    "*.git*",
                    "*/data/*",
                    "*/logs/*",
                    "*/sandboxes/*",
                    "*/uploads/*",
                    "*/frontend/*",
                    "*/docker/*",
                    "*/.venv/*",
                    "*/node_modules/*",
                ],
                reload_delay=0.5,
            )
        else:
            # 正常模式使用 NoneBot 原生启动
            if args.docs:
                print("📚 API 文档已启用: /docs, /redoc")
            nonebot.run(host=str(driver.config.host) or "0.0.0.0", port=int(driver.config.port) or 8021)
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======

def main():
    try:
        nonebot.run(host="0.0.0.0", port=8021)
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Plugin Load Test Error: {e}")
        raise


if __name__ == "__main__":
    main()
