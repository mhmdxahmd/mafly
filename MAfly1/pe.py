#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAFLYA体育直播 - FongMi/OK影视 Python 直播蜘蛛
实时抓取 17 个 M3U 源，过滤 @stymei 注释，保留 https://stymei. 域名，
合并返回 M3U 文本给壳子。
"""

import re
import requests


class Spider:

    def __init__(self):
        self.sources = [
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
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

    # ---------- 过滤规则 ----------
    def _should_filter(self, line):
        """
        返回 True 表示该行应被丢弃。
        规则：
          - 空行丢弃
          - 以 https://stymei. 开头的 URL 保留（不丢弃）
          - 含 @stymei 的行丢弃（广告注释）
          - 其他 # 注释行丢弃（避免干扰解析）
        """
        s = line.strip()
        if not s:
            return True
        if s.lower().startswith("https://stymei."):
            return False
        if "@stymei" in s:
            return True
        if s.startswith("#") and not s.startswith("#EXTINF") and not s.startswith("#EXTM3U"):
            return True
        return False

    # ---------- 抓取 ----------
    def _fetch(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=8)
            r.raise_for_status()
            # 有些源返回 gbk，统一按 utf-8 忽略错误解码
            return r.content.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    # ---------- 壳子入口 ----------
    def liveContent(self, url):
        lines = ["#EXTM3U"]

        for name, m3u_url in self.sources:
            raw = self._fetch(m3u_url)
            if not raw or "#EXTM3U" not in raw.upper():
                continue

            kept = []
            for ln in raw.splitlines():
                if self._should_filter(ln):
                    continue
                kept.append(ln.strip())

            # 只保留 #EXTINF 行 + 紧跟的 http 行，保证壳子能正确配对
            i = 0
            while i < len(kept):
                ln = kept[i]
                if ln.startswith("#EXTINF"):
                    # 统一 group-title 为本源名称
                    if 'group-title="' in ln:
                        ln = re.sub(r'group-title="[^"]*"', f'group-title="{name}"', ln)
                    else:
                        ln = ln.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{name}"', 1)

                    # 找下一行有效 http
                    j = i + 1
                    while j < len(kept) and not kept[j].startswith("http"):
                        # 跳过中间可能残留的 # 行
                        j += 1
                    if j < len(kept) and kept[j].startswith("http"):
                        lines.append(ln)
                        lines.append(kept[j])
                        i = j + 1
                        continue
                i += 1

        # 防止返回空壳
        if len(lines) <= 1:
            return "#EXTM3U\n"

        return "\n".join(lines)
