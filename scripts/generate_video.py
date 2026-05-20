"""
Stage 6: 视频生成 - 调用云梦 2.0 (seedance-2-0) 生成视频

输入：
1. 提示词（单段或分段 Prompt）
2. 时长（4-15秒）
3. 分镜参考图（Stage 2 生成的新分镜图）

固定参数：480p、9:16、sound=true

依赖: pip install requests python-dotenv
"""

import os
import sys
import re
import time
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

# 加载配置
load_dotenv(Path(__file__).parent / ".env")

BASE_URL = os.getenv("YUNJIAN_BASE_URL", "https://ai.cnvp.cn")
TOKEN = os.getenv("YUNJIAN_TOKEN", "")
SITE_ID = os.getenv("YUNJIAN_SITE_ID", "10000")

MODEL_ID = "seedance-2-0"
PROVIDER = "vg"

# 导入上传工具
sys.path.insert(0, str(Path(__file__).parent))
from upload_image import upload_image


def _headers():
    """通用请求头"""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "site-id": SITE_ID,
        "Content-Type": "application/json",
    }


def create_video_task(prompt: str, duration: int, storyboard_url: str) -> str:
    """
    创建视频生成任务，返回 task_id。

    Args:
        prompt: 视频生成提示词
        duration: 视频时长（4-15秒）
        storyboard_url: 分镜参考图公网URL

    Returns:
        task_id
    """
    duration = max(4, min(15, duration))

    payload = {
        "provider": PROVIDER,
        "model_id": MODEL_ID,
        "type": "text_to_video",
        "input": {
            "prompt": prompt,
            "image_urls": [storyboard_url],
        },
        "options": {
            "duration": duration,
            "aspect_ratio": "9:16",
            "seedance_mode": "allround",
            "sound": True,
            "camera_fixed": False,
            "person_generation": False,
            "watermark": False,
        },
    }

    resp = requests.post(
        f"{BASE_URL}/api/tasks",
        headers=_headers(),
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()

    task_id = result.get("task_id")
    if not task_id:
        raise ValueError(f"未获取到 task_id，响应: {json.dumps(result, ensure_ascii=False)}")

    return task_id


def poll_video_task(task_id: str, timeout_seconds: int = 600, interval: int = 10) -> str:
    """
    轮询视频生成任务直到成功，返回视频 URL。

    Args:
        task_id: 任务ID
        timeout_seconds: 超时时间（秒）
        interval: 轮询间隔（秒）

    Returns:
        生成的视频 URL
    """
    max_attempts = timeout_seconds // interval
    print(f"  轮询中", end="", flush=True)

    for i in range(max_attempts):
        time.sleep(interval)
        print(".", end="", flush=True)

        resp = requests.get(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

        status = result.get("status", "")
        progress = result.get("progress", 0)

        if status == "succeeded":
            print(f" 完成!")
            primary_url = result.get("result", {}).get("primary_url")
            if primary_url:
                return primary_url
            result_urls = result.get("result", {}).get("result_urls", [])
            if result_urls:
                return result_urls[0]
            raise ValueError(f"任务成功但未找到视频URL: {json.dumps(result, ensure_ascii=False)}")

        elif status == "failed":
            print(f" 失败!")
            error = result.get("error", {})
            msg = error.get("message", "未知错误")
            raise RuntimeError(f"视频生成失败: {msg}")

        # 显示进度
        if i % 3 == 0 and progress > 0:
            print(f"({progress}%)", end="", flush=True)

        # 首次显示队列信息
        if i == 0:
            queue = result.get("queue")
            if queue and queue.get("ahead_count"):
                print(f" (前方{queue['ahead_count']}个任务)", end="", flush=True)

    raise TimeoutError(f"视频生成超时（{timeout_seconds}秒）")


def generate_video(
    prompt: str,
    duration: int,
    storyboard_image: str,
    output_dir: str = "",
    output_name: str = "generated_video.mp4",
) -> str:
    """
    生成单段视频。

    Args:
        prompt: 视频生成提示词
        duration: 视频时长（4-15秒）
        storyboard_image: 分镜参考图本地路径（会自动上传）
        output_dir: 输出目录
        output_name: 输出文件名

    Returns:
        生成的视频文件保存路径
    """
    # 上传分镜参考图
    print(f"  上传分镜参考图: {storyboard_image}")
    r = upload_image(storyboard_image)
    storyboard_url = r.get("public_url") or r.get("external_read_url")
    print(f"  -> {storyboard_url}")

    # 创建任务
    print(f"  创建视频生成任务 (duration={duration}s, 9:16, 480p)")
    task_id = create_video_task(prompt, duration, storyboard_url)
    print(f"  任务ID: {task_id}")

    # 轮询结果
    video_url = poll_video_task(task_id)
    print(f"  视频URL: {video_url}")

    # 下载视频
    if not output_dir:
        output_dir = "."
    output_path = Path(output_dir) / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  下载视频...")
    video_resp = requests.get(video_url, timeout=120)
    video_resp.raise_for_status()
    output_path.write_bytes(video_resp.content)

    size_mb = len(video_resp.content) / 1024 / 1024
    print(f"  已保存: {output_path} ({size_mb:.1f}MB)")

    return str(output_path)


def generate_from_segments(
    segments_file: str,
    storyboard_image: str,
    output_dir: str = "",
) -> list[str]:
    """
    从分段 Prompt 文件批量生成视频。

    解析文件中的每个 Segment，逐个提交生成任务。
    所有 Segment 共用同一张分镜参考图。

    Args:
        segments_file: 分段视频Prompt文件路径（或单段Prompt文件）
        storyboard_image: 分镜参考图本地路径
        output_dir: 输出目录

    Returns:
        生成的视频文件路径列表
    """
    content = Path(segments_file).read_text(encoding="utf-8")

    # 尝试按 Segment 分割
    segment_pattern = r"\[Segment\s+(\d+)\s*\|[^\]]*\]"
    segment_splits = list(re.finditer(segment_pattern, content))

    if segment_splits:
        # 多段模式
        segments = []
        for i, match in enumerate(segment_splits):
            start = match.start()
            end = segment_splits[i + 1].start() if i + 1 < len(segment_splits) else len(content)
            segment_text = content[start:end].strip()
            segments.append((match.group(1), segment_text))
    else:
        # 单段模式
        segments = [("1", content)]

    print(f"检测到 {len(segments)} 个 Segment")

    # 先上传分镜参考图（所有 Segment 共用）
    print(f"\n上传分镜参考图: {storyboard_image}")
    r = upload_image(storyboard_image)
    storyboard_url = r.get("public_url") or r.get("external_read_url")
    print(f"  -> {storyboard_url}\n")

    video_paths = []
    for seg_num, seg_text in segments:
        print(f"{'='*60}")
        print(f"Segment {seg_num}")
        print(f"{'='*60}")

        # 从 Segment 文本中提取时长
        duration_match = re.search(r"0\.00\s*-\s*([\d.]+)\s*s", seg_text)
        duration = 5  # 默认
        if duration_match:
            duration = int(float(duration_match.group(1)))
            duration = max(4, min(15, duration))

        print(f"  时长: {duration}s")

        # 创建任务
        print(f"  创建视频生成任务")
        task_id = create_video_task(seg_text, duration, storyboard_url)
        print(f"  任务ID: {task_id}")

        # 轮询结果
        try:
            video_url = poll_video_task(task_id)
            print(f"  视频URL: {video_url}")

            # 下载视频
            output_name = f"segment_{seg_num}.mp4"
            output_path = Path(output_dir) / output_name
            output_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"  下载视频...")
            video_resp = requests.get(video_url, timeout=120)
            video_resp.raise_for_status()
            output_path.write_bytes(video_resp.content)

            size_mb = len(video_resp.content) / 1024 / 1024
            print(f"  已保存: {output_path} ({size_mb:.1f}MB)")
            video_paths.append(str(output_path))

        except Exception as e:
            print(f"  Segment {seg_num} 生成失败: {e}")

        print()

    return video_paths


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Stage 6: 云梦 2.0 视频生成")
    parser.add_argument("prompt_file", help="视频Prompt文件路径（单段或分段）")
    parser.add_argument("storyboard_image", help="分镜参考图路径（Stage 2 生成的新分镜图）")
    parser.add_argument("--duration", type=int, default=0, help="视频时长（4-15秒，0=从Prompt自动检测）")
    parser.add_argument("--output-dir", default="", help="输出目录")

    args = parser.parse_args()

    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        print(f"错误: 文件不存在: {args.prompt_file}")
        sys.exit(1)

    if not Path(args.storyboard_image).exists():
        print(f"错误: 分镜参考图不存在: {args.storyboard_image}")
        sys.exit(1)

    output_dir = args.output_dir or str(prompt_path.parent)

    print(f"输出目录: {output_dir}\n")

    try:
        if args.duration > 0:
            # 指定时长，单段直接生成
            prompt_text = prompt_path.read_text(encoding="utf-8")
            generate_video(
                prompt=prompt_text,
                duration=args.duration,
                storyboard_image=args.storyboard_image,
                output_dir=output_dir,
            )
        else:
            # 自动检测：解析 Segment 逐个生成
            paths = generate_from_segments(
                segments_file=args.prompt_file,
                storyboard_image=args.storyboard_image,
                output_dir=output_dir,
            )
            print(f"\n{'='*60}")
            print(f"全部完成! 共生成 {len(paths)} 个视频")
            for p in paths:
                print(f"  - {p}")

    except Exception as e:
        print(f"\n生成失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
