"""
视频内容拆解 - 调用阿里云百炼 qwen-vl-plus 分析视频内容
依赖: pip install openai python-dotenv
"""

import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 配置
load_dotenv(Path(__file__).parent / ".env")

# 百炼 API 配置
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen3.6-plus"

SYSTEM_PROMPT = "你是一个视频拆解专家"

USER_PROMPT = """请对这条抖音短视频做完整的内容拆解，按以下结构输出：

1. 【基础规格】时长、画幅比例、是否有字幕、是否有背景音乐/BGM、是否有旁白/口播

2. 【内容结构拆解】按时间轴逐段拆解（精确到秒）：
 - 每段的画面内容描述
 - 镜头类型（特写/中景/全景/俯拍/仰拍等）
 - 人物出镜情况（真人/手/产品特写）
 - 字幕/文字内容（完整转录）
 - 音频内容（口播台词完整转录 + BGM描述）

3. 【爆款钩子分析】
 - 开头3秒用了什么钩子留住用户
 - 标题/话题词策略
 - 痛点/利益点是如何植入的

4. 【产品卖点提炼】视频中展示了哪些产品卖点，如何呈现的

5. 【视觉呈现手法】BGM节奏、剪辑节奏、字幕风格、特效/转场

6. 【口播脚本完整转录】逐句转录全部口播内容，标注时间点

7. 【复刻关键点】如果要完全复刻这条视频，最核心需要注意的5个要点是什么"""


def analyze_video(video_url: str) -> str:
    """
    调用百炼视觉模型分析视频内容，返回 Markdown 格式的拆解结果。

    Args:
        video_url: 视频的 CDN 直链

    Returns:
        Markdown 格式的视频拆解文本
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError(
            "未设置 DASHSCOPE_API_KEY，请在 scripts/.env 中配置百炼 API Key"
        )

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {"url": video_url},
                    },
                    {
                        "type": "text",
                        "text": USER_PROMPT,
                    },
                ],
            },
        ],
        extra_body={"enable_thinking": False},
    )

    return completion.choices[0].message.content


def analyze_and_save(video_url: str, save_dir: str | None = None, video_name: str = "", upload_feishu: bool = True) -> dict:
    """
    分析视频并将结果保存为 Word 文档，可选上传到飞书。

    Args:
        video_url: 视频CDN直链
        save_dir: 保存目录（为空则保存到当前目录）
        video_name: 视频名称（必填，用于文件命名，如 "氨糖带货"）
        upload_feishu: 是否上传到飞书（默认 True）

    Returns:
        包含 local_path 和 feishu_url（如有）的字典
    """
    from pathlib import Path
    from md_to_docx import md_to_docx

    if not video_name:
        raise ValueError("video_name 不能为空，必须提供视频名称用于文件命名")

    result = analyze_video(video_url)

    # 文件名格式：<视频名称>-拆解报告.docx
    filename = f"{video_name}-拆解报告.docx"

    if save_dir:
        save_path = Path(save_dir) / filename
    else:
        save_path = Path.cwd() / filename

    save_path.parent.mkdir(parents=True, exist_ok=True)
    md_to_docx(result, str(save_path))

    output = {"local_path": str(save_path), "feishu_url": ""}

    # 上传到飞书
    if upload_feishu:
        try:
            from upload_feishu import upload_docx_to_feishu
            feishu_result = upload_docx_to_feishu(
                str(save_path),
                doc_name=f"{video_name}-拆解报告",
                video_name=video_name,
            )
            output["feishu_url"] = feishu_result.get("url", "")
        except Exception as e:
            print(f"  飞书上传失败（不影响本地保存）: {e}")

    return output


def main():
    import argparse

    parser = argparse.ArgumentParser(description="调用百炼 qwen3.6-plus 分析视频内容")
    parser.add_argument("video_url", help="视频CDN直链")
    parser.add_argument("save_dir", nargs="?", default=None, help="拆解报告保存目录")
    parser.add_argument("--video-name", default="", help="视频名称（用于文件命名，如 '氨糖带货'）")
    parser.add_argument("--base-dir", default=None, help="工作根目录（与save_dir二选一，会自动创建qwen_video子目录）")

    args = parser.parse_args()

    print("正在分析视频内容，请稍候（可能需要1-2分钟）...\n")

    try:
        result = analyze_video(args.video_url)
        print(result)

        # 确定保存目录
        save_dir = args.save_dir
        if not save_dir and args.base_dir:
            from datetime import date
            today = date.today().strftime("%Y%m%d")
            save_dir = str(Path(args.base_dir) / "qwen_video" / today)

        if save_dir:
            video_name = args.video_name
            if not video_name:
                print("错误: 必须通过 --video-name 指定视频名称")
                sys.exit(1)
            filename = f"{video_name}-拆解报告.docx"
            save_path = Path(save_dir) / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)
            from md_to_docx import md_to_docx
            md_to_docx(result, str(save_path))
            print(f"\n{'='*60}")
            print(f"拆解报告已保存: {save_path}")

            # 上传到飞书
            try:
                from upload_feishu import upload_docx_to_feishu
                feishu_result = upload_docx_to_feishu(
                    str(save_path),
                    doc_name=f"{video_name}-拆解报告",
                    video_name=video_name,
                )
                print(f"飞书文档: {feishu_result.get('url', '')}")
            except Exception as e:
                print(f"飞书上传跳过: {e}")

    except ValueError as e:
        print(f"配置错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"分析失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
