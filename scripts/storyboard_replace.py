"""
GPT-image2 分镜受控替换 - 基于原分镜大图生成替换后的新分镜

流程：
1. 上传原分镜图 + 替换素材图到云间平台获取 URL
2. 根据替换项构造提示词（参考 references/storyboard-replacement-gptimage2.md）
3. 调用云间 /api/tasks 创建生图任务（异步）
4. 轮询任务状态直到 succeeded，下载生成的新分镜图

依赖: pip install requests python-dotenv
"""

import os
import sys
import time
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

# 加载配置
load_dotenv(Path(__file__).parent / ".env")

BASE_URL = os.getenv("YUNJIAN_BASE_URL", "http://yunjian.ai")
TOKEN = os.getenv("YUNJIAN_TOKEN", "")
SITE_ID = os.getenv("YUNJIAN_SITE_ID", "10000")

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


def build_replacement_prompt(
    product: bool = False,
    person: bool = False,
    scene: bool = False,
) -> str:
    """
    根据替换项构造 GPT-image2 提示词。

    Args:
        product: 是否替换产品
        person: 是否替换人物
        scene: 是否替换场景

    Returns:
        完整的替换提示词
    """
    replacements = []
    keeps = []

    if product:
        replacements.append("产品为我上传的产品图")
    else:
        keeps.append("产品")

    if person:
        replacements.append("人物为我上传的人物参考")
    else:
        keeps.append("人物")

    if scene:
        replacements.append("场景为我上传的场景参考")
    else:
        keeps.append("场景")

    if not replacements:
        return ""

    replace_line = "只替换分镜图中的" + "，".join(replacements) + "。"
    keep_line = ""
    if keeps:
        keep_line = "、".join(keeps) + "保持原分镜图中的原样内容。"

    prompt = f"""请基于我上传的原分镜图进行受控替换。

{replace_line}

{keep_line}

其余内容必须与原分镜图保持完全一致。

禁止重新设计画面构图。
禁止修改镜头角度。
禁止修改运镜。
禁止修改景别。
禁止修改人物动作。
禁止修改画面节奏。
禁止修改光影关系。
禁止修改分镜结构。

保持与原分镜图完全一致的格子数量。

禁止新增、删除、合并、重排分镜格子。

人物动作、人物姿势、人物位置必须严格对齐原分镜图对应格子。

最终结果需实现与原分镜图的1:1视觉对齐。"""

    return prompt


def create_image_task(prompt: str, image_urls: list[str], size: str = "2160x3840") -> str:
    """
    创建 GPT-image2 生图任务，返回 task_id。

    Args:
        prompt: 替换提示词
        image_urls: 图片URL列表（第一张为原分镜图，后续为替换素材）
        size: 输出尺寸

    Returns:
        task_id
    """
    payload = {
        "type": "text_to_image",
        "provider": "vg",
        "model_id": "gpt-image-2",
        "input": {
            "prompt": prompt,
            "image_urls": image_urls,
        },
        "options": {
            "resolution": size,
            "response_format": "url",
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


def poll_task(task_id: str, timeout_seconds: int = 600, interval: int = 5) -> str:
    """
    轮询任务状态直到成功，返回生成的图片 URL。

    Args:
        task_id: 任务ID
        timeout_seconds: 超时时间（秒）
        interval: 轮询间隔（秒）

    Returns:
        生成的图片 URL
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

        if status == "succeeded":
            print(" 完成!")
            # 提取图片URL
            primary_url = result.get("result", {}).get("primary_url")
            if primary_url:
                return primary_url
            result_urls = result.get("result", {}).get("result_urls", [])
            if result_urls:
                return result_urls[0]
            raise ValueError(f"任务成功但未找到图片URL: {json.dumps(result, ensure_ascii=False)}")

        elif status == "failed":
            print(" 失败!")
            error = result.get("error", {})
            msg = error.get("message", "未知错误")
            raise RuntimeError(f"任务失败: {msg}")

        # 打印队列信息
        if i == 0:
            queue = result.get("queue")
            if queue and queue.get("ahead_count"):
                print(f" (前方{queue['ahead_count']}个任务)", end="", flush=True)

    raise TimeoutError(f"任务超时（{timeout_seconds}秒）")


def replace_storyboard(
    storyboard_path: str,
    product_path: str = "",
    person_path: str = "",
    scene_path: str = "",
    output_dir: str = "",
    size: str = "2160x3840",
) -> str:
    """
    完整的分镜替换流程。

    Args:
        storyboard_path: 原分镜大图路径
        product_path: 产品素材图路径（为空则不替换产品）
        person_path: 人物素材图路径（为空则不替换人物）
        scene_path: 场景素材图路径（为空则不替换场景）
        output_dir: 输出目录（为空则保存到原分镜同目录）
        size: 输出尺寸

    Returns:
        生成的新分镜图保存路径
    """
    has_product = bool(product_path)
    has_person = bool(person_path)
    has_scene = bool(scene_path)

    if not (has_product or has_person or has_scene):
        print("  所有项都沿用原样，无需替换")
        return storyboard_path

    # 1. 构造提示词
    print("[1/4] 构造替换提示词")
    prompt = build_replacement_prompt(
        product=has_product,
        person=has_person,
        scene=has_scene,
    )
    print(f"  替换项: {'产品 ' if has_product else ''}{'人物 ' if has_person else ''}{'场景' if has_scene else ''}")

    # 2. 上传图片获取 URL
    print("[2/4] 上传图片")
    image_urls = []

    # 原分镜图（必须第一张）
    print(f"  上传原分镜图: {storyboard_path}")
    storyboard_result = upload_image(storyboard_path)
    storyboard_url = storyboard_result.get("public_url") or storyboard_result.get("external_read_url")
    image_urls.append(storyboard_url)
    print(f"  -> {storyboard_url}")

    # 替换素材
    if has_product:
        print(f"  上传产品图: {product_path}")
        r = upload_image(product_path)
        url = r.get("public_url") or r.get("external_read_url")
        image_urls.append(url)
        print(f"  -> {url}")

    if has_person:
        print(f"  上传人物图: {person_path}")
        r = upload_image(person_path)
        url = r.get("public_url") or r.get("external_read_url")
        image_urls.append(url)
        print(f"  -> {url}")

    if has_scene:
        print(f"  上传场景图: {scene_path}")
        r = upload_image(scene_path)
        url = r.get("public_url") or r.get("external_read_url")
        image_urls.append(url)
        print(f"  -> {url}")

    # 3. 创建生图任务
    print("[3/4] 创建 GPT-image2 生图任务")
    task_id = create_image_task(prompt, image_urls, size=size)
    print(f"  任务ID: {task_id}")

    # 4. 轮询直到成功，获取图片URL
    generated_url = poll_task(task_id)
    print(f"  生成图片: {generated_url}")

    # 5. 下载生成的新分镜图
    print("[4/4] 下载新分镜图")
    if not output_dir:
        output_dir = str(Path(storyboard_path).parent)

    output_path = Path(output_dir) / "新分镜_替换后.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img_resp = requests.get(generated_url, timeout=60)
    img_resp.raise_for_status()
    output_path.write_bytes(img_resp.content)

    print(f"\n  新分镜已保存: {output_path}")

    return str(output_path)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GPT-image2 分镜受控替换")
    parser.add_argument("storyboard", help="原分镜大图路径")
    parser.add_argument("--product", default="", help="产品素材图路径")
    parser.add_argument("--person", default="", help="人物素材图路径")
    parser.add_argument("--scene", default="", help="场景素材图路径")
    parser.add_argument("--output-dir", default="", help="输出目录")
    parser.add_argument("--size", default="2160x3840", help="输出尺寸 (默认 2160x3840)")

    args = parser.parse_args()

    if not (args.product or args.person or args.scene):
        print("错误: 至少需要指定一个替换项 (--product / --person / --scene)")
        sys.exit(1)

    try:
        result_path = replace_storyboard(
            storyboard_path=args.storyboard,
            product_path=args.product,
            person_path=args.person,
            scene_path=args.scene,
            output_dir=args.output_dir,
            size=args.size,
        )
        print(f"\n完成! 新分镜: {result_path}")
    except Exception as e:
        print(f"\n替换失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
