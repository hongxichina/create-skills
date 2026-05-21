"""
飞书文档上传 - 将本地 .docx 文件导入为飞书在线文档

流程：
1. 获取 tenant_access_token
2. 上传素材（upload_all）获取 file_token
3. 创建导入任务（import_task/create）
4. 轮询导入结果（import_task/get）
5. 返回飞书文档 URL

依赖: pip install requests python-dotenv
"""

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# 加载配置
load_dotenv(Path(__file__).parent / ".env")

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_FOLDER_TOKEN = os.getenv("FEISHU_FOLDER_TOKEN", "")  # 为空则上传到根目录
FEISHU_USER_ID = os.getenv("FEISHU_USER_ID", "")  # 自动共享给该用户

BASE_URL = "https://open.feishu.cn/open-apis"


def get_tenant_access_token() -> str:
    """
    获取 tenant_access_token（应用身份令牌）。

    Returns:
        tenant_access_token 字符串
    """
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        raise ValueError("未设置 FEISHU_APP_ID 或 FEISHU_APP_SECRET，请在 scripts/.env 中配置")

    resp = requests.post(
        f"{BASE_URL}/auth/v3/tenant_access_token/internal",
        json={
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {result.get('msg')}")

    return result["tenant_access_token"]


def create_folder(name: str, parent_token: str, token: str) -> str:
    """
    在飞书云空间创建文件夹。

    Args:
        name: 文件夹名称
        parent_token: 父文件夹 token（为空则在根目录创建）
        token: tenant_access_token

    Returns:
        新建文件夹的 token
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    payload = {
        "name": name,
        "folder_token": parent_token,
    }

    resp = requests.post(
        f"{BASE_URL}/drive/v1/files/create_folder",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise RuntimeError(f"创建文件夹失败: {result.get('msg')} (code={result.get('code')})")

    return result.get("data", {}).get("token", "")


def _share_folder_to_user(folder_token: str, token: str) -> None:
    """将文件夹共享给 FEISHU_USER_ID 配置的用户（full_access）。"""
    if not FEISHU_USER_ID:
        return
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "member_type": "userid",
        "member_id": FEISHU_USER_ID,
        "perm": "full_access",
        "type": "user",
    }
    try:
        requests.post(
            f"{BASE_URL}/drive/v1/permissions/{folder_token}/members?type=folder&need_notification=false",
            headers=headers,
            json=payload,
            timeout=30,
        )
    except Exception:
        pass  # 共享失败不阻断主流程


def ensure_folder_path(folder_names: list[str], root_token: str, token: str) -> str:
    """
    确保飞书云空间中按层级存在指定文件夹路径，不存在则逐级创建。

    Args:
        folder_names: 文件夹名称列表，如 ["2026-05-21", "氨糖带货"]
        root_token: 根文件夹 token
        token: tenant_access_token

    Returns:
        最终叶子文件夹的 token
    """
    current_token = root_token

    for name in folder_names:
        # 先查找是否已存在同名文件夹
        existing_token = _find_subfolder(name, current_token, token)
        if existing_token:
            current_token = existing_token
            print(f"  文件夹已存在: {name} -> {existing_token}")
        else:
            # 不存在则创建
            new_token = create_folder(name, current_token, token)
            current_token = new_token
            _share_folder_to_user(current_token, token)
            print(f"  创建文件夹: {name} -> {new_token}")

    return current_token


def _find_subfolder(name: str, parent_token: str, token: str) -> str:
    """
    在父文件夹中查找指定名称的子文件夹。

    Args:
        name: 要查找的文件夹名称
        parent_token: 父文件夹 token
        token: tenant_access_token

    Returns:
        找到的文件夹 token，未找到返回空字符串
    """
    headers = {
        "Authorization": f"Bearer {token}",
    }

    params = {
        "folder_token": parent_token,
        "order_by": "EditedTime",
        "direction": "DESC",
    }

    resp = requests.get(
        f"{BASE_URL}/drive/v1/files",
        headers=headers,
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        return ""

    files = result.get("data", {}).get("files", [])
    for f in files:
        if f.get("name") == name and f.get("type") == "folder":
            return f.get("token", "")

    return ""


def upload_file_to_feishu(file_path: str, token: str, folder_token: str = "") -> str:
    """
    上传本地文件到飞书云空间，返回 file_token。

    Args:
        file_path: 本地文件路径
        token: tenant_access_token
        folder_token: 目标文件夹 token

    Returns:
        file_token
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    file_size = path.stat().st_size
    if file_size > 20 * 1024 * 1024:
        raise ValueError(f"文件超过 20MB 限制: {file_size / 1024 / 1024:.1f}MB")

    headers = {
        "Authorization": f"Bearer {token}",
    }

    with open(path, "rb") as f:
        form_data = {
            "file_name": (None, path.name),
            "parent_type": (None, "explorer"),
            "parent_node": (None, folder_token or FEISHU_FOLDER_TOKEN or ""),
            "size": (None, str(file_size)),
            "file": (path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        }

        resp = requests.post(
            f"{BASE_URL}/drive/v1/files/upload_all",
            headers=headers,
            files=form_data,
            timeout=120,
        )

    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise RuntimeError(f"上传失败: {result.get('msg')} (code={result.get('code')})")

    file_token = result.get("data", {}).get("file_token")
    if not file_token:
        raise ValueError(f"未获取到 file_token: {result}")

    return file_token


def create_import_task(file_token: str, file_name: str, token: str, folder_token: str = "") -> str:
    """
    创建导入任务，将上传的 .docx 导入为飞书文档。

    Args:
        file_token: 上传素材返回的 file_token
        file_name: 导入后的文档名称
        token: tenant_access_token
        folder_token: 目标文件夹 token（为空则上传到根目录）

    Returns:
        导入任务 ticket
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    payload = {
        "file_extension": "docx",
        "file_token": file_token,
        "type": "docx",
        "file_name": file_name,
        "point": {
            "mount_type": 1,
            "mount_key": folder_token or "",
        },
    }

    resp = requests.post(
        f"{BASE_URL}/drive/v1/import_tasks",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise RuntimeError(f"创建导入任务失败: {result.get('msg')} (code={result.get('code')})")

    ticket = result.get("data", {}).get("ticket")
    if not ticket:
        raise ValueError(f"未获取到 ticket: {result}")

    return ticket


def poll_import_task(ticket: str, token: str, timeout_seconds: int = 60, interval: int = 2) -> dict:
    """
    轮询导入任务结果。

    Args:
        ticket: 导入任务 ID
        token: tenant_access_token
        timeout_seconds: 超时时间
        interval: 轮询间隔

    Returns:
        包含 token 和 url 的结果字典
    """
    headers = {
        "Authorization": f"Bearer {token}",
    }

    max_attempts = timeout_seconds // interval
    print(f"  轮询导入结果", end="", flush=True)

    for _ in range(max_attempts):
        time.sleep(interval)
        print(".", end="", flush=True)

        resp = requests.get(
            f"{BASE_URL}/drive/v1/import_tasks/{ticket}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("code") != 0:
            raise RuntimeError(f"查询导入结果失败: {result.get('msg')}")

        task_result = result.get("data", {}).get("result", {})
        job_status = task_result.get("job_status")

        if job_status == 0:
            print(" 完成!")
            return {
                "token": task_result.get("token", ""),
                "url": task_result.get("url", ""),
                "type": task_result.get("type", ""),
            }
        elif job_status in (3, 100, 101, 102, 103, 104, 105, 106, 108, 109, 110, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121):
            print(" 失败!")
            error_msg = task_result.get("job_error_msg", "未知错误")
            raise RuntimeError(f"导入失败 (status={job_status}): {error_msg}")

    raise TimeoutError(f"导入任务超时（{timeout_seconds}秒）")


def upload_docx_to_feishu(
    file_path: str,
    doc_name: str = "",
    folder_token: str = "",
    date_folder: str = "",
    video_name: str = "",
) -> dict:
    """
    完整流程：将本地 .docx 文件导入为飞书在线文档。

    支持按 <日期>/<视频名称> 的层级自动创建飞书文件夹。

    Args:
        file_path: 本地 .docx 文件路径
        doc_name: 飞书文档名称（为空则使用文件名）
        folder_token: 飞书文件夹 token（为空则使用 .env 中配置的，再为空则上传到根目录）
        date_folder: 日期文件夹名称，如 "2026-05-21"（为空则自动使用今天日期）
        video_name: 视频名称文件夹（为空则不创建子文件夹）

    Returns:
        包含 url 和 token 的字典
    """
    from datetime import date as _date

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if not doc_name:
        doc_name = path.stem  # 去掉扩展名

    root_token = folder_token or FEISHU_FOLDER_TOKEN or ""

    # 1. 获取 token
    print("[1/5] 获取飞书访问令牌")
    access_token = get_tenant_access_token()
    print("  -> 获取成功")

    # 2. 按 日期/视频名称 创建文件夹层级
    target_folder = root_token
    folder_path = []

    if not date_folder:
        date_folder = _date.today().strftime("%Y-%m-%d")
    folder_path.append(date_folder)

    if video_name:
        folder_path.append(video_name)

    if folder_path:
        print(f"[2/5] 确保飞书文件夹: {'/'.join(folder_path)}")
        target_folder = ensure_folder_path(folder_path, root_token, access_token)
    else:
        print("[2/5] 使用根文件夹")

    # 3. 上传素材
    print(f"[3/5] 上传文件: {path.name}")
    file_token = upload_file_to_feishu(file_path, access_token, target_folder)
    print(f"  -> file_token: {file_token}")

    # 4. 创建导入任务
    print(f"[4/5] 创建导入任务: {doc_name}")
    ticket = create_import_task(file_token, doc_name, access_token, target_folder)
    print(f"  -> ticket: {ticket}")

    # 5. 轮询结果
    print("[5/5] 等待导入完成")
    result = poll_import_task(ticket, access_token)
    print(f"  -> 飞书文档: {result['url']}")

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="将 .docx 文件导入为飞书在线文档")
    parser.add_argument("file_path", help=".docx 文件路径")
    parser.add_argument("--name", default="", help="飞书文档名称（默认使用文件名）")
    parser.add_argument("--folder", default="", help="飞书根文件夹 token（默认使用 .env 配置）")
    parser.add_argument("--date", default="", help="日期文件夹名称，如 2026-05-21（默认今天）")
    parser.add_argument("--video-name", default="", help="视频名称文件夹")

    args = parser.parse_args()

    try:
        result = upload_docx_to_feishu(
            file_path=args.file_path,
            doc_name=args.name,
            folder_token=args.folder,
            date_folder=args.date,
            video_name=args.video_name,
        )
        print(f"\n完成! 飞书文档链接: {result['url']}")
    except Exception as e:
        print(f"\n上传失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
