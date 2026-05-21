"""
视频下载 + 按时间轴拆分 + 抽帧 + 场景检测 + 合成分镜大图

工作流程:
1. 下载视频到 qwen_video/<日期>/<内容名称>/
2. 解析拆解结果中的时间段，用 ffmpeg 拆分视频
3. 对每个片段：均匀抽帧(1fps) + 场景变化检测(threshold=0.25)
4. 将截帧合成有序大图（4-6列，最后一行尽量不空）

依赖: pip install requests Pillow
系统依赖: ffmpeg (需要在 PATH 中)
"""

import os
import re
import sys
import math
import subprocess
from datetime import date
from pathlib import Path

import requests
from PIL import Image


def download_video(video_url: str, save_dir: Path, filename: str = "original.mp4") -> Path:
    """下载视频到指定目录"""
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename

    if save_path.exists():
        print(f"  视频已存在，跳过下载: {save_path}")
        return save_path

    print(f"  正在下载视频...")
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/16.6 Mobile/15E148 Safari/604.1",
    }
    resp = requests.get(video_url, headers=headers, stream=True, timeout=60)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = downloaded / total * 100
                print(f"\r  下载进度: {pct:.1f}%", end="", flush=True)

    print(f"\n  下载完成: {save_path} ({downloaded / 1024 / 1024:.1f}MB)")
    return save_path


def parse_segments_json(segments_json: str) -> list[dict]:
    """
    解析时间段 JSON 字符串。
    
    格式: [{"start": 0, "end": 3}, {"start": 3, "end": 8}, ...]
    start/end 单位为秒（整数或浮点数）
    """
    import json as _json
    segments = _json.loads(segments_json)
    
    # 校验并排序
    valid = []
    for seg in segments:
        start = int(seg["start"])
        end = int(seg["end"])
        if end > start:
            valid.append({"start": start, "end": end})
    
    valid.sort(key=lambda x: x["start"])
    return valid


def split_video_by_segments(video_path: Path, segments: list[dict], output_dir: Path) -> list[Path]:
    """用 ffmpeg 按时间段拆分视频"""
    output_dir.mkdir(parents=True, exist_ok=True)
    split_files = []

    for i, seg in enumerate(segments):
        start = seg["start"]
        duration = seg["end"] - seg["start"]
        output_file = output_dir / f"segment_{i:03d}_{start}s-{seg['end']}s.mp4"

        if output_file.exists():
            split_files.append(output_file)
            continue

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(duration),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            str(output_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            split_files.append(output_file)
            print(f"  拆分片段 {i}: {start}s - {seg['end']}s -> {output_file.name}")
        else:
            print(f"  拆分片段 {i} 失败: {result.stderr[:200]}")

    return split_files


def extract_frames_uniform(video_path: Path, output_dir: Path, fps: int = 1) -> list[Path]:
    """均匀抽帧：从第0秒开始，每秒取整数时间点的帧（0s, 1s, 2s, 3s...）"""
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame_%04d.jpg"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"select='isnan(prev_selected_t)+gte(t-prev_selected_t\\,{fps})'",
        "-vsync", "vfr",
        "-q:v", "2",
        str(pattern),
    ]

    subprocess.run(cmd, capture_output=True, text=True)

    frames = sorted(output_dir.glob("frame_*.jpg"))
    return frames


def extract_frames_scene_change(video_path: Path, output_dir: Path, threshold: float = 0.45) -> list[Path]:
    """场景变化检测抽帧（阈值越高越严格，帧越少）"""
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "scene_%04d.jpg"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-q:v", "2",
        str(pattern),
    ]

    subprocess.run(cmd, capture_output=True, text=True)

    frames = sorted(output_dir.glob("scene_*.jpg"))
    return frames


def find_optimal_columns(n_frames: int, min_cols: int = 4, max_cols: int = 6) -> int:
    """
    找到最优列数（4-6），使最后一行空位最少。
    如果有多个列数空位相同，优先选较大的列数（视觉更紧凑）。
    """
    if n_frames == 0:
        return min_cols

    best_cols = min_cols
    best_empty = max_cols  # 最差情况

    for cols in range(min_cols, max_cols + 1):
        remainder = n_frames % cols
        empty = (cols - remainder) % cols  # 最后一行空位数
        if empty < best_empty:
            best_empty = empty
            best_cols = cols
        elif empty == best_empty and cols > best_cols:
            # 空位相同时选更大的列数
            best_cols = cols

    return best_cols


def compose_contact_sheet(
    frames: list[Path],
    output_path: Path,
    min_cols: int = 4,
    max_cols: int = 6,
    thumb_width: int = 480,
    padding: int = 4,
) -> Path | None:
    """
    将帧图片合成有序大图。
    从左到右排列，满一行换行。列数在 min_cols~max_cols 之间选最优值。
    """
    if not frames:
        return None

    n = len(frames)
    cols = find_optimal_columns(n, min_cols, max_cols)
    rows = math.ceil(n / cols)

    # 读取第一张图获取比例
    sample = Image.open(frames[0])
    aspect = sample.height / sample.width
    thumb_height = int(thumb_width * aspect)
    sample.close()

    # 创建画布
    canvas_width = cols * thumb_width + (cols + 1) * padding
    canvas_height = rows * thumb_height + (rows + 1) * padding
    canvas = Image.new("RGB", (canvas_width, canvas_height), (30, 30, 30))

    for idx, frame_path in enumerate(frames):
        row = idx // cols
        col = idx % cols

        x = padding + col * (thumb_width + padding)
        y = padding + row * (thumb_height + padding)

        img = Image.open(frame_path)
        img = img.resize((thumb_width, thumb_height), Image.LANCZOS)
        canvas.paste(img, (x, y))
        img.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, quality=90)
    print(f"  合成大图: {output_path} ({cols}列 x {rows}行, {n}帧)")
    return output_path


def process_video(
    video_url: str,
    segments: list[dict],
    content_name: str = "",
    base_dir: Path | None = None,
    analysis_text: str = "",
) -> dict:
    """
    完整处理流程：下载 -> 拆分 -> 抽帧 -> 合成大图

    Args:
        video_url: 视频CDN直链
        segments: 时间段列表，如 [{"start": 0, "end": 3}, ...]
        content_name: 内容名称（用于目录命名，为空则自动生成）
        base_dir: 基础目录，默认为当前目录
        analysis_text: 拆解报告文本，非空则保存到视频目录

    Returns:
        包含各路径信息的字典
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # 1. 创建目录结构: qwen_video/<日期>/<内容名称>/
    today = date.today().strftime("%Y%m%d")
    if not content_name:
        content_name = "video_teardown"

    # 清理文件名中的非法字符
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', content_name)
    safe_name = safe_name[:50]  # 限制长度

    work_dir = base_dir / "qwen_video" / today / safe_name
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"工作目录: {work_dir}")
    print(f"{'='*60}")

    # 2. 下载视频
    print(f"\n[1/5] 下载视频")
    video_path = download_video(video_url, work_dir)

    # 保存拆解报告到视频目录
    if analysis_text:
        from md_to_docx import md_to_docx
        report_filename = f"{safe_name}-拆解报告.docx"
        report_path = work_dir / report_filename
        md_to_docx(analysis_text, str(report_path))
        print(f"  拆解报告已保存: {report_path.name}")

        # 上传到飞书
        try:
            from upload_feishu import upload_docx_to_feishu
            feishu_result = upload_docx_to_feishu(
                str(report_path),
                doc_name=f"{safe_name}-拆解报告",
                video_name=content_name,
            )
            print(f"  飞书文档: {feishu_result.get('url', '')}")
        except Exception as e:
            print(f"  飞书上传跳过: {e}")

    # 3. 拆分视频
    print(f"\n[2/5] 拆分视频")
    if not segments:
        print("  未提供时间段，按固定间隔(3秒)拆分")
        duration = get_video_duration(video_path)
        if duration > 0:
            interval = 3
            segments = [
                {"start": i, "end": min(i + interval, int(duration))}
                for i in range(0, int(duration), interval)
            ]

    split_dir = work_dir / "拆分"
    split_files = split_video_by_segments(video_path, segments, split_dir)
    print(f"  共拆分 {len(split_files)} 个片段")

    # 4. 对每个片段均匀抽帧 + 合成分镜大图
    print(f"\n[3/5] 片段抽帧")
    all_contact_sheets = []

    for i, split_file in enumerate(split_files):
        seg_name = split_file.stem
        print(f"\n  --- 片段 {i}: {seg_name} ---")

        # 均匀抽帧
        uniform_dir = split_dir / seg_name / "均匀抽帧"
        uniform_frames = extract_frames_uniform(split_file, uniform_dir, fps=1)
        print(f"  均匀抽帧: {len(uniform_frames)} 帧")

        # 合成片段大图
        if uniform_frames:
            sheet_path = split_dir / seg_name / f"分镜总览_{seg_name}.jpg"
            compose_contact_sheet(uniform_frames, sheet_path)
            all_contact_sheets.append(sheet_path)

    # 5. 对原视频整体做场景变化检测（阈值0.45）
    print(f"\n[4/5] 全视频场景变化检测 (threshold=0.45)")
    scene_dir = work_dir / "场景检测"
    scene_frames = extract_frames_scene_change(video_path, scene_dir, threshold=0.45)
    print(f"  检测到 {len(scene_frames)} 个场景变化帧")

    # 合成场景检测大图
    if scene_frames:
        scene_sheet_path = work_dir / "场景变化总览.jpg"
        compose_contact_sheet(scene_frames, scene_sheet_path)

    # 6. 全视频总览大图（所有均匀抽帧合成一张）
    print(f"\n[5/5] 生成全视频总览大图")
    all_uniform_dir = work_dir / "全视频抽帧"
    all_uniform_frames = extract_frames_uniform(video_path, all_uniform_dir, fps=1)
    if all_uniform_frames:
        overview_path = work_dir / "全视频时间轴总览.jpg"
        compose_contact_sheet(all_uniform_frames, overview_path)

    print(f"\n{'='*60}")
    print(f"处理完成!")
    print(f"工作目录: {work_dir}")
    print(f"  - 原始视频: {video_path.name}")
    print(f"  - 拆分目录: 拆分/ ({len(split_files)} 个片段)")
    print(f"  - 片段分镜大图: {len(all_contact_sheets)} 张")
    print(f"  - 场景检测: {len(scene_frames)} 帧 -> 场景变化总览.jpg")
    if (work_dir / "全视频时间轴总览.jpg").exists():
        print(f"  - 全视频总览: 全视频时间轴总览.jpg")
    print(f"{'='*60}")

    return {
        "work_dir": str(work_dir),
        "video_path": str(video_path),
        "split_dir": str(split_dir),
        "split_files": [str(f) for f in split_files],
        "contact_sheets": [str(f) for f in all_contact_sheets],
        "segments": segments,
    }


def get_video_duration(video_path: Path) -> float:
    """获取视频时长（秒）"""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        import json
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 0))
    return 0


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="视频下载+拆分+抽帧+合成大图")
    parser.add_argument("video_url", help="视频CDN直链")
    parser.add_argument("segments_json", help='时间段JSON，如 \'[{"start":0,"end":3}]\'')
    parser.add_argument("content_name", nargs="?", default="", help="内容名称（用于目录命名）")
    parser.add_argument("report_file", nargs="?", default="", help="拆解报告文件路径（.md 或 .docx）")
    parser.add_argument("--base-dir", default=None, help="工作目录（默认为当前目录）")

    args = parser.parse_args()

    # 解析时间段
    try:
        segments = parse_segments_json(args.segments_json)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"错误: 时间段JSON格式无效: {e}")
        sys.exit(1)

    # 读取拆解报告
    analysis_text = ""
    if args.report_file:
        report_path = Path(args.report_file)
        if report_path.exists():
            analysis_text = report_path.read_text(encoding="utf-8")
        else:
            print(f"警告: 拆解报告文件不存在: {args.report_file}")

    # 确定工作目录
    base_dir = Path(args.base_dir) if args.base_dir else None

    try:
        process_video(video_url=args.video_url, segments=segments,
                      content_name=args.content_name, base_dir=base_dir,
                      analysis_text=analysis_text)
    except Exception as e:
        print(f"\n处理失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
