# coding=utf-8
import re
import sys
import requests
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

        # 一级分类：源名称 -> m3u地址
        self.sources = [
            ("IPTV直播", "https://iptv.445569.xyz/live.m3u"),
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

        # 缓存：源索引 -> {组名: [频道...]}
        self.group_cache = {}

    # ---------- 过滤 ----------
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

    # ---------- 抓取 ----------
    def _fetch_m3u(self, url):
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return ""

    # ---------- 解析：按 group-title 分组 ----------
    def _parse_groups(self, m3u_text):
        """
        返回 dict：组名 -> [{name, url}]
        没有 group-title 的频道归入 "未分组"
        """
        groups = {}
        lines = [ln.strip() for ln in m3u_text.splitlines() if not self._should_filter(ln)]
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.startswith("#EXTINF"):
                # 频道名：最后一个逗号之后
                name = ln.split(",")[-1].strip() if "," in ln else "未知频道"
                # 组名：group-title="..."
                m = re.search(r'group-title="([^"]*)"', ln)
                group = m.group(1).strip() if m and m.group(1).strip() else "未分组"

                # 找紧跟的 http 行
                j = i + 1
                while j < len(lines) and not lines[j].startswith("http"):
                    j += 1
                if j < len(lines):
                    groups.setdefault(group, []).append({"name": name, "url": lines[j]})
                    i = j + 1
                    continue
            i += 1
        return groups

    def _load_groups(self, tid):
        """加载并缓存某个源的二级分组"""
        tid = str(tid)
        if tid in self.group_cache:
            return self.group_cache[tid]
        idx = int(tid)
        if idx < 0 or idx >= len(self.sources):
            return {}
        name, url = self.sources[idx]
        m3u = self._fetch_m3u(url)
        groups = self._parse_groups(m3u)
        self.group_cache[tid] = groups
        return groups

    # ---------- 壳子接口 ----------
    def homeContent(self, filter):
        # 一级分类：17 个源
        classes = [{"type_id": str(idx), "type_name": name}
                   for idx, (name, _) in enumerate(self.sources)]
        return {"class": classes}

    def categoryContent(self, tid, pg, filter, extend):
        """
        tid 支持两种形态：
          - "源索引"          -> 返回该源下的二级分组列表
          - "源索引_组名"     -> 返回该组下的频道列表
        """
        tid = str(tid)

        # 二级：源索引_组名
        if "_" in tid:
            src_idx, group_name = tid.split("_", 1)
            groups = self._load_groups(src_idx)
            channels = groups.get(group_name, [])
            items = []
            for i, ch in enumerate(channels):
                items.append({
                    "vod_id": f"{src_idx}__{group_name}__{i}",
                    "vod_name": ch["name"],
                    "vod_pic": "",
                    "vod_remarks": group_name,
                })
            return {"list": items, "page": 1, "pagecount": 1,
                    "limit": len(items), "total": len(items)}

        # 一级：源索引 -> 列出二级分组
        groups = self._load_groups(tid)
        items = []
        for group_name, channels in groups.items():
            items.append({
                "vod_id": f"{tid}_{group_name}",
                "vod_name": group_name,
                "vod_pic": "",
                "vod_remarks": f"{len(channels)} 个频道",
            })
        return {"list": items, "page": 1, "pagecount": 1,
                "limit": len(items), "total": len(items)}

    def detailContent(self, ids):
        vid = ids[0]
        # 三级 vod_id：源索引__组名__频道索引
        parts = vid.split("__")
        if len(parts) != 3:
            return {"list": []}
        src_idx, group_name, ch_idx = parts
        ch_idx = int(ch_idx)
        groups = self._load_groups(src_idx)
        channels = groups.get(group_name, [])
        if ch_idx >= len(channels):
            return {"list": []}
        ch = channels[ch_idx]
        return {"list": [{
            "vod_id": vid,
            "vod_name": ch["name"],
            "vod_pic": "",
            "vod_play_from": group_name,
            "vod_play_url": f"{ch['name']}${ch['url']}"
        }]}

    def playerContent(self, flag, pid, vipFlags):
        return {
            "parse": 0,
            "jx": 0,
            "url": pid,
            "header": self.headers,
        }
