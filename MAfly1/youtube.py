# coding=utf-8
import re
import requests
from urllib.parse import quote, urlparse

try:
    from base.spider import Spider as BaseSpider
except Exception:
    BaseSpider = object

# 您的 Cloudflare Worker 代理地址
PROXY_BASE = 'https://x.maflya.com/api/proxy?target='

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
        return "YouTube新闻直播"

    def init(self, extend=""):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def homeContent(self, filter):
        return {
            "class": [{"type_id": "yt_live", "type_name": "新闻直播"}]
        }

    def homeVideoContent(self):
        return self.categoryContent("yt_live", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        items = [
            {
                "vod_id": "vr3XyVCR4T0",
                "vod_name": "中天新闻 24H直播",
                "vod_pic": "https://i.ytimg.com/vi/vr3XyVCR4T0/hqdefault.jpg",
                "vod_remarks": "LIVE"
            },
            {
                "vod_id": "6IquAgfvYmc",
                "vod_name": "寰宇新闻 24H直播",
                "vod_pic": "https://i.ytimg.com/vi/6IquAgfvYmc/hqdefault.jpg",
                "vod_remarks": "LIVE"
            },
            {
                "vod_id": "ylYJSBUgaMA",
                "vod_name": "民视新闻 24H直播",
                "vod_pic": "https://i.ytimg.com/vi/ylYJSBUgaMA/hqdefault.jpg",
                "vod_remarks": "LIVE"
            }
        ]
        return {"list": items, "page": 1, "pagecount": 1, "limit": len(items), "total": len(items)}

    def detailContent(self, ids):
        vid = ids[0]
        vod = {
            "vod_id": vid,
            "vod_name": vid,
            "vod_play_from": "YouTube直链",
            "vod_play_url": f"直播线路${vid}"
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        # 原始 YouTube 页面 URL
        video_url = f"https://www.youtube.com/watch?v={id}"
        # 通过代理请求页面
        proxied_video_url = apply_proxy(video_url)
        m3u8_url = ""
        try:
            res = requests.get(proxied_video_url, headers=self.headers, timeout=10)
            # 从网页中提取 hlsManifestUrl
            match = re.search(r'"hlsManifestUrl"\s*:\s*"(https:[^"]+)"', res.text)
            if match:
                m3u8_url = match.group(1).replace(r"\/", "/")
        except Exception:
            pass

        if m3u8_url:
            # 对提取到的 HLS 地址也应用代理
            proxied_m3u8 = apply_proxy(m3u8_url)
            return {
                "parse": 0,  # 告诉 TVBox 这是直链，不用再走网页嗅探
                "url": proxied_m3u8,
                "header": self.headers
            }
        
        # 提取失败时的回退（通过代理打开网页）
        return {"parse": 1, "url": proxied_video_url, "header": self.headers}
