"""
视频上传工具 - 上传本地视频到云间平台，返回公网可访问的 URL

流程与图片上传相同：创建直传票据 → PUT 到 COS → 通知后端完成 → 返回 public_url
依赖: pip install requests python-dotenv
"""

import os
import sys
import mimetypes
from pathlib import Path

import requests
from dotenv import load_dotenv

# 加载配置
load_dotenv(Path(__file__).parent / ".env")

BASE_URL = os.getenv("YUNJIAN_BASE_URL", "https://ai.cnvp.cn")
TOKEN = os.getenv("YUNJIAN_TOKEN", "")
SITE_ID = os.getenv("YUNJIAN_SITE_ID", "10000")


def _headers():
    """通用请求头"""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "site-id": SITE_ID,
        "Content-Type": "application/json",
    }


def upload_video(file_path: str) -> dict:
    """
    上传本地视频文件，返回包含 public_url 等信息的字典。

    Args:
        file_path: 本地视频文件路径

    Returns:
        {
            "public_url": "https://...",
            "preview_url": "https://...",
            "external_read_url": "https://...",
            "file_ext": ".mp4",
        }
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 推断 content_type
    content_type, _ = mimetypes.guess_type(str(path))
    if not content_type:
        content_type = "video/mp4"

    file_size = path.stat().st_size
    filename = path.name

    # Step 1: 创建直传票据
    create_resp = requests.post(
        f"{BASE_URL}/api/assets/direct-upload/create",
        headers=_headers(),
        json={
            "media_type": "video",
            "filename": filename,
            "content_type": content_type,
            "size_bytes": file_size,
        },
        timeout=30,
    )
    create_resp.raise_for_status()
    ticket = create_resp.json()

    upload_url = ticket["upload_url"]
    object_key = ticket["object_key"]
    file_ext = ticket.get("file_ext", path.suffix)

    # Step 2: PUT 上传到 COS（预签名地址，不需要 token）
    print(f"  上传中 ({file_size / 1024 / 1024:.1f}MB)...", end="", flush=True)
    with open(path, "rb") as f:
        put_resp = requests.put(
            upload_url,
            headers={"Content-Type": content_type},
            data=f,
            timeout=300,
        )
    put_resp.raise_for_status()
    print(" 完成")

    # Step 3: 通知后端上传完成
    complete_resp = requests.post(
        f"{BASE_URL}/api/assets/direct-upload/complete",
        headers=_headers(),
        json={
            "media_type": "video",
            "object_key": object_key,
            "content_type": content_type,
            "file_ext": file_ext,
        },
        timeout=30,
    )
    complete_resp.raise_for_status()
    result = complete_resp.json()

    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python upload_video.py <视频路径> [视频路径2] ...")
        print("")
        print("返回每个视频的公网 URL")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        try:
            result = upload_video(file_path)
            url = result.get("public_url") or result.get("external_read_url", "")
            print(f"{file_path} -> {url}")
        except Exception as e:
            print(f"{file_path} -> 上传失败: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
