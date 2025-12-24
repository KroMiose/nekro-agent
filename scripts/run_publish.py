import os
import sys
from pathlib import Path

from .utils import publish_package


def main():
    # 检测使用哪个包管理器
    if Path("uv.lock").exists() and os.getenv("USE_UV", "false").lower() == "true":
        print("Publishing package with UV...")
        
        # 构建包
        ret = os.system("uv build")
        if ret != 0:
            print("Build failed!")
            exit(1)
        
        # 发布到 PyPI
        ret = os.system("uv publish")
        if ret != 0:
            print("Publish failed!")
            exit(1)
        
        print("Package published successfully!")
    else:
        print("Publishing package with Poetry...")
        os.system("poetry config virtualenvs.in-project true")
        publish_package()
    
    exit(0)
