import os
import sys
from pathlib import Path

from .utils import publish_package


def main():
    # 设置 poetry 创建项目内虚拟环境
    os.system("poetry config virtualenvs.in-project true")

    print("Publishing package...")
    publish_package()
    exit(0)
