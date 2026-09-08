# coding=utf-8
import re
import json
import time
import requests
from urllib.parse import quote, urlparse
from base.spider import Spider as BaseSpider

# ================== 配置区域 ==================
FIXED_CHANNELS = [
    ("vr3XyVCR4T0", "中天新闻 24H直播"),
    ("6IquAgfvYmc", "寰宇新闻 24H直播"),
    ("ylYJSBUgaMA", "民视新闻 24H直播"),
    ("V1p33hqPrUk", "TVBS新闻 24H直播"),
    ("m_dhMSvUCIc", "东森新闻 24H直播"),
    ("fWlRLYXkVxY", "三立新闻 24H直播"),
    ("Ry--eMIjYLQ", "台视新闻 24H直播"),
]

# HTTP 代理列表（用于 Python 请求 YouTube）
HTTP_PROXIES = [
    'https://fan.240104.xyz:443',
    'https://fan.891058.xyz:443',
    'https://fan.596189.xyz:443',
    'https://fan.226278.xyz:443',
    'https://fan.587475.xyz:443',
    'https://fan.571589.xyz:443',
    'https://fan.572609.xyz:443',
    'https://fan.212800.xyz:443',
    'https://fan.973511.xyz:443',
]

# 调试日志
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

def get_proxy():
    """轮询获取 HTTP 代理"""
    if HTTP_PROXIES:
        return HTTP_PROXIES[int(time.time()) % len(HTTP_PROXIES)]
    return None

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
        debug_log('spider init', {'http_proxies': len(HTTP_PROXIES)})

    def homeContent(self, filter):
        return {"class": [{"type_id": "yt_live", "type_name": "新闻直播"}]}

    def homeVideoContent(self):
        return self.categoryContent("yt_live", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        items = []
        for vid, name in FIXED_CHANNELS:
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                "vod_remarks": "LIVE"
            })
        return {"list": items, "page": 1, "pagecount": 1, "limit": len(items), "total": len(items)}

    def detailContent(self, ids):
        vid = ids[0]
        name = vid
        for ch_vid, ch_name in FIXED_CHANNELS:
            if ch_vid == vid:
                name = ch_name
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
        debug_log('player start', {'video_id': video_id})

        # 使用 HTTP 代理请求 YouTube 页面
        hls_url = self._fetch_hls_with_proxy(video_id)
        
        if hls_url:
            debug_log('hls extracted', {'video_id': video_id, 'hls_url_len': len(hls_url)})
            # 直接返回原始 HLS 地址（不经过任何转发）
            # 播放器需要能直连 googlevideo.com（开全局代理时）
            return {
                "parse": 0,
                "jx": 0,
                "url": hls_url,
                "header": self.headers,
                "format": "application/x-mpegURL"
            }
        
        # 回退
        debug_log('hls not found, fallback', {'video_id': video_id})
        return {
            "parse": 1,
            "url": f'https://www.youtube.com/watch?v={video_id}',
            "header": self.headers
        }

    def _fetch_hls_with_proxy(self, video_id):
        """使用 HTTP 代理请求 YouTube 页面并提取 HLS"""
        watch_url = f'https://www.youtube.com/watch?v={video_id}'
        
        # 尝试多个代理
        for i in range(5):
            proxy = get_proxy()
            proxies = {'http': proxy, 'https': proxy} if proxy else None
            
            try:
                debug_log('try proxy', {'video_id': video_id, 'proxy': proxy, 'attempt': i+1})
                resp = self.session.get(watch_url, proxies=proxies, timeout=15)
                page = resp.text
                hls_url = self._extract_hls(page)
                if hls_url:
                    debug_log('hls extracted with proxy', {'video_id': video_id, 'proxy': proxy})
                    return hls_url
            except Exception as e:
                debug_log('proxy attempt failed', {'video_id': video_id, 'proxy': proxy, 'error': repr(e)})
                continue
        
        return ''

    def _extract_hls(self, page):
        # 方法1：直接正则
        match = re.search(r'"hlsManifestUrl"\s*:\s*"(https:[^"]+)"', page)
        if match:
            return match.group(1).replace(r'\/', '/')
        
        # 方法2：JSON 提取
        match2 = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', page, re.S)
        if match2:
            try:
                data = json.loads(match2.group(1))
                hls = data.get('streamingData', {}).get('hlsManifestUrl')
                if hls:
                    return hls
            except:
                pass
        
        # 方法3：查找所有 m3u8
        matches = re.findall(r'"(https://[^"]*?\.m3u8[^"]*)"', page)
        if matches:
            return matches[0].replace(r'\/', '/')
        
        return ''
