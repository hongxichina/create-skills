"""
Stage 4: 最终 Video Prompt 编排

将 Stage 1 的拆解报告、Stage 2 的新分镜图、产品图等材料整合，
调用编排模型（qwen3.6-plus）生成可直接发送给视频生成模型的最终 Prompt。

依赖: pip install openai python-dotenv
"""

import os
import sys
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

# 加载配置
load_dotenv(Path(__file__).parent / ".env")

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen3.6-plus"

# 读取参考文档
REFERENCES_DIR = Path(__file__).parent.parent / "references"
SYSTEM_PROMPT_PATH = REFERENCES_DIR / "final-prompt-orchestration-system.md"
USER_TEMPLATE_PATH = REFERENCES_DIR / "final-prompt-orchestration-user.md"


def _load_system_prompt() -> str:
    """加载系统提示词（提取 markdown 代码块中的内容）"""
    content = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    # 提取 ```markdown ... ``` 之间的内容
    start = content.find("```markdown")
    if start == -1:
        start = content.find("```")
    if start != -1:
        start = content.index("\n", start) + 1
        end = content.rfind("```")
        if end > start:
            return content[start:end].strip()
    # 如果没有代码块，返回全文（去掉标题行）
    lines = content.split("\n")
    return "\n".join(lines[2:]).strip()


def _load_user_template() -> str:
    """加载用户任务模板（提取 markdown 代码块中的内容）"""
    content = USER_TEMPLATE_PATH.read_text(encoding="utf-8")
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


def generate_video_prompt(
    breakdown_text: str,
    storyboard_url: str,
    product_url: str,
    model_ref_url: str = "",
    scene_ref_url: str = "",
    srt_text: str = "",
) -> str:
    """
    调用编排模型生成最终 Video Prompt。

    Args:
        breakdown_text: Stage 1/3 的结构化拆解结果文本
        storyboard_url: Stage 2 新分镜图的公网URL
        product_url: 产品图的公网URL
        model_ref_url: 人物参考图URL（可选）
        scene_ref_url: 场景参考图URL（可选）
        srt_text: SRT字幕文本（可选）

    Returns:
        最终 Video Prompt 文本
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("未设置 DASHSCOPE_API_KEY")

    # 加载提示词
    system_prompt = _load_system_prompt()
    user_template = _load_user_template()

    # 填充用户模板
    # 替换 Original Video Breakdown 部分
    user_content = user_template.replace(
        "【Original Video Breakdown】\n在这里粘贴原视频结构化拆解结果",
        f"【Original Video Breakdown】\n{breakdown_text}",
    )

    # 替换 SRT 部分
    if srt_text:
        user_content = user_content.replace(
            "【SRT】\n如果有 SRT，在这里粘贴。\n如果没有 SRT，请按无口播处理。",
            f"【SRT】\n{srt_text}",
        )
    else:
        user_content = user_content.replace(
            "【SRT】\n如果有 SRT，在这里粘贴。\n如果没有 SRT，请按无口播处理。",
            "【SRT】\n无 SRT，按无口播处理。",
        )

    # 替换人物参考
    if model_ref_url:
        user_content = user_content.replace(
            "【Model Reference Image】\n如有，请使用用户上传的人物参考图；如无，则忽略。",
            f"【Model Reference Image】\n用户已上传人物参考图: {model_ref_url}",
        )
    else:
        user_content = user_content.replace(
            "【Model Reference Image】\n如有，请使用用户上传的人物参考图；如无，则忽略。",
            "【Model Reference Image】\n无人物参考图，以新分镜图中的人物为准。",
        )

    # 替换场景参考
    if scene_ref_url:
        user_content = user_content.replace(
            "【Scene Reference Image】\n如有，请使用用户上传的场景参考图；如无，则忽略。",
            f"【Scene Reference Image】\n用户已上传场景参考图: {scene_ref_url}",
        )
    else:
        user_content = user_content.replace(
            "【Scene Reference Image】\n如有，请使用用户上传的场景参考图；如无，则忽略。",
            "【Scene Reference Image】\n无场景参考图，以新分镜图中的场景为准。",
        )

    # 构造消息（多模态：文本 + 图片）
    user_message_content = [
        {"type": "text", "text": user_content},
        {
            "type": "image_url",
            "image_url": {"url": storyboard_url},
        },
        {
            "type": "image_url",
            "image_url": {"url": product_url},
        },
    ]

    if model_ref_url:
        user_message_content.append({
            "type": "image_url",
            "image_url": {"url": model_ref_url},
        })

    if scene_ref_url:
        user_message_content.append({
            "type": "image_url",
            "image_url": {"url": scene_ref_url},
        })

    # 调用模型
    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_content},
        ],
        extra_body={"enable_thinking": False},
    )

    return completion.choices[0].message.content


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Stage 4: 编排最终 Video Prompt")
    parser.add_argument("breakdown_file", help="拆解报告或结构化动作骨架文件路径")
    parser.add_argument("storyboard_url", help="新分镜图公网URL")
    parser.add_argument("product_url", help="产品图公网URL")
    parser.add_argument("--model-ref", default="", help="人物参考图URL")
    parser.add_argument("--scene-ref", default="", help="场景参考图URL")
    parser.add_argument("--srt", default="", help="SRT字幕文件路径")
    parser.add_argument("--output-dir", default="", help="输出目录（保存最终Prompt）")

    args = parser.parse_args()

    # 读取拆解报告
    breakdown_path = Path(args.breakdown_file)
    if not breakdown_path.exists():
        print(f"错误: 文件不存在: {args.breakdown_file}")
        sys.exit(1)
    breakdown_text = breakdown_path.read_text(encoding="utf-8")

    # 读取 SRT（如果有）
    srt_text = ""
    if args.srt:
        srt_path = Path(args.srt)
        if srt_path.exists():
            srt_text = srt_path.read_text(encoding="utf-8")
        else:
            print(f"警告: SRT文件不存在: {args.srt}")

    print("正在编排最终 Video Prompt，请稍候...\n")

    try:
        result = generate_video_prompt(
            breakdown_text=breakdown_text,
            storyboard_url=args.storyboard_url,
            product_url=args.product_url,
            model_ref_url=args.model_ref,
            scene_ref_url=args.scene_ref,
            srt_text=srt_text,
        )

        print(result)

        # 保存到输出目录
        if args.output_dir:
            from md_to_docx import md_to_docx
            output_path = Path(args.output_dir) / "最终视频Prompt.docx"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            md_to_docx(result, str(output_path))
            print(f"\n{'='*60}")
            print(f"最终 Video Prompt 已保存: {output_path}")

    except ValueError as e:
        print(f"配置错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"编排失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
