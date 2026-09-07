# coding=utf-8
import re
import requests
try:
    from base.spider import Spider as BaseSpider
except Exception:
    BaseSpider = object

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
        # 核心：请求页面，提取隐藏在 HTML 中的 m3u8 直链
        video_url = f"https://www.youtube.com/watch?v={id}"
        m3u8_url = ""
        try:
            res = requests.get(video_url, headers=self.headers, timeout=10)
            # 从网页中提取 hlsManifestUrl
            match = re.search(r'"hlsManifestUrl"\s*:\s*"(https:[^"]+)"', res.text)
            if match:
                m3u8_url = match.group(1).replace(r"\/", "/")
        except Exception:
            pass

        if m3u8_url:
            return {
                "parse": 0,  # 告诉 TVBox 这是直链，不用再走网页嗅探
                "url": m3u8_url,
                "header": self.headers
            }
        
        # 提取失败时的回退（通常是因为网络未连通科学环境）
        return {"parse": 1, "url": video_url, "header": self.headers}
