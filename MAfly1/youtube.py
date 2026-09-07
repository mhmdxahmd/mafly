# coding=utf-8
import re
import json
import time
import requests
from urllib.parse import quote, urlparse
from base.spider import Spider as BaseSpider

# ================== 配置区域 ==================
CHANNELS = [
    {"id": "vr3XyVCR4T0", "name": "中天新闻 24H直播"},
    {"id": "6IquAgfvYmc", "name": "寰宇新闻 24H直播"},
    {"id": "ylYJSBUgaMA", "name": "民视新闻 24H直播"},
]

# 您的 Cloudflare Worker 代理地址（请确保域名正确）
PROXY_BASE = 'https://x.maflya.com/api/proxy?target='

# 调试日志文件路径（留空则禁用日志）
DEBUG_LOG = '/sdcard/Download/ytb_live_debug.log'
# ===========================================

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

def apply_proxy(url):
    """对 Google/YouTube 域名自动添加代理前缀"""
    google_domains = [
        'youtube.com', 'youtu.be', 'ytimg.com', 'googlevideo.com',
        'googleapis.com', 'google.com', 'gstatic.com', 'googleusercontent.com'
    ]
    try:
        host = urlparse(url).hostname or ''
        host = host.lower()
        if any(host == d or host.endswith('.' + d) for d in google_domains):
            return PROXY_BASE + quote(url, safe='')
    except:
        pass
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
        debug_log('spider init', {'proxy_base': PROXY_BASE, 'channels': len(CHANNELS)})

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
                # 缩略图也通过代理，避免加载失败
                "vod_pic": apply_proxy(f"https://i.ytimg.com/vi/{ch['id']}/hqdefault.jpg"),
                "vod_remarks": "LIVE"
            })
        return {
            "list": items,
            "page": 1,
            "pagecount": 1,
            "limit": len(items),
            "total": len(items)
        }

    def detailContent(self, ids):
        vid = ids[0]
        name = vid
        for ch in CHANNELS:
            if ch["id"] == vid:
                name = ch["name"]
                break
        vod = {
            "vod_id": vid,
            "vod_name": name,
            "vod_play_from": "YouTube直播",
            "vod_play_url": f"直播线路${vid}@live"
        }
        return {"list": [vod]}

    def playerContent(self, flag, pid, vipFlags):
        raw_pid = pid.split('$')[-1]
        video_id = raw_pid.rsplit('@', 1)[0] if '@' in raw_pid else raw_pid
        debug_log('player start', {'video_id': video_id})

        # 通过 Worker 代理请求 YouTube 页面
        watch_url = apply_proxy(f'https://www.youtube.com/watch?v={video_id}')
        try:
            resp = self.session.get(watch_url, timeout=12)
            page = resp.text
            hls_url = self._extract_hls(page)
            if hls_url:
                # 对 HLS 地址应用代理，播放器请求的就是 Worker 地址
                proxied_hls = apply_proxy(hls_url)
                debug_log('extract hls success', {'video_id': video_id, 'proxied_hls_len': len(proxied_hls)})
                return {
                    "parse": 0,
                    "jx": 0,
                    "url": proxied_hls,
                    "header": self.headers,
                    "format": "application/x-mpegURL"
                }
        except Exception as e:
            debug_log('extract hls error', {'video_id': video_id, 'error': repr(e)})

        # 提取失败，回退到网页解析（也走代理）
        debug_log('hls not found, fallback to web', {'video_id': video_id})
        return {
            "parse": 1,
            "url": watch_url,
            "header": self.headers
        }

    def _extract_hls(self, page):
        """从 YouTube 页面中提取 HLS master 地址"""
        # 方式1：直接正则 hlsManifestUrl
        match = re.search(r'"hlsManifestUrl"\s*:\s*"(https:[^"]+)"', page)
        if match:
            return match.group(1).replace(r'\/', '/')

        # 方式2：ytInitialPlayerResponse JSON 中提取
        match2 = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', page, re.S)
        if match2:
            try:
                data = json.loads(match2.group(1))
                hls = data.get('streamingData', {}).get('hlsManifestUrl')
                if hls:
                    return hls
            except Exception:
                pass

        # 方式3：查找所有 m3u8 链接
        matches = re.findall(r'"(https://[^"]*?\.m3u8[^"]*)"', page)
        if matches:
            for m in matches:
                if 'master' in m or 'hls_playlist' in m:
                    return m.replace(r'\/', '/')
            return matches[0].replace(r'\/', '/')

        return ''
