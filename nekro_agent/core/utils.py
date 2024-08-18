import os
import sys
from pathlib import Path
from typing import Any, Tuple


class ArgTypes:

    @staticmethod
    def _use_arg(arg_key: str, default: Any = None) -> Any:
        if arg_key in sys.argv:
            index = sys.argv.index(arg_key)
            if index + 1 < len(sys.argv):
                return sys.argv[index + 1]
        return default

    @staticmethod
    def Str(key: str, default: str = "") -> str:
        return str(ArgTypes._use_arg(key, default))

    @staticmethod
    def Int(key: str, default: int = 0) -> int:
        return int(ArgTypes._use_arg(key, default))

    @staticmethod
    def Float(key: str, default: float = 0.0) -> float:
        return float(ArgTypes._use_arg(key, default))

    @staticmethod
    def Bool(key: str) -> bool:
        return key in sys.argv


class OsEnvTypes:

    @staticmethod
    def _use_env(env_key: str, default: Any = None) -> Any:
        return os.environ.get(f"NEKRO_{env_key.upper()}", default)

    @staticmethod
    def Str(key: str, default: str = "") -> str:
        return str(OsEnvTypes._use_env(key, default))

    @staticmethod
    def Int(key: str, default: int = 0) -> int:
        return int(OsEnvTypes._use_env(key, default))

    @staticmethod
    def Float(key: str, default: float = 0.0) -> float:
        return float(OsEnvTypes._use_env(key, default))

    @staticmethod
    def Bool(key: str) -> bool:
        return str(OsEnvTypes._use_env(key, "false")).lower() == "true"
