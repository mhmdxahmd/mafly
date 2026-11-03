#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAFLYA体育直播 - FongMi/OK影视 Python 直播蜘蛛
壳子调用时实时抓取并过滤，直接返回 M3U 文本。
"""

import requests
import re

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }

    def _should_filter(self, line):
        """过滤含 @stymei 的行，但保留 https://stymei. 开头的 URL"""
        s = line.strip()
        if not s:
            return True
        if s.lower().startswith("https://stymei."):
            return False
        if "@stymei" in s:
            return True
        return False

    def _fetch(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=20)
            r.raise_for_status()
            return r.text
        except Exception:
            return ""

    def liveContent(self, url=""):
        """壳子调用的入口，返回合并后的 M3U 文本"""
        lines = ["#EXTM3U"]

        for name, m3u_url in self.sources:
            raw = self._fetch(m3u_url)
            if not raw:
                continue

            # 过滤广告注释行
            kept = [ln for ln in raw.splitlines() if not self._should_filter(ln)]
            text = "\n".join(kept).strip()

            if "#EXTM3U" not in text.upper():
                continue

            # 统一替换 group-title 为本源名称，方便壳子里分类展示
            current_extinf = None
            for ln in kept:
                stripped = ln.strip()
                if stripped.startswith("#EXTINF"):
                    # 把原来的 group-title 替换或追加为本源名称
                    if 'group-title="' in stripped:
                        stripped = re.sub(
                            r'group-title="[^"]*"',
                            f'group-title="{name}"',
                            stripped
                        )
                    else:
                        # 没有 group-title，插入一个
                        stripped = stripped.replace(
                            "#EXTINF:-1",
                            f'#EXTINF:-1 group-title="{name}"',
                            1
                        )
                    current_extinf = stripped
                    lines.append(current_extinf)
                elif stripped.startswith("#"):
                    # 跳过源文件里的 #EXTM3U 和多余注释
                    continue
                elif stripped.startswith("http"):
                    # 只保留紧跟在 #EXTINF 后的 URL
                    if current_extinf is not None:
                        lines.append(stripped)
                        current_extinf = None

        return "\n".join(lines)
