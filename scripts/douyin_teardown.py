"""
抖音分享链接解析 - 获取视频直链（无水印）
返回 Markdown 格式的解析结果
依赖: pip install requests
"""

import re
import sys
import json
import requests


def get_video_url(share_url: str) -> dict:
    """通过抖音分享链接获取视频直链（无水印）"""

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/16.6 Mobile/15E148 Safari/604.1",
    }

    # 1. 解析短链接，跟随重定向获取视频ID
    resp = requests.get(share_url, headers=headers, allow_redirects=True, timeout=10)
    final_url = resp.url

    # 从URL中提取视频ID
    video_id = _extract_video_id(final_url, resp)
    if not video_id:
        raise ValueError(f"无法从URL中提取视频ID: {final_url}")

    # 2. 通过 iesdouyin 分享页面获取视频数据
    share_page_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
    resp = requests.get(share_page_url, headers=headers, timeout=10)

    if resp.status_code != 200:
        raise ValueError(f"请求分享页面失败，状态码: {resp.status_code}")

    # 3. 从页面中提取 _ROUTER_DATA JSON 数据
    router_match = re.search(
        r"<script>window\._ROUTER_DATA\s*=\s*(.*?)</script>",
        resp.text,
        re.DOTALL,
    )

    if not router_match:
        raise ValueError("无法从页面中找到视频数据")

    raw_json = router_match.group(1)
    data = json.loads(raw_json)

    # 4. 从 JSON 中递归提取视频信息
    video_info = _extract_video_info(data)

    if not video_info.get("video_url"):
        raise ValueError("无法从页面数据中提取视频链接")

    video_info["video_id"] = video_id

    # 5. 获取无水印直链（将 playwm 替换为 play）
    video_url = video_info["video_url"]
    video_url = video_url.replace("/playwm/", "/play/")
    video_url = video_url.replace("playwm/?", "play/?")

    # 跟随重定向获取最终的 CDN 直链
    try:
        cdn_resp = requests.head(
            video_url, headers=headers, allow_redirects=True, timeout=10
        )
        if cdn_resp.status_code == 200:
            video_info["video_url_cdn"] = cdn_resp.url
    except requests.RequestException:
        pass

    video_info["video_url"] = video_url
    return video_info


def _extract_video_id(url: str, resp=None) -> str | None:
    """从URL或重定向历史中提取视频ID"""
    match = re.search(r"/video/(\d+)", url)
    if match:
        return match.group(1)

    match = re.search(r"/note/(\d+)", url)
    if match:
        return match.group(1)

    if resp and resp.history:
        for r in resp.history:
            loc = r.headers.get("Location", "")
            m = re.search(r"/video/(\d+)", loc)
            if m:
                return m.group(1)

    return None


def _extract_video_info(data: dict) -> dict:
    """从 _ROUTER_DATA 中提取视频信息"""
    result = {
        "title": "",
        "author": "",
        "cover": "",
        "video_url": "",
    }

    def find_in_obj(obj, depth=0):
        if depth > 20:
            return
        if isinstance(obj, dict):
            if "play_addr" in obj and not result["video_url"]:
                play_addr = obj["play_addr"]
                if isinstance(play_addr, dict):
                    url_list = play_addr.get("url_list", [])
                    if url_list:
                        result["video_url"] = url_list[0]

            if "desc" in obj and not result["title"]:
                desc = obj["desc"]
                if isinstance(desc, str) and len(desc) > 1:
                    result["title"] = desc

            if "nickname" in obj and not result["author"]:
                nickname = obj["nickname"]
                if isinstance(nickname, str) and len(nickname) > 0:
                    result["author"] = nickname

            if "cover" in obj and not result["cover"]:
                cover = obj["cover"]
                if isinstance(cover, dict):
                    cover_urls = cover.get("url_list", [])
                    if cover_urls:
                        result["cover"] = cover_urls[0]

            for v in obj.values():
                find_in_obj(v, depth + 1)

        elif isinstance(obj, list):
            for item in obj:
                find_in_obj(item, depth + 1)

    find_in_obj(data)
    return result


def format_markdown(result: dict) -> str:
    """将解析结果格式化为 Markdown 文本"""
    lines = []
    lines.append(f"# {result.get('title', '未知标题')}")
    lines.append("")

    if result.get("author"):
        lines.append(f"**作者**: {result['author']}")
    lines.append(f"**视频ID**: {result['video_id']}")
    lines.append("")

    lines.append("## 视频直链（无水印）")
    lines.append("")
    lines.append(f"```")
    lines.append(result["video_url"])
    lines.append(f"```")
    lines.append("")

    if result.get("video_url_cdn"):
        lines.append("## CDN直链（可直接下载）")
        lines.append("")
        lines.append(f"```")
        lines.append(result["video_url_cdn"])
        lines.append(f"```")
        lines.append("")

    if result.get("cover"):
        lines.append("## 封面图")
        lines.append("")
        lines.append(f"![封面]({result['cover']})")
        lines.append("")

    return "\n".join(lines)


def teardown(share_url: str) -> str:
    """
    主入口：解析抖音分享链接，返回 Markdown 格式结果。
    
    Args:
        share_url: 抖音分享链接
        
    Returns:
        Markdown 格式的解析结果文本
        
    Raises:
        ValueError: 解析失败时抛出
    """
    result = get_video_url(share_url)
    return format_markdown(result)


def main():
    if len(sys.argv) < 2:
        print("用法: python douyin_teardown.py <分享链接>")
        sys.exit(1)

    url = sys.argv[1]

    try:
        markdown_output = teardown(url)
        print(markdown_output)
    except ValueError as e:
        print(f"解析失败: {e}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"网络请求失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
