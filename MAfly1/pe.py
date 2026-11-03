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

        self.sources = [
            ("IPTV直播", "http://seep.eu.org/https://iptv.445569.xyz/live.m3u"),
            ("咖啡体育直播", "http://seep.eu.org/https://jsnzkpg.de5.net/all.m3u"),
            ("大米体育直播", "http://seep.eu.org/https://stymei.pages.dev/live.m3u"),
            ("88看球直播", "http://seep.eu.org/https://stymei1.pages.dev/live.m3u"),
            ("178体育直播", "http://seep.eu.org/https://stymei2.pages.dev/live.m3u"),
            ("310体育直播", "http://seep.eu.org/https://stymei3.pages.dev/live.m3u"),
            ("豆包体育直播", "http://seep.eu.org/https://stymei4.pages.dev/live.m3u"),
            ("鲸鱼体育直播", "http://seep.eu.org/https://stymei5.pages.dev/live.m3u"),
            ("看球通体育直播", "http://seep.eu.org/https://stymei6.pages.dev/live.m3u"),
            ("球吧体育直播", "http://seep.eu.org/https://stymei7.pages.dev/live.m3u"),
            ("松果体育直播", "http://seep.eu.org/https://stymei8.pages.dev/live.m3u"),
            ("天天体育直播", "http://seep.eu.org/https://stymei9.pages.dev/live.m3u"),
            ("一代体育直播", "http://seep.eu.org/https://stymei10.pages.dev/live.m3u"),
            ("JRKAN体育直播", "http://seep.eu.org/https://stymei11.pages.dev/live.m3u"),
            ("OK体育直播", "http://seep.eu.org/https://stymei12.pages.dev/live.m3u"),
            ("说球帝体育直播", "http://seep.eu.org/https://stymei13.pages.dev/live.m3u"),
            ("海星体育直播", "http://seep.eu.org/https://stymei14.pages.dev/live.m3u"),
            ("U球体育直播", "http://seep.eu.org/https://stymei15.pages.dev/live.m3u"),
        ]

        self.group_cache = {}

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

    def _parse_groups(self, m3u_text):
        groups = {}
        lines = [ln.strip() for ln in m3u_text.splitlines() if not self._should_filter(ln)]
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.startswith("#EXTINF"):
                name = ln.split(",")[-1].strip() if "," in ln else "未知频道"
                m = re.search(r'group-title="([^"]*)"', ln)
                group = m.group(1).strip() if m and m.group(1).strip() else "未分组"

                j = i + 1
                while j < len(lines) and not lines[j].startswith("http"):
                    j += 1
                if j < len(lines):
                    groups.setdefault(group, []).append({"name": name, "url": lines[j]})
                    i = j + 1
                    continue
            i += 1
        return groups

    def _load_groups(self, src_idx):
        try:
            src_idx = int(src_idx)
        except (TypeError, ValueError):
            return {}
        key = str(src_idx)
        if key in self.group_cache:
            return self.group_cache[key]
        if src_idx < 0 or src_idx >= len(self.sources):
            return {}
        _, url = self.sources[src_idx]
        m3u = self._fetch_m3u(url)
        groups = self._parse_groups(m3u)
        self.group_cache[key] = groups
        return groups

    def _make_channel_entry(self, src_idx, group_idx, ch_idx, ch):
        vid = f"{src_idx}_{group_idx}_{ch_idx}"
        safe_name = re.sub(r'[#$@]', ' ', ch["name"]).strip() or "频道"
        return f"{safe_name}${vid}@live"

    def homeContent(self, filter):
        classes = [{"type_id": str(idx), "type_name": name}
                   for idx, (name, _) in enumerate(self.sources)]
        return {"class": classes}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            tid = str(tid).strip()
            if not tid:
                return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

            if "_" in tid:
                parts = tid.split("_")
                if len(parts) != 2:
                    return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

                src_idx, group_idx = int(parts[0]), int(parts[1])
                groups = self._load_groups(src_idx)
                group_names = list(groups.keys())

                if group_idx < 0 or group_idx >= len(group_names):
                    return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

                group_name = group_names[group_idx]
                channels = groups[group_name]

                items = []
                for ch_idx, ch in enumerate(channels):
                    item_id = f"{src_idx}_{group_idx}_{ch_idx}"
                    items.append({
                        "vod_id": item_id,
                        "vod_name": ch["name"],
                        "vod_pic": "",
                        "vod_remarks": group_name,
                    })
                return {"list": items, "page": 1, "pagecount": 1,
                        "limit": len(items), "total": len(items)}

            src_idx = int(tid)
            groups = self._load_groups(src_idx)
            items = []
            for g_idx, (group_name, channels) in enumerate(groups.items()):
                items.append({
                    "vod_id": f"{src_idx}_{g_idx}",
                    "vod_name": group_name,
                    "vod_pic": "",
                    "vod_remarks": f"{len(channels)} 个频道",
                })
            return {"list": items, "page": 1, "pagecount": 1,
                    "limit": len(items), "total": len(items)}
        except Exception:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def detailContent(self, ids):
        try:
            if not ids:
                return {"list": []}
            vid = str(ids[0]).strip()
            parts = vid.split("_")

            # 壳子把“组”当视频点了：返回 1 个 vod，把组内所有频道拼进 vod_play_url 用 # 分隔
            if len(parts) == 2:
                src_idx, group_idx = int(parts[0]), int(parts[1])
                groups = self._load_groups(src_idx)
                group_names = list(groups.keys())
                if group_idx < 0 or group_idx >= len(group_names):
                    return {"list": []}

                group_name = group_names[group_idx]
                channels = groups[group_name]
                if not channels:
                    return {"list": []}

                play_urls = []
                for ch_idx, ch in enumerate(channels):
                    play_urls.append(self._make_channel_entry(src_idx, group_idx, ch_idx, ch))

                return {"list": [{
                    "vod_id": vid,
                    "vod_name": group_name,
                    "vod_pic": "",
                    "vod_remarks": f"{len(channels)} 个频道",
                    "vod_play_from": group_name,
                    "vod_play_url": "#".join(play_urls),
                }]}

            # 正常频道：三段 vod_id
            if len(parts) == 3:
                src_idx, group_idx, ch_idx = int(parts[0]), int(parts[1]), int(parts[2])
                groups = self._load_groups(src_idx)
                group_names = list(groups.keys())
                if group_idx < 0 or group_idx >= len(group_names):
                    return {"list": []}

                group_name = group_names[group_idx]
                channels = groups[group_name]
                if ch_idx < 0 or ch_idx >= len(channels):
                    return {"list": []}

                ch = channels[ch_idx]
                play_url = self._make_channel_entry(src_idx, group_idx, ch_idx, ch)
                return {"list": [{
                    "vod_id": vid,
                    "vod_name": ch["name"],
                    "vod_pic": "",
                    "vod_remarks": group_name,
                    "vod_play_from": group_name,
                    "vod_play_url": play_url,
                }]}

            return {"list": []}
        except Exception:
            return {"list": []}

    def playerContent(self, flag, pid, vipFlags):
        try:
            if not pid:
                return {"parse": 0, "jx": 0, "url": "", "header": self.headers,
                        "format": "application/x-mpegURL"}

            raw_pid = str(pid).split('$')[-1]
            if '@' in raw_pid:
                raw_pid = raw_pid.rsplit('@', 1)[0]

            url = raw_pid

            if not raw_pid.startswith("http"):
                parts = raw_pid.split("_")
                if len(parts) == 3:
                    src_idx, group_idx, ch_idx = int(parts[0]), int(parts[1]), int(parts[2])
                    groups = self._load_groups(src_idx)
                    group_names = list(groups.keys())
                    if 0 <= group_idx < len(group_names):
                        channels = groups[group_names[group_idx]]
                        if 0 <= ch_idx < len(channels):
                            url = channels[ch_idx]["url"]

            return {
                "parse": 0,
                "jx": 0,
                "url": url,
                "header": self.headers,
                "format": "application/x-mpegURL",
            }
        except Exception:
            return {"parse": 0, "jx": 0, "url": "", "header": self.headers,
                    "format": "application/x-mpegURL"}
