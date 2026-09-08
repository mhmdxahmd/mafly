[2026/9/8 13:41] Flora: # coding=utf-8
import re
import urllib.parse
import requests

try:
    from base.spider import Spider as BaseSpider
except Exception:
    BaseSpider = object


class Spider(BaseSpider):
    def getName(self):
        return "YouTube新闻直播(代理版)"

    def init(self, extend=""):
        self.proxy_api = "https://x.maflya.com/api/proxy?target="
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _wrap_proxy(self, target_url):
        """将目标 URL 转为通过代理访问的 URL"""
        if not target_url:
            return ""
        return f"{self.proxy_api}{urllib.parse.quote(target_url, safe='')}"

    def homeContent(self, filter):
        return {"class": [{"type_id": "yt_live", "type_name": "新闻直播"}]}

    def homeVideoContent(self):
        return self.categoryContent("yt_live", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        channels = [
            ("vr3XyVCR4T0", "中天新闻 24H直播"),
            ("6IquAgfvYmc", "寰宇新闻 24H直播"),
            ("ylYJSBUgaMA", "民视新闻 24H直播"),
            ("V1p33hqPrUk", "TVBS新闻 24H直播"),
            ("m_dhMSvUCIc", "东森新闻 24H直播"),
            ("fWlRLYXkVxY", "三立新闻 24H直播"),
            ("Ry--eMIjYLQ", "台视新闻 24H直播"),
        ]

        items = []
        for vid, name in channels:
            raw_pic = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            items.append({
                "vod_id": vid,
                "vod_name": name,
                # 封面图同时套用代理，避免国内海报裂图
                "vod_pic": self._wrap_proxy(raw_pic),
                "vod_remarks": "LIVE",
            })

        return {
            "list": items,
            "page": 1,
            "pagecount": 1,
            "limit": len(items),
            "total": len(items),
        }

    def detailContent(self, ids):
        vid = ids[0]
        vod = {
            "vod_id": vid,
            "vod_name": vid,
            "vod_play_from": "YouTube直链",
            "vod_play_url": f"直播线路${vid}",
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        raw_video_url = f"https://www.youtube.com/watch?v={id}"
        proxied_page_url = self._wrap_proxy(raw_video_url)
        
        m3u8_url = ""
        try:
            # 1. 通过代理抓取 YouTube 页面源码
            res = requests.get(proxied_page_url, headers=self.headers, timeout=10)
            match = re.search(r'"hlsManifestUrl"\s*:\s*"(https:[^"]+)"', res.text)
            if match:
                raw_m3u8 = match.group(1).replace(r"\/", "/")
                # 2. 将最终的 m3u8 直播流地址也套上代理
                m3u8_url = self._wrap_proxy(raw_m3u8)
        except Exception:
            pass

        if m3u8_url:
            return {
                "parse": 0,
                "url": m3u8_url,
                "header": {"User-Agent": self.headers["User-Agent"]},
            }

        # 降级备用逻辑
        return {
            "parse": 1,
            "url": proxied_page_url,
            "header": self.headers,
        }
[2026/9/8 13:41] Flora: 是你的地址有问题吗
