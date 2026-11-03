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
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def _fetch(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return ""

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

    def liveContent(self, url):
        out = ["#EXTM3U"]
        for name, m3u_url in self.sources:
            raw = self._fetch(m3u_url)
            if not raw or "#EXTM3U" not in raw.upper():
                continue
            lines = [ln.strip() for ln in raw.splitlines() if not self._should_filter(ln)]
            i = 0
            while i < len(lines):
                ln = lines[i]
                if ln.startswith("#EXTINF"):
                    # 统一 group-title 为源名称
                    if 'group-title="' in ln:
                        ln = re.sub(r'group-title="[^"]*"', f'group-title="{name}"', ln)
                    else:
                        ln = ln.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{name}"', 1)
                    j = i + 1
                    while j < len(lines) and not lines[j].startswith("http"):
                        j += 1
                    if j < len(lines):
                        out.append(ln)
                        out.append(lines[j])
                        i = j + 1
                        continue
                i += 1
        return "\n".join(out)
