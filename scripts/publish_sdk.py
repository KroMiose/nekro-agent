"""
SSE SDK 发布脚本
================

用于独立发布 nekro-agent-sse-sdk 包到 PyPI
"""

import os
import shutil
import sys
from pathlib import Path


def main():
    """发布SSE SDK到PyPI"""
    # SDK目录
    sdk_dir = Path("nekro_agent/adapters/sse/sdk")
    
    if not sdk_dir.exists():
        print(f"错误: SDK目录不存在: {sdk_dir}")
        sys.exit(1)
    
    # 检查必要文件
    required_files = ["pyproject.toml", "README.md", "LICENSE"]
    for file in required_files:
        if not (sdk_dir / file).exists():
            print(f"错误: 缺少必要文件: {file}")
            sys.exit(1)
    
    print("=" * 60)
    print("开始发布 nekro-agent-sse-sdk")
    print("=" * 60)
    
    # 切换到SDK目录
    original_dir = Path.cwd()
    os.chdir(sdk_dir)
    
    try:
        # 清理旧的构建文件
        print("\n[1/4] 清理旧的构建文件...")
        for path in ["dist", "build", "*.egg-info"]:
            if Path(path).exists():
                if Path(path).is_dir():
                    shutil.rmtree(path)
                else:
                    Path(path).unlink()
        print("✓ 清理完成")
        
        # 构建包
        print("\n[2/4] 构建SDK包...")
        ret = os.system("uv build")
        if ret != 0:
            print("✗ 构建失败!")
            sys.exit(1)
        print("✓ 构建成功")
        
        # 检查构建产物
        print("\n[3/4] 检查构建产物...")
        dist_dir = Path("dist")
        if not dist_dir.exists() or not list(dist_dir.glob("*")):
            print("✗ 构建产物不存在!")
            sys.exit(1)
        
        print("构建产物:")
        for file in dist_dir.glob("*"):
            print(f"  - {file.name}")
        print("✓ 检查通过")
        
        # 发布到PyPI
        print("\n[4/4] 发布到PyPI...")
        print("提示: 如果需要使用测试PyPI，请设置环境变量:")
        print("  export UV_PUBLISH_URL=https://test.pypi.org/legacy/")
        print("  export UV_PUBLISH_USERNAME=__token__")
        print("  export UV_PUBLISH_PASSWORD=<your-test-pypi-token>")
        print()
        
        # 询问是否继续
        response = input("是否继续发布到PyPI? (y/n): ").strip().lower()
        if response != "y":
            print("取消发布")
            sys.exit(0)
        
        ret = os.system("uv publish")
        if ret != 0:
            print("✗ 发布失败!")
            print("\n提示: 请确保已设置PyPI凭证:")
            print("  export UV_PUBLISH_USERNAME=__token__")
            print("  export UV_PUBLISH_PASSWORD=<your-pypi-token>")
            sys.exit(1)
        
        print("✓ 发布成功!")
        print("\n" + "=" * 60)
        print("nekro-agent-sse-sdk 发布完成!")
        print("=" * 60)
        
    finally:
        # 切换回原目录
        os.chdir(original_dir)


if __name__ == "__main__":
    main()

