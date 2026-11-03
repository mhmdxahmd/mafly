# coding=utf-8
import re
import sys
import requests
import json
from base.spider import Spider as BaseSpider

sys.path.append('..')


class Spider(BaseSpider):

    def getName(self):
        return "MAFLYA体育直播"

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # 源配置：分类名 -> m3u地址
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
        # 缓存：分类ID -> 频道列表
        self.channel_cache = {}

    def _should_filter(self, line):
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

    def _fetch_m3u(self, url):
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return ""

    def _parse_channels(self, m3u_text):
        """解析 M3U，返回 [{name, url}]"""
        channels = []
        lines = [ln.strip() for ln in m3u_text.splitlines() if not self._should_filter(ln)]
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.startswith("#EXTINF"):
                # 频道名：逗号后面
                name = ln.split(",")[-1].strip() if "," in ln else "未知频道"
                j = i + 1
                while j < len(lines) and not lines[j].startswith("http"):
                    j += 1
                if j < len(lines):
                    channels.append({"name": name, "url": lines[j]})
                    i = j + 1
                    continue
            i += 1
        return channels

    # ---------- 壳子接口 ----------
    def homeContent(self, filter):
        classes = [{"type_id": str(idx), "type_name": name}
                   for idx, (name, _) in enumerate(self.sources)]
        return {"class": classes}

    def categoryContent(self, tid, pg, filter, extend):
        idx = int(tid)
        if idx < 0 or idx >= len(self.sources):
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

        name, url = self.sources[idx]
        # 缓存避免重复抓取
        if tid not in self.channel_cache:
            m3u = self._fetch_m3u(url)
            self.channel_cache[tid] = self._parse_channels(m3u)

        channels = self.channel_cache[tid]
        items = []
        for i, ch in enumerate(channels):
            items.append({
                "vod_id": f"{tid}_{i}",
                "vod_name": ch["name"],
                "vod_pic": "",
                "vod_remarks": name,
            })
        return {"list": items, "page": 1, "pagecount": 1, "limit": len(items), "total": len(items)}

    def detailContent(self, ids):
        vid = ids[0]
        tid, idx = vid.split("_")
        idx = int(idx)
        name, _ = self.sources[int(tid)]
        channels = self.channel_cache.get(tid, [])
        if idx >= len(channels):
            return {"list": []}
        ch = channels[idx]
        return {"list": [{
            "vod_id": vid,
            "vod_name": ch["name"],
            "vod_pic": "",
            "vod_play_from": name,
            "vod_play_url": f"{ch['name']}${ch['url']}"
        }]}

    def playerContent(self, flag, pid, vipFlags):
        # pid 直接就是播放地址
        return {
            "parse": 0,
            "jx": 0,
            "url": pid,
            "header": self.headers,
        }
