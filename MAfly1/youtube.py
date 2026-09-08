# coding=utf-8
import re
import json
import time
import requests
from urllib.parse import quote, urlparse
from base.spider import Spider as BaseSpider

# ================== 配置区域 ==================
# 固定视频ID频道列表（新闻台24小时直播）
FIXED_CHANNELS = [
    ("vr3XyVCR4T0", "中天新闻 24H直播"),
    ("6IquAgfvYmc", "寰宇新闻 24H直播"),
    ("ylYJSBUgaMA", "民视新闻 24H直播"),
    ("V1p33hqPrUk", "TVBS新闻 24H直播"),
    ("m_dhMSvUCIc", "东森新闻 24H直播"),
    ("fWlRLYXkVxY", "三立新闻 24H直播"),
    ("Ry--eMIjYLQ", "台视新闻 24H直播"),
]

# 动态检测的频道ID列表（凤凰卫视）
DYNAMIC_CHANNEL_IDS = [
    ("UC4vnLYInDvXtLKGOZieMeMw", "凤凰卫视"),
]

# 您的 Cloudflare Worker 代理地址
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

def is_google_domain(url):
    """判断 URL 是否属于 Google/YouTube 相关域名"""
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
    """对 Google 域名添加代理前缀"""
    if is_google_domain(url):
        return PROXY_BASE + quote(url, safe=':/?&=%')
    return url

class Spider(BaseSpider):
    def getName(self):
        return 'YouTube新闻直播'

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.youtube.com/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        debug_log('spider init', {
            'proxy_base': PROXY_BASE,
            'fixed_channels': len(FIXED_CHANNELS),
            'dynamic_channels': len(DYNAMIC_CHANNEL_IDS)
        })

    def homeContent(self, filter):
        return {"class": [{"type_id": "yt_live", "type_name": "新闻直播"}]}

    def homeVideoContent(self):
        return self.categoryContent("yt_live", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        items = []
        
        # 1. 添加固定视频ID频道
        for vid, name in FIXED_CHANNELS:
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": apply_proxy(f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"),
                "vod_remarks": "LIVE"
            })
        
        # 2. 动态检测频道是否在直播
        for channel_id, channel_name in DYNAMIC_CHANNEL_IDS:
            try:
                live_video_id = self._get_live_video_from_channel(channel_id)
                if live_video_id:
                    items.append({
                        "vod_id": live_video_id,
                        "vod_name": f"{channel_name} 直播",
                        "vod_pic": apply_proxy(f"https://i.ytimg.com/vi/{live_video_id}/hqdefault.jpg"),
                        "vod_remarks": "LIVE"
                    })
                    debug_log('dynamic channel live found', {'channel_id': channel_id, 'video_id': live_video_id})
            except Exception as e:
                debug_log('dynamic channel check error', {'channel_id': channel_id, 'error': repr(e)})
        
        return {"list": items, "page": 1, "pagecount": 1, "limit": len(items), "total": len(items)}

    def detailContent(self, ids):
        vid = ids[0]
        name = vid
        # 查找固定频道名称
        for ch_vid, ch_name in FIXED_CHANNELS:
            if ch_vid == vid:
                name = ch_name
                break
        # 查找动态频道名称
        for ch_id, ch_name in DYNAMIC_CHANNEL_IDS:
            if ch_name in name:
                name = f"{ch_name} 直播"
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

        # 通过代理请求 YouTube 页面
        watch_url = apply_proxy(f'https://www.youtube.com/watch?v={video_id}')
        try:
            resp = self.session.get(watch_url, timeout=12)
            page = resp.text
            hls_url = self._extract_hls(page)
            if hls_url:
                # 对 HLS 地址应用代理
                proxied_hls = apply_proxy(hls_url)
                debug_log('play url generated', {'video_id': video_id, 'url_len': len(proxied_hls)})
                return {
                    "parse": 1,
                    "jx": 0,
                    "url": proxied_hls,
                    "header": self.headers,
                    "format": "application/x-mpegURL"
                }
        except Exception as e:
            debug_log('extract error', {'video_id': video_id, 'error': repr(e)})

        debug_log('hls not found, fallback to web', {'video_id': video_id})
        return {"parse": 1, "url": watch_url, "header": self.headers}

    def _get_live_video_from_channel(self, channel_id):
        """从频道页面获取当前直播视频ID（通过代理）"""
        live_url = f'https://www.youtube.com/channel/{channel_id}/live'
        try:
            proxied_url = apply_proxy(live_url)
            resp = self.session.get(proxied_url, allow_redirects=False, timeout=10)
            debug_log('channel live page', {
                'channel_id': channel_id,
                'status': resp.status_code,
                'location': resp.headers.get('Location', '')
            })
            # 如果重定向到 watch?v=xxx
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get('Location', '')
                match = re.search(r'[?&]v=([0-9A-Za-z_-]{11})', location)
                if match:
                    return match.group(1)
            # 如果返回200，尝试从页面提取
            if resp.status_code == 200:
                html_text = resp.text
                match = re.search(r'"videoId":"([0-9A-Za-z_-]{11})"', html_text)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            debug_log('channel live page error', {'channel_id': channel_id, 'error': repr(e)})
            return None

    def _extract_hls(self, page):
        # 方式1：直接匹配 hlsManifestUrl
        match = re.search(r'"hlsManifestUrl"\s*:\s*"(https:[^"]+)"', page)
        if match:
            return match.group(1).replace(r'\/', '/')

        # 方式2：从 ytInitialPlayerResponse JSON 中提取
        match2 = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', page, re.S)
        if match2:
            try:
                data = json.loads(match2.group(1))
                hls = data.get('streamingData', {}).get('hlsManifestUrl')
                if hls:
                    return hls
            except:
                pass

        # 方式3：查找所有 m3u8 链接
        matches = re.findall(r'"(https://[^"]*?\.m3u8[^"]*)"', page)
        if matches:
            for m in matches:
                if 'master' in m or 'hls_playlist' in m:
                    return m.replace(r'\/', '/')
            return matches[0].replace(r'\/', '/')

        return ''
