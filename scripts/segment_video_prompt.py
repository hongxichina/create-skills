"""
Stage 5: 长视频 Prompt 智能分段

当 Stage 4 生成的最终 Video Prompt 总时长超过 15 秒时，
调用分段引擎将其拆分为多个 ≤15s 的独立 Segment Prompt。

每个 Segment 都是独立完整的视频生成指令，可单独发给视频模型。

依赖: pip install openai python-dotenv
"""

import os
import re
import sys
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

# 加载配置
load_dotenv(Path(__file__).parent / ".env")

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen3.6-plus"

# 分段提示词
REFERENCES_DIR = Path(__file__).parent.parent / "references"
SEGMENTATION_PROMPT_PATH = REFERENCES_DIR / "long-video-prompt-segmentation.md"


def _load_segmentation_prompt() -> str:
    """加载分段系统提示词（提取 markdown 代码块中的内容）"""
    content = SEGMENTATION_PROMPT_PATH.read_text(encoding="utf-8")
    start = content.find("```markdown")
    if start == -1:
        start = content.find("```")
    if start != -1:
        start = content.index("\n", start) + 1
        end = content.rfind("```")
        if end > start:
            return content[start:end].strip()
    lines = content.split("\n")
    return "\n".join(lines[2:]).strip()


def extract_total_duration(prompt_text: str) -> float:
    """从 Video Prompt 中提取总时长（秒）"""
    # 匹配 [Video Prompt | 0.00-58.00s, ...] 格式
    match = re.search(r"\[Video Prompt\s*\|\s*[\d.]+\s*-\s*([\d.]+)\s*s", prompt_text)
    if match:
        return float(match.group(1))

    # 匹配最后一个 Panel 的结束时间
    panel_times = re.findall(r"\[Panel\s+\d+\s*\|\s*[\d.]+-\s*([\d.]+)\s*s", prompt_text)
    if panel_times:
        return max(float(t) for t in panel_times)

    return 0.0


def segment_video_prompt(prompt_text: str) -> str:
    """
    对 Video Prompt 进行智能分段。

    如果总时长 ≤15s，原样返回。
    如果总时长 >15s，调用分段引擎拆分为多个 Segment。

    Args:
        prompt_text: Stage 4 生成的完整 Video Prompt 文本

    Returns:
        分段后的 Prompt 文本（或原样返回）
    """
    duration = extract_total_duration(prompt_text)

    if duration <= 15.0:
        print(f"  总时长 {duration:.1f}s ≤ 15s，无需分段")
        return prompt_text

    print(f"  总时长 {duration:.1f}s > 15s，需要分段")

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("未设置 DASHSCOPE_API_KEY")

    system_prompt = _load_segmentation_prompt()

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"请对以下完整 Video Prompt 进行智能分段：\n\n{prompt_text}",
            },
        ],
        extra_body={"enable_thinking": False},
    )

    return completion.choices[0].message.content


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Stage 5: 长视频 Prompt 智能分段")
    parser.add_argument("prompt_file", help="Stage 4 生成的最终视频Prompt文件路径")
    parser.add_argument("--output-dir", default="", help="输出目录（保存分段结果）")

    args = parser.parse_args()

    # 读取 Prompt 文件
    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        print(f"错误: 文件不存在: {args.prompt_file}")
        sys.exit(1)

    prompt_text = prompt_path.read_text(encoding="utf-8")

    # 检查时长
    duration = extract_total_duration(prompt_text)
    print(f"检测到视频总时长: {duration:.1f}s")

    if duration <= 15.0:
        print("总时长 ≤ 15s，无需分段，保持原样。")
        return

    print("正在进行智能分段，请稍候...\n")

    try:
        result = segment_video_prompt(prompt_text)
        print(result)

        # 保存到输出目录
        output_dir = args.output_dir or str(prompt_path.parent)
        output_path = Path(output_dir) / "分段视频Prompt.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        print(f"\n{'='*60}")
        print(f"分段结果已保存: {output_path}")

    except ValueError as e:
        print(f"配置错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"分段失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
