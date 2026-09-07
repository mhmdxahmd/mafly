# coding=utf-8
import re
import json
import time
import requests
from urllib.parse import quote, urlparse
from base.spider import Spider as BaseSpider

CHANNELS = [
    {"id": "vr3XyVCR4T0", "name": "中天新闻 24H直播"},
    {"id": "6IquAgfvYmc", "name": "寰宇新闻 24H直播"},
    {"id": "ylYJSBUgaMA", "name": "民视新闻 24H直播"},
]
PROXY_BASE = 'https://x.maflya.com/api/proxy?target='
DEBUG_LOG = '/sdcard/Download/ytb_live_debug.log'

def debug_log(message, data=None):
    if not DEBUG_LOG:
        return
    try:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        if data is not None:
            if isinstance(data, (dict, list)):
                line += ' ' + json.dumps(data, ensure_ascii=False, default=str)
            else:
                line += ' ' + str(data)
        with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

def is_google_domain(url):
    google_domains = [
        'youtube.com', 'youtu.be', 'ytimg.com', 'googlevideo.com',
        'googleapis.com', 'google.com', 'gstatic.com', 'googleusercontent.com'
    ]
    try:
        host = urlparse(url).hostname or ''
        host = host.lower()
        return any(host == d or host.endswith('.' + d) for d in google_domains)
    except:
        return False

def apply_proxy(url):
    if is_google_domain(url):
        # 仅编码必要的字符，保留 URL 结构可读性，减少播放器解析错误
        return PROXY_BASE + quote(url, safe=':/?&=%')
    return url

class Spider(BaseSpider):
    def getName(self):
        return 'YouTube固定频道直播'

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.youtube.com/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        debug_log('spider init', {'proxy_base': PROXY_BASE})

    def homeContent(self, filter):
        return {"class": [{"type_id": "fixed_live", "type_name": "固定频道直播"}]}

    def homeVideoContent(self):
        return self.categoryContent("fixed_live", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        items = []
        for ch in CHANNELS:
            items.append({
                "vod_id": ch["id"],
                "vod_name": ch["name"],
                "vod_pic": apply_proxy(f"https://i.ytimg.com/vi/{ch['id']}/hqdefault.jpg"),
                "vod_remarks": "LIVE"
            })
        return {"list": items, "page": 1, "pagecount": 1, "limit": len(items), "total": len(items)}

    def detailContent(self, ids):
        vid = ids[0]
        name = vid
        for ch in CHANNELS:
            if ch["id"] == vid:
                name = ch["name"]
                break
        return {"list": [{
            "vod_id": vid,
            "vod_name": name,
            "vod_play_from": "YouTube直播",
            "vod_play_url": f"直播线路${vid}@live"
        }]}

    def playerContent(self, flag, pid, vipFlags):
        raw_pid = pid.split('$')[-1]
        video_id = raw_pid.rsplit('@', 1)[0] if '@' in raw_pid else raw_pid
        watch_url = apply_proxy(f'https://www.youtube.com/watch?v={video_id}')
        try:
            resp = self.session.get(watch_url, timeout=12)
            page = resp.text
            # 提取 HLS 地址
            hls_url = self._extract_hls(page)
            if hls_url:
                proxied_hls = apply_proxy(hls_url)
                debug_log('play url generated', {'video_id': video_id, 'url_len': len(proxied_hls)})
                return {
                    "parse": 0,
                    "jx": 0,
                    "url": proxied_hls,
                    "header": self.headers,
                    "format": "application/x-mpegURL"
                }
        except Exception as e:
            debug_log('extract error', {'video_id': video_id, 'error': repr(e)})
        return {"parse": 1, "url": watch_url, "header": self.headers}

    def _extract_hls(self, page):
        match = re.search(r'"hlsManifestUrl"\s*:\s*"(https:[^"]+)"', page)
        if match:
            return match.group(1).replace(r'\/', '/')
        match2 = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', page, re.S)
        if match2:
            try:
                data = json.loads(match2.group(1))
                hls = data.get('streamingData', {}).get('hlsManifestUrl')
                if hls:
                    return hls
            except:
                pass
        matches = re.findall(r'"(https://[^"]*?\.m3u8[^"]*)"', page)
        if matches:
            for m in matches:
                if 'master' in m or 'hls_playlist' in m:
                    return m.replace(r'\/', '/')
            return matches[0].replace(r'\/', '/')
        return ''
