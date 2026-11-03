#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAFLYA体育直播 - OK影视直播接口自动生成
实时读取指定M3U源，过滤@stymei注释，保留https://stymei.域名
输出：maflya_live.json （OK影视可直接加载）
"""

import json
import re
import sys
import urllib.request
from urllib.error import URLError

# ========== 配置：直播源列表 ==========
SOURCES = [
    ("咖啡体育直播", "https://jsnzkpg.de5.net/all.m3u"),
    ("大米体育直播", "https://stymei.pages.dev/live.m3u"),
    ("88看球直播", "https://stymei1.pages.dev/live.m3u"),
    ("178体育直播", "https://stymei2.pages.dev/live.m3u"),
    ("310体育直播", "https://stymei3.pages.dev/live.m3u"),
    ("豆包体育直播", "https://stymei4.pages.dev/live.m3u"),
    ("鲸鱼体育直播", "https://stymei5.pages.dev/live.m3u"),
    ("看球通体育直播", "https://stymei6.pages.dev/live.m3u"),
    ("球吧体育直播", "https://stymei7.pages.dev/live.m3u"),
    ("松果体育直播", "https://stymei8.pages.dev/live.m3u"),
    ("天天体育直播", "https://stymei9.pages.dev/live.m3u"),
    ("一代体育直播", "https://stymei10.pages.dev/live.m3u"),
    ("JRKAN体育直播", "https://stymei11.pages.dev/live.m3u"),
    ("OK体育直播", "https://stymei12.pages.dev/live.m3u"),
    ("说球帝体育直播", "https://stymei13.pages.dev/live.m3u"),
    ("海星体育直播", "https://stymei14.pages.dev/live.m3u"),
    ("U球体育直播", "https://stymei15.pages.dev/live.m3u"),
]

OUTPUT_JSON = "maflya_live.json"

# ========== 过滤规则 ==========
def should_filter_line(line: str) -> bool:
    """
    判断该行是否应被过滤掉。
    规则：
      1. 包含 @stymei 的注释/广告行 -> 删除
      2. 但以 https://stymei. 开头的 URL -> 保留（不删）
    """
    stripped = line.strip()
    if not stripped:
        return True

    # 关键：如果是以 https://stymei. 开头的链接，绝不删除
    if stripped.lower().startswith("https://stymei."):
        return False

    # 如果包含 @stymei，视为广告注释，删除
    if "@stymei" in stripped:
        return True

    return False


def fetch_m3u(url: str) -> str:
    """抓取 M3U 文本"""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [错误] 抓取失败: {e}", file=sys.stderr)
        return ""


def build_lives_json():
    """构建 OK影视 的 lives JSON"""
    lives = []
    for name, url in SOURCES:
        print(f"[处理] {name} ...")
        raw = fetch_m3u(url)
        if not raw:
            print(f"  [跳过] 内容为空")
            continue

        # 按行过滤
        lines = raw.splitlines()
        kept = [ln for ln in lines if not should_filter_line(ln)]
        filtered_text = "\n".join(kept).strip()

        if not filtered_text or "#EXTM3U" not in filtered_text.upper():
            print(f"  [跳过] 过滤后无有效M3U内容")
            continue

        entry = {
            "name": f"* {name}",
            "type": 0,
            "url": url,          # OK影视会自己去拉这个 M3U
            "ua": "",
        }
        lives.append(entry)
        removed = len(lines) - len(kept)
        print(f"  [完成] 保留行数 {len(kept)}，过滤行数 {removed}")

    return {"lives": lives}


def main():
    print("=" * 50)
    print("MAFLYA体育直播 · OK影视接口生成器")
    print("=" * 50)

    data = build_lives_json()

    if not data["lives"]:
        print("[失败] 未生成任何有效直播源", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[成功] 已生成: {OUTPUT_JSON}")
    print(f"共 {len(data['lives'])} 个直播源分组")
    print("\nOK影视使用方法：")
    print("  1. 把 maflya_live.json 放到可访问的 HTTP 服务器或 GitHub Pages")
    print("  2. OK影视 -> 设置 -> 直播源 -> 添加上述 JSON 的 URL")
    print("  或直接把本地文件路径填入（部分版本支持 file://）")


if __name__ == "__main__":
    main()
