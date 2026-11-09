# coding=utf-8
import re
import json
import time
import base64
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urljoin
from base.spider import Spider as BaseSpider

# ============================================================
# 📺 YouTube 频道配置（按用户指定分类和顺序）
# ============================================================
CHANNEL_GROUPS = {
    "国际新闻": [
        ("Jxk39FR22so", "CGTN LIVE"),
        ("vYRfQo6JMxc", "United Nations联合国"),
        ("gCNeDWCI0vo", "Al Jazeera English"),
        ("LuKwFajn37U", "DW News"),
        ("Ry--eMIjYLQ", "凤凰卫视"),
    ],
    "儿歌/音乐": [
        ("SIYoSJ-KvHQ", "YOASOBI - STATION"),
        ("ouGgxvUNhok", "432Hz + 963Hz + 528Hz 深层疗愈"),
        ("PUqkUzXEtuI", "黃明志千萬點閱神曲精選"),
        ("wKolkRh5-_k", "古风歌曲合集"),
        ("DP8Esat08rs", "金庸武俠大戲"),
    ],
    "台湾新闻/财经/宗教": [
        ("wIicpuUDgv4", "正德电视台"),
        ("YyOrp1NBkDM", "生命电视台"),
        ("m_dhMSvUCIc", "TVBS NEWS"),
        ("o_-hSMgpAzs", "TVBS NEWS1"),
        ("2mCSYvcfhtc", "TVBS 新闻HD"),
        ("kMwoV2js-B4", "三立财经"),
        ("E0zhe2gkXBs", "东森LIVE"),
        ("V1p33hqPrUk", "东森新闻"),
        ("1I2iq41Akmo", "东森财经"),
        ("vr3XyVCR4T0", "中天新闻"),
        ("hg4nYb3jE9A", "公视新闻"),
        ("jD79P0pWBc4", "台视新闻"),
        ("ylYJSBUgaMA", "民视新闻"),
        ("yeYC0mbSIOo", "三立新闻网"),
        ("6IquAgfvYmc", "环宇新闻"),
        ("w87VGpgd90U", "环宇新闻台湾台"),
        ("yAUQQ0DhPxI", "环宇财经"),
        ("5n0y6b0Q25o", "镜新闻"),
        ("xLqt2p6Dowo", "非凡财经"),
    ],
    "电视剧": [
        ("UgOi92IvONg", "86版 西游记"),
        ("HEYnMz9zGhY", "楊麗花歌仔戲24小時不無聊直播"),
    ],
    "台湾电视剧/综艺": [
        ("NyrdWXddfR4", "台湾奇案"),
        ("K2qsju6byIg", "藍色水玲瓏"),
        ("OhA_G0s9pqw", "現代嘉慶君"),
        ("6ZowCmLBcMY", "台灣靈異事件"),
    ],
    "科技分享": [
        ("FS7IPxmfEms", "不良林"),
        ("epaQ9FmRooc", "jc-nf那坨"),
        ("hWWFQd9aMvc", "爱分享的小企鹅"),
    ],
    "宗教/佛经": [
        ("eHkFgEVwefI", "華藏衛視"),
        ("XWQTHTOj6VU", "悟道法師講經直播台"),
        ("Y_OIcysppaA", "大悲咒"),
        ("KSIwUaDOl3A", "心经 The Heart Sutra"),
        ("xJv_2lF1eb4", "地藏菩薩本願經"),
        ("jgUdjPLf2tY", "地藏王菩薩心咒"),
        ("xCHeilSLxHU", "綠度母心咒 108遍"),
        ("aAZ3-OZb5K4", "《安土地真言108遍"),
        ("gahE0BDf_uc", "金剛薩埵百字明咒21遍"),
        ("8TBKZE3rd1Y", "九天應元雷聲普化天尊"),
        ("Bn7GsaDY614", "《八大神咒》孟圆辉"),
        ("9m-_A7ubjLQ", "妙觉 24/7 佛曲电台"),
        ("Oc51BmM0dq0", "齊豫 清淨心靈 經典佛曲"),
        ("E3XJOvJMXBY", "12部经典佛经咒语净心合集"),
    ],
}

# ============================================================
# 🌐 YouTube 代理配置
# 主代理：严格按第一组提供的顺序优先使用
# 备用代理：主代理全部不可用/失败时，按第二组顺序接续
# ============================================================
PRIMARY_PROXIES = [
    "https://119.28.24.235:3128",       # 香港_1
    "https://103.86.116.118:443",       # 印度尼西亚_1
    "https://118.184.140.90:58764",     # 美国_42
    "https://138.199.35.206:9002",      # 美国_3
    "https://138.199.35.219:9002",      # 美国_13
    "https://fan.240104.xyz:443",       # HK香港
    "https://fan.226278.xyz:443",       # US美国
    "https://103.86.117.202:443",       # 印尼
    "https://150552-nat-jk.barokah.net.id:443",  # 印尼
    "https://96.5.129.85:443",          # us美国
    "https://87.106.223.158:443",       # NL荷兰
    "https://103.97.88.154:443",        # NL荷兰2
]

BACKUP_PROXIES = [
    "https://146.70.244.18:443",       # 奥地利_1
    "https://31.171.155.210:9443",     # 阿尔巴尼亚_1
    "https://31.171.154.66:443",       # 阿尔巴尼亚_2
    "https://18.200.158.139:443",     # 爱尔兰_1
    "https://149.88.96.12:9443",       # 爱尔兰_2
    "https://146.70.123.98:443",      # 比利时_1
    "https://37.120.156.18:443",      # 波兰_1
    "https://151.115.54.133:443",    # 波兰_2
    "https://151.115.54.133:443",    # 波兰_3
    "https://151.115.54.133:443",    # 波兰_4
    "https://37.120.213.210:9443",   # 瑞士_1
    "https://149.88.27.33:9443",     # 瑞士_2
    "https://149.36.50.129:443",     # 德国_1
    "https://149.36.50.157:443",     # 德国_2
    "https://87.106.223.158:443",    # 德国_3
    "https://158.173.154.3:9002",    # 德国_4
    "https://158.173.154.5:9002",    # 德国_5
    "https://158.173.154.4:9002",    # 德国_6
    "https://193.233.75.115:443",    # 德国_7
    "https://79.127.156.177:9443",   # 德国_8
    "https://158.173.154.2:9002",    # 德国_9
    "https://159.69.94.125:443",     # 德国_10
    "https://193.233.75.115:443",    # 德国_11
    "https://46.29.166.134:1446",    # 俄罗斯_1
    "https://82.65.162.76:443",      # 法国_1
    "https://87.98.174.157:6103",    # 法国_2
    "https://80.124.109.22:8090",    # 法国_3
    "https://213.139.9.142:9443",    # 法国_4
    "https://83.206.1.225:8090",     # 法国_5
    "https://87.98.174.157:6103",    # 法国_6
    "https://51.158.243.91:443",    # 荷兰_1
    "https://84.17.47.125:9002",    # 荷兰_2
    "https://84.17.47.147:9002",    # 荷兰_3
    "https://84.17.47.146:9002",    # 荷兰_4
    "https://103.97.88.154:443",    # 荷兰_5
    "https://84.17.47.149:9002",    # 荷兰_7
    "https://51.158.243.91:443",    # 荷兰_8
    "https://84.17.47.146:9002",    # 荷兰_9
    "https://84.17.47.146:9002",    # 荷兰_10
    "https://84.17.47.149:9002",    # 荷兰_11x
    "https://149.36.51.129:443",    # 荷兰_12
    "https://84.17.47.150:9002",    # 荷兰_13
    "https://84.17.47.147:9002",    # 荷兰_14
    "https://84.17.47.148:9002",    # 荷兰_15
    "https://5.255.118.82:443",     # 荷兰_16
    "https://51.159.225.197:19362", # 荷兰_18
    "https://84.17.47.124:9002",    # 荷兰_19
    "https://149.36.51.157:9443",   # 荷兰_20
    "https://84.17.47.123:9002",    # 荷兰_21
    "https://89.150.35.94:443",     # 荷兰_22
    "https://185.53.129.141:9090",  # 荷兰_23
    "https://185.140.209.235:443",  # 荷兰_25
    "https://185.216.35.130:443",   # 捷克_1
    "https://154.47.29.174:443",    # 克罗地亚_1
    "https://154.47.29.161:443",    # 克罗地亚_2
    "https://109.248.147.66:443",   # 拉脱维亚_1
    "https://185.219.159.16:443",   # 拉脱维亚_2
    "https://185.221.132.242:443",  # 卢森堡_1
    "https://185.221.132.226:443",  # 卢森堡_2
    "https://193.176.84.31:9002",   # 罗马尼亚_1
    "https://193.176.84.26:9002",   # 罗马尼亚_2
    "https://193.176.84.32:9002",   # 罗马尼亚_3
    "https://193.176.84.38:9002",   # 罗马尼亚_4
    "https://193.176.84.38:9002",   # 罗马尼亚_5
    "https://193.176.84.16:9002",   # 罗马尼亚_6
    "https://193.176.84.33:9002",   # 罗马尼亚_7
    "https://193.176.84.24:9002",   # 罗马尼亚_8
    "https://185.163.110.194:443",  # 罗马尼亚_9
    "https://193.176.84.18:9002",   # 罗马尼亚_10
    "https://193.176.84.22:9002",   # 罗马尼亚_11
    "https://193.176.84.39:9002",   # 罗马尼亚_12
    "https://193.176.84.17:9002",   # 罗马尼亚_13
    "https://193.176.84.31:9002",   # 罗马尼亚_14
    "https://193.176.84.21:9002",   # 罗马尼亚_15
    "https://146.70.221.34:443",    # 塞尔维亚_1
    "https://146.70.221.18:443",    # 塞尔维亚_2
    "https://146.70.242.146:443",  # 瑞典_1
    "https://185.245.84.50:9443",   # 丹麦_1
    "https://138.199.35.211:9002",  # 美国_1
    "https://138.199.35.200:9002",  # 美国_2
    "https://138.199.35.206:9002",  # 美国_3
    "https://138.199.35.203:9002",  # 美国_4
    "https://138.199.35.195:9002",  # 美国_5
    "https://138.199.35.195:9002",  # 美国_6
    "https://138.199.35.207:9002",  # 美国_7
    "https://138.199.35.201:9002",  # 美国_8
    "https://138.199.35.210:9002",  # 美国_9
    "https://voteshirleysew.club:443", # 美国_10
    "https://138.199.35.216:9002",  # 美国_11
    "https://138.199.35.206:9002",  # 美国_12
    "https://138.199.35.219:9002",  # 美国_13
    "https://138.199.35.219:9002",  # 美国_14
    "https://138.199.35.198:9002",  # 美国_15
    "https://138.199.35.212:9002",  # 美国_16
    "https://149.34.248.65:443",    # 美国_17
    "https://138.199.35.202:9002",  # 美国_18
    "https://44.217.145.28:8443",   # 美国_19
    "https://129.153.93.183:443",   # 美国_21
    "https://44.248.167.117:8443",  # 美国_22
    "https://167.88.60.242:443",    # 美国_23
    "https://154.47.25.78:9443",    # 美国_24
    "https://68.235.56.59:443",     # 美国_25
    "https://44.217.145.28:8443",   # 美国_26
    "https://12.202.180.10:443",    # 美国_27
    "https://23.133.176.14:443",    # 美国_28
    "https://12.221.146.147:443",  # 美国_29
    "https://18.206.28.143:8443",   # 美国_30
    "https://162.244.227.36:443",  # 美国_31
    "https://38.247.141.135:443",  # 美国_33
    "https://173.42.49.102:8090",  # 美国_34
    "https://44.248.167.117:8443", # 美国_35
    "https://138.199.35.209:9002", # 美国_36
    "https://138.199.35.217:9002", # 美国_37
    "https://138.199.35.204:9002", # 美国_38
    "https://138.199.35.202:9002", # 美国_39
    "https://138.199.35.203:9002", # 美国_40
    "https://138.199.35.207:9002", # 美国_41
    "https://118.184.140.90:58764",# 美国_42
    "https://138.199.35.216:9002", # 美国_43
    "https://130.195.250.34:443",  # 西班牙_1
    "https://82.102.17.178:443",   # 西班牙_2
    "https://130.195.250.18:443",  # 西班牙_3
    "https://119.28.24.235:3128",  # 香港_1
    "https://120.232.204.58:31343",# 香港_2
    "https://154.26.139.24:443",   # 新加坡_1
    "https://23.169.224.34:9443",  # 加拿大_1
    "https://206.223.183.16:443",  # 加拿大_2
    "https://134.65.17.77:443",    # 巴西_1
    "https://120.232.204.58:40583",# 日本_1
    "https://149.22.85.78:443",    # 希腊_1
    "https://103.86.116.118:443",  # 印度尼西亚_1
    "https://212.102.63.61:443",   # 英国_1
    "https://84.17.50.193:443",    # 英国_2
    "https://212.102.63.31:443",   # 英国_3
    "https://185.164.138.156:443", # 英国_4
    "https://149.22.86.14:443",    # 葡萄牙_1
    "https://185.183.105.130:443", # 意大利_1
    "https://93.42.177.250:443",   # 意大利_2
    "https://95.229.15.89:443",    # 意大利_3
    "https://109.248.149.34:443",  # 其他_1
]

# 保持主代理优先、备用代理其次；去重但不改变首次出现的顺序
ALL_PROXIES = list(dict.fromkeys(PRIMARY_PROXIES + BACKUP_PROXIES))

HTTP_PROXIES = PRIMARY_PROXIES
SOCKS5_PROXIES = []

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

def get_proxies_dict(proxy):
    if not proxy:
        return None
    return {'http': proxy, 'https': proxy}

class Spider(BaseSpider):
    def getName(self):
        return 'YouTube直播'

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.youtube.com/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # 本地代理缓存
        self.hls_cache = {}
        self.hls_key_seq = 0
        self.hls_ttl = {
            'master': 6 * 3600,
            'playlist': 6 * 3600,
            'media': 120,
            'pic': 3600,
        }

        # 代理管理
        self.failed_proxies = set()
        self.available_proxies = []

        # 启动异步代理检测
        threading.Thread(target=self._check_proxies_async, daemon=True).start()
        threading.Thread(target=self._refresh_proxies_periodically, daemon=True).start()

        # 今日日期（用于宣传视频）
        today = time.strftime('%Y.%m.%d')
        self.today_date = today

        debug_log('spider init', {
            'total_proxies': len(ALL_PROXIES),
            'primary_proxies': len(PRIMARY_PROXIES),
            'backup_proxies': len(BACKUP_PROXIES),
            'today_date': today,
        })

    # ---------- 代理健康检查 ----------
    def _check_proxies_async(self):
        try:
            results = []
            with ThreadPoolExecutor(max_workers=30) as executor:
                future_to_proxy = {
                    executor.submit(self._test_proxy, proxy): proxy
                    for proxy in ALL_PROXIES
                }
                working = set()
                for future in as_completed(future_to_proxy):
                    proxy = future_to_proxy[future]
                    try:
                        if future.result() is not None:
                            working.add(proxy)
                    except Exception:
                        pass

            self.available_proxies = [p for p in ALL_PROXIES if p in working]

            debug_log('proxy check completed', {
                'total_checked': len(ALL_PROXIES),
                'available': len(self.available_proxies),
                'best': self.available_proxies[0] if self.available_proxies else None,
            })
        except Exception as e:
            debug_log('proxy check error', {'error': str(e)})

    def _test_proxy(self, proxy):
        try:
            start = time.time()
            proxies = get_proxies_dict(proxy)
            test_url = 'https://www.youtube.com/generate_204'
            resp = self.session.get(test_url, proxies=proxies, timeout=5)
            if resp.status_code == 204:
                return time.time() - start
            return None
        except Exception:
            return None

    def _refresh_proxies_periodically(self):
        while True:
            time.sleep(300)
            try:
                self._check_proxies_async()
            except Exception:
                pass

    def _get_working_proxy(self, exclude=None):
        proxy_pool = self.available_proxies if self.available_proxies else ALL_PROXIES
        available = [p for p in proxy_pool if p not in self.failed_proxies]
        if exclude:
            available = [p for p in available if p != exclude]

        if not available:
            self.failed_proxies.clear()
            available = proxy_pool

        return available[0] if available else None

    def _mark_proxy_failed(self, proxy):
        self.failed_proxies.add(proxy)
        debug_log('proxy marked as failed', {'proxy': proxy, 'failed_count': len(self.failed_proxies)})

        if len(self.failed_proxies) >= len(ALL_PROXIES):
            self.failed_proxies.clear()
            debug_log('all proxies failed, cleared failure list')

    # ---------- 代理顺序修复 ----------
    def get_proxy_candidates(self):
        return list(dict.fromkeys(PRIMARY_PROXIES + BACKUP_PROXIES))

    def request_with_proxy_fallback(self, method, url, **kwargs):
        candidates = self.get_proxy_candidates()
        for proxy in candidates:
            if proxy in self.failed_proxies:
                continue
            proxies = get_proxies_dict(proxy)
            kwargs_copy = kwargs.copy()
            kwargs_copy['proxies'] = proxies
            kwargs_copy['timeout'] = 15

            try:
                if method == 'get':
                    resp = self.session.get(url, **kwargs_copy)
                else:
                    resp = self.session.post(url, **kwargs_copy)
                if resp.status_code in (408, 425, 429, 500, 502, 503, 504):
                    self._mark_proxy_failed(proxy)
                    continue
                return resp
            except Exception:
                self._mark_proxy_failed(proxy)
                continue
        return None

    # ---------- 内容加载 ----------
    def homeContent(self, filter):
        today = self.today_date

        # 宣传视频1
        item1 = {
            "vod_id": "youtube_promote_1",
            "vod_name": f"更新时间{today}",
            "vod_pic": f"https://epg.112114.xyz/logo/{today}.png",
            "vod_remarks": "LIVE"
        }
        # 宣传视频2
        item2 = {
            "vod_id": "youtube_promote_2",
            "vod_name": "永久官网 https://maflya.com",
            "vod_pic": "https://epg.112114.xyz/logo/永久官网https://maflya.com.png",
            "vod_remarks": "LIVE"
        }

        classes = [{"type_id": name, "type_name": name} for name in CHANNEL_GROUPS.keys()]
        classes = classes + [{"type_id": "宣传视频", "type_name": "首页宣传视频"}]

        items = [item1, item2]
        return {"class": classes, "list": items, "page": 1, "pagecount": 1, "limit": len(items), "total": len(items)}

    def homeVideoContent(self):
        return self.categoryContent("宣传视频", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        if tid == "宣传视频":
            return self.homeVideoContent()

        items = []
        channels = CHANNEL_GROUPS.get(tid, [])
        for vid, name in channels:
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self._get_proxy_pic_url(f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"),
                "vod_remarks": "LIVE"
            })
        return {"list": items, "page": 1, "pagecount": 1, "limit": len(items), "total": len(items)}

    def detailContent(self, ids):
        vid = ids[0]
        if vid in ("youtube_promote_1", "youtube_promote_2"):
            return {"list": [{
                "vod_id": vid,
                "vod_name": vid,
                "vod_pic": "https://epg.112114.xyz/logo/" + ("更新时间" + self.today_date if vid == "youtube_promote_1" else "永久官网https://maflya.com") + ".png",
                "vod_play_from": "YouTube直播",
                "vod_play_url": f"直播线路${vid}@live"
            }]}
        name = vid
        for group_channels in CHANNEL_GROUPS.values():
            for ch_vid, ch_name in group_channels:
                if ch_vid == vid:
                    name = ch_name
                    break
        return {"list": [{
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": self._get_proxy_pic_url(f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"),
            "vod_play_from": "YouTube直播",
            "vod_play_url": f"直播线路${vid}@live"
        }]}

    def playerContent(self, flag, pid, vipFlags):
        raw_pid = pid.split('$')[-1]
        video_id = raw_pid.rsplit('@', 1)[0] if '@' in raw_pid else raw_pid
        debug_log('player start', {'video_id': video_id})

        hls_url = self._get_hls_with_proxy(video_id)
        if hls_url:
            debug_log('hls obtained', {'video_id': video_id, 'hls_url_len': len(hls_url)})
            play_url = self._cache_hls_url(hls_url, video_id, 'master')
            debug_log('local proxy url', {'video_id': video_id, 'play_url': play_url})
            return {
                "parse": 0,
                "jx": 0,
                "url": play_url,
                "header": self.headers,
                "format": "application/x-mpegURL"
            }
        debug_log('hls not found', {'video_id': video_id})
        return {
            "parse": 1,
            "url": f'https://www.youtube.com/watch?v={video_id}',
            "header": self.headers
        }

    # ---------- HLS 获取 ----------
    def _get_hls_with_proxy(self, video_id):
        watch_url = f'https://www.youtube.com/watch?v={video_id}'
        candidates = self.get_proxy_candidates()
        for proxy in candidates:
            if proxy in self.failed_proxies:
                continue
            proxies = get_proxies_dict(proxy)
            try:
                debug_log('try proxy', {'video_id': video_id, 'proxy': proxy, 'attempt': 1})
                for client_name in ['web', 'android', 'ios']:
                    try:
                        hls = self._try_player_api(video_id, watch_url, proxy, proxies, client_name)
                        if hls:
                            debug_log('hls from api', {'video_id': video_id, 'proxy': proxy, 'client': client_name})
                            return hls
                    except Exception as e:
                        debug_log('api client failed', {'client': client_name, 'error': str(e)[:100]})
                        continue

                resp = self.request_with_proxy_fallback('get', watch_url, timeout=15)
                if resp:
                    page = resp.text
                    hls = self._extract_hls_from_page(page)
                    if hls:
                        debug_log('hls from page', {'video_id': video_id, 'proxy': proxy})
                        return hls
            except Exception as e:
                debug_log('proxy failed', {'video_id': video_id, 'proxy': proxy, 'error': str(e)[:200]})
                self._mark_proxy_failed(proxy)
                continue
        return ''

    def _try_player_api(self, video_id, watch_url, proxy, proxies, client_name):
        resp = self.request_with_proxy_fallback('get', watch_url, timeout=15)
        if not resp:
            return ''
        page = resp.text
        api_key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', page)
        if not api_key_match:
            return ''
        api_key = api_key_match.group(1)
        api_url = f'https://www.youtube.com/youtubei/v1/player?key={api_key}'

        client_configs = {
            'web': {'clientName': 'WEB', 'clientVersion': '2.20240310.01.00'},
            'android': {'clientName': 'ANDROID', 'clientVersion': '21.02.35', 'androidSdkVersion': 30},
            'ios': {'clientName': 'IOS', 'clientVersion': '21.02.3'},
        }
        config = client_configs.get(client_name, client_configs['web'])
        client = {
            'clientName': config['clientName'],
            'clientVersion': config['clientVersion'],
            'hl': 'en',
            'gl': 'US'
        }
        if 'androidSdkVersion' in config:
            client['androidSdkVersion'] = config['androidSdkVersion']

        payload = {
            'context': {'client': client},
            'videoId': video_id,
            'contentCheckOk': True,
            'racyCheckOk': True,
        }
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://www.youtube.com',
            'Referer': watch_url,
        }
        api_resp = self.request_with_proxy_fallback('post', api_url, json=payload, headers=headers, timeout=15)
        if api_resp:
            data = api_resp.json()
            return data.get('streamingData', {}).get('hlsManifestUrl', '')
        return ''

    def _extract_hls_from_page(self, page):
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
            return matches[0].replace(r'\/', '/')
        return ''

    # ---------- 本地代理 ----------
    def _get_proxy_pic_url(self, original_url):
        encoded = base64.b64encode(original_url.encode()).decode()
        return f'http://127.0.0.1:9978/proxy?do=py&type=pic&url={encoded}'

    def _cache_hls_url(self, target_url, video_id='', kind='media'):
        self.hls_key_seq += 1
        key = f'{int(time.time() * 1000)}_{self.hls_key_seq}'
        self.hls_cache[key] = {
            'url': target_url,
            'video_id': video_id,
            'kind': kind,
            'expires': time.time() + self.hls_ttl.get(kind, 180)
        }
        return f'http://127.0.0.1:9978/proxy?do=py&type=hls&key={quote(key)}'

    def localProxy(self, params):
        if params.get('do') != 'py':
            return None
        if params.get('type') == 'pic':
            return self._proxy_pic(params)
        if params.get('type') == 'hls':
            return self._proxy_hls(params)
        return None

    def _proxy_pic(self, params):
        try:
            encoded_url = params.get('url') or ''
            original_url = base64.b64decode(encoded_url).decode()
            cache_key = f'pic_{encoded_url[:50]}'
            if cache_key in self.hls_cache:
                item = self.hls_cache[cache_key]
                if item.get('expires', 0) > time.time():
                    return [200, item.get('content_type', 'image/jpeg'), item.get('content'),
                            {'Cache-Control': 'public, max-age=3600'}]

            proxy = self._get_working_proxy()
            proxies = get_proxies_dict(proxy)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.youtube.com/',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            }
            debug_log('proxy pic', {'url': original_url[:80], 'proxy': proxy})
            try:
                response = self.request_with_proxy_fallback('get', original_url, headers=headers, timeout=15)
            except Exception:
                self._mark_proxy_failed(proxy)
                proxy = self._get_working_proxy(exclude=proxy)
                proxies = get_proxies_dict(proxy)
                response = self.request_with_proxy_fallback('get', original_url, headers=headers, timeout=15)

            if response and response.status_code == 200:
                content_type = response.headers.get('content-type', 'image/jpeg')
                content = response.content
                self.hls_cache[cache_key] = {
                    'content': content,
                    'content_type': content_type,
                    'expires': time.time() + self.hls_ttl.get('pic', 3600)
                }
                return [200, content_type, content, {'Cache-Control': 'public, max-age=3600'}]
            else:
                return [404, 'text/plain', 'Image not found']
        except Exception as e:
            debug_log('proxy pic error', {'error': str(e)[:200]})
            return [500, 'text/plain', f'Image proxy error: {str(e)}']

    def _proxy_hls(self, params):
        key = params.get('key') or ''
        item = self.hls_cache.get(key)
        if not item or item.get('expires', 0) < time.time():
            return [404, 'text/plain', 'HLS 缓存已过期']
        item['expires'] = time.time() + self.hls_ttl.get(item.get('kind'), 180)
        target_url = item.get('url') or ''
        try:
            headers = self._hls_headers(item.get('kind'))
            proxy = self._get_working_proxy()
            proxies = get_proxies_dict(proxy)
            debug_log('local proxy request', {'kind': item.get('kind'), 'proxy': proxy, 'url_tail': target_url[-80:]})
            try:
                response = self.request_with_proxy_fallback('get', target_url, headers=headers, stream=True, timeout=20)
            except Exception:
                self._mark_proxy_failed(proxy)
                proxy = self._get_working_proxy(exclude=proxy)
                proxies = get_proxies_dict(proxy)
                response = self.request_with_proxy_fallback('get', target_url, headers=headers, stream=True, timeout=20)

            content_type = response.headers.get('content-type') or ''
            is_m3u8 = item.get('kind') in ('master', 'playlist') or 'mpegurl' in content_type.lower() or target_url.endswith('.m3u8')
            if is_m3u8:
                text = response.text
                rewritten = self._rewrite_m3u8(text, target_url, item.get('video_id') or '')
                return [response.status_code, 'application/vnd.apple.mpegurl', rewritten,
                        {'Content-Type': 'application/vnd.apple.mpegurl', 'Cache-Control': 'no-cache'}]
            else:
                return [response.status_code, content_type or 'application/octet-stream', response.content,
                        {'Content-Type': content_type or 'application/octet-stream', 'Cache-Control': 'no-cache'}]
        except Exception as e:
            debug_log('local proxy error', {'key': key, 'error': str(e)[:200]})
            return [500, 'text/plain', f'HLS 代理失败: {str(e)}']

    def _hls_headers(self, kind=None):
        headers = self.headers.copy()
        headers['Accept'] = '*/*'
        if kind in ('master', 'playlist'):
            headers['Origin'] = 'https://www.youtube.com'
            headers['Referer'] = 'https://www.youtube.com/'
        elif kind == 'media':
            headers['User-Agent'] = 'com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip'
            headers.pop('Origin', None)
            headers.pop('Referer', None)
        return headers

    def _rewrite_m3u8(self, text, base_url, video_id=''):
        output = []
        for line in (text or '').splitlines():
            stripped = line.strip()
            if not stripped:
                output.append(line)
                continue
            if stripped.startswith('#'):
                output.append(self._rewrite_m3u8_tag(line, base_url, video_id))
                continue
            absolute = urljoin(base_url, stripped)
            kind = 'playlist' if stripped.endswith('.m3u8') else 'media'
            output.append(self._cache_hls_url(absolute, video_id, kind))
        return '\n'.join(output) + '\n'

    def _rewrite_m3u8_tag(self, line, base_url, video_id=''):
        def replace_uri(match):
            raw_url = match.group(1)
            absolute = urljoin(base_url, raw_url)
            proxied = self._cache_hls_url(absolute, video_id, 'media')
            return f'URI="{proxied}"'
        return re.sub(r'URI="([^"]+)"', replace_uri, line)
