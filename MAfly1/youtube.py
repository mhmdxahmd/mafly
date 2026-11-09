# coding=utf-8
import re
import json
import time
import base64
import requests
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urljoin
from base.spider import Spider as BaseSpider

# ============================================================
# 📺 OKTVBox YouTube 直播源 Python 爬虫 (完整修复增强版)
# ============================================================

# 1. 首页 EPG 地址配置
HEADER_EPG = "https://gitee.com/gsls200808/xmltvepg/raw/master/e9.xml.gz"

# 2. 首页宣传视频源地址
HEADER_PROMO_1_URL = "https://jsnzkpg4.pages.dev/https://mpimg.cn/view.php/7156505e46d701ce78133f2bf0349d4d.mp4"
HEADER_PROMO_2_URL = "https://mpimg.cn/view.php/33d9c1521de0e0e9de09ad5d78668564.mp4"

# 3. 频道独立 LOGO 配置字典
# 规则：优先读取此处的自定义 LOGO 地址；若为空值 "" 或未配置，则自动降级使用 YouTube 视频缩略图
CHANNEL_LOGOS = {
    # 首页宣传视频 LOGO
    "promo_1": "",  # 运行时根据当前日期动态生成：https://epg.112114.xyz/logo/更新时间YYYY.MM.DD.png
    "promo_2": "https://epg.112114.xyz/logo/永久官网https://maflya.com.png",

    # 国际新闻
    "Jxk39FR22so": "",
    "vYRfQo6JMxc": "",
    "gCNeDWCI0vo": "",
    "LuKwFajn37U": "",
    "Ry--eMIjYLQ": "",

    # 儿歌/音乐
    "SIYoSJ-KvHQ": "",
    "ouGgxvUNhok": "",
    "PUqkUzXEtuI": "",
    "wKolkRh5-_k": "",
    "DP8Esat08rs": "",

    # 台湾新闻/财经/宗教
    "wIicpuUDgv4": "",
    "YyOrp1NBkDM": "",
    "m_dhMSvUCIc": "",
    "o_-hSMgpAzs": "",
    "2mCSYvcfhtc": "",
    "kMwoV2js-B4": "",
    "E0zhe2gkXBs": "",
    "V1p33hqPrUk": "",
    "1I2iq41Akmo": "",
    "vr3XyVCR4T0": "",
    "hg4nYb3jE9A": "",
    "jD79P0pWBc4": "",
    "ylYJSBUgaMA": "",
    "yeYC0mbSIOo": "",
    "6IquAgfvYmc": "",
    "w87VGpgd90U": "",
    "yAUQQ0DhPxI": "",
    "5n0y6b0Q25o": "",
    "xLqt2p6Dowo": "",

    # 电视剧
    "UgOi92IvONg": "",
    "HEYnMz9zGhY": "",

    # 台湾电视剧/综艺
    "NyrdWXddfR4": "",
    "K2qsju6byIg": "",
    "OhA_G0s9pqw": "",
    "6ZowCmLBcMY": "",

    # 科技分享
    "FS7IPxmfEms": "",
    "epaQ9FmRooc": "",
    "hWWFQd9aMvc": "",

    # 宗教/佛经
    "eHkFgEVwefI": "",
    "XWQTHTOj6VU": "",
    "Y_OIcysppaA": "",
    "KSIwUaDOl3A": "",
    "xJv_2lF1eb4": "",
    "jgUdjPLf2tY": "",
    "xCHeilSLxHU": "",
    "aAZ3-OZb5K4": "",
    "gahE0BDf_uc": "",
    "8TBKZE3rd1Y": "",
    "Bn7GsaDY614": "",
    "9m-_A7ubjLQ": "",
    "Oc51BmM0dq0": "",
    "E3XJOvJMXBY": "",
}

# 4. YouTube 频道分类列表
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

# 5. YouTube 代理配置
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

def get_proxy_candidates():
    """按顺序生成唯一代理列表：12条主代理严格在前，140条备用代理按顺序在后，保持首次出现的位置去重"""
    seen = set()
    candidates = []
    for p in PRIMARY_PROXIES + BACKUP_PROXIES:
        if p and p not in seen:
            seen.add(p)
            candidates.append(p)
    return candidates

# 全局去重且严格按原始顺序排列的代理候选列表
ALL_PROXIES = get_proxy_candidates()

# 保持旧变量兼容名
HTTP_PROXIES = PRIMARY_PROXIES
SOCKS5_PROXIES = []

# 日志输出文件路径
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
    """根据代理字符串构建 requests 使用的 proxies 字典"""
    if not proxy:
        return None
    return {'http': proxy, 'https': proxy}

def iter_proxies_in_order():
    """严格按照原始顺序迭代完整代理候选列表（主代理 -> 备用代理）"""
    for p in ALL_PROXIES:
        yield p

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

        # 代理健康检测状态记录表（仅记录健康数据，绝对不用于重排序）
        self.proxy_health_status = {}

        # 启动后台代理健康监测线程
        threading.Thread(target=self._check_proxies_async, daemon=True).start()

        debug_log('spider init', {
            'total_proxies': len(ALL_PROXIES),
            'primary_proxies': len(PRIMARY_PROXIES),
            'backup_proxies': len(BACKUP_PROXIES),
        })

    # ---------- 代理健康检测（仅后台记录状态，不改变请求顺序） ----------
    def _check_proxies_async(self):
        """异步并发检测所有代理延迟并保存状态"""
        try:
            with ThreadPoolExecutor(max_workers=30) as executor:
                future_to_proxy = {
                    executor.submit(self._test_proxy, proxy): proxy
                    for proxy in ALL_PROXIES
                }
                for future in as_completed(future_to_proxy):
                    proxy = future_to_proxy[future]
                    try:
                        latency = future.result()
                        if latency is not None:
                            self.proxy_health_status[proxy] = {'ok': True, 'latency': latency}
                        else:
                            self.proxy_health_status[proxy] = {'ok': False, 'latency': None}
                    except Exception:
                        self.proxy_health_status[proxy] = {'ok': False, 'latency': None}
        except Exception as e:
            debug_log('proxy health check error', {'error': str(e)})

    def _test_proxy(self, proxy):
        """测试单个代理连通度"""
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

    # ---------- 统一网络请求代理失败顺序切换核心 ----------
    def request_with_proxy_fallback(self, method, url, **kwargs):
        """
        全网络请求代理失败按序切换核心函数。
        严格按照主代理 -> 备用代理的原始顺序进行单次尝试。
        遇到连接超时、读取超时、网络错误、5xx服务器错误及特定状态码时，自动平滑切换下一条代理。
        """
        kwargs.setdefault('timeout', 15)
        headers = kwargs.pop('headers', None) or {}
        req_headers = self.headers.copy()
        req_headers.update(headers)
        kwargs['headers'] = req_headers

        retry_status_codes = {408, 425, 429, 500, 502, 503, 504}
        last_exception = None

        for proxy in iter_proxies_in_order():
            proxies = get_proxies_dict(proxy)
            kwargs['proxies'] = proxies
            try:
                debug_log('attempting proxy request', {'url': url[:80], 'proxy': proxy})
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 200:
                    return response, proxy
                elif response.status_code in retry_status_codes:
                    debug_log('proxy response retry code', {'proxy': proxy, 'status': response.status_code})
                    continue
                else:
                    return response, proxy
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
                debug_log('proxy request failed, trying next', {'proxy': proxy, 'error': str(e)[:100]})
                last_exception = e
                continue

        if last_exception:
            raise last_exception
        return None, None

    # ---------- 首页宣传与分类 ----------
    def _get_current_date_str(self):
        """获取当天日期字符串 (YYYY.MM.DD)"""
        return datetime.datetime.now().strftime("%Y.%m.%d")

    def _get_promo_items(self):
        """生成首页顶部的两条宣传视频节点数据"""
        date_str = self._get_current_date_str()
        promo_1_name = f"更新时间{date_str}"
        promo_1_pic = self.get_channel_logo("promo_1") or f"https://epg.112114.xyz/logo/更新时间{date_str}.png"

        promo_2_name = "永久官网https://maflya.com"
        promo_2_pic = self.get_channel_logo("promo_2") or "https://epg.112114.xyz/logo/永久官网https://maflya.com.png"

        return [
            {
                "vod_id": "promo_1",
                "vod_name": promo_1_name,
                "vod_pic": self._get_proxy_pic_url(promo_1_pic),
                "vod_remarks": "📢宣传",
                "style": {"type": "rect", "ratio": 1.33}
            },
            {
                "vod_id": "promo_2",
                "vod_name": promo_2_name,
                "vod_pic": self._get_proxy_pic_url(promo_2_pic),
                "vod_remarks": "🌐官网",
                "style": {"type": "rect", "ratio": 1.33}
            }
        ]

    def get_channel_logo(self, channel_id):
        """根据唯一频道 ID 查找配置的频道独立 LOGO 地址；未配置时返回空"""
        return CHANNEL_LOGOS.get(channel_id, "").strip()

    def homeContent(self, filter):
        classes = [{"type_id": name, "type_name": name} for name in CHANNEL_GROUPS.keys()]
        result = {
            "class": classes,
            "header": {
                "epg": HEADER_EPG,
                "lines": self._get_promo_items()
            }
        }
        return result

    def homeVideoContent(self):
        """OKTVBox 首页推荐卡片：顶部展示宣传视频，随后接第一个分类频道"""
        promo_list = self._get_promo_items()
        first_group = list(CHANNEL_GROUPS.keys())[0]
        category_res = self.categoryContent(first_group, "1", False, {})
        cat_list = category_res.get("list", [])
        
        combined_list = promo_list + cat_list
        return {
            "list": combined_list,
            "page": 1,
            "pagecount": 1,
            "limit": len(combined_list),
            "total": len(combined_list)
        }

    def categoryContent(self, tid, pg, filter, extend):
        items = []
        channels = CHANNEL_GROUPS.get(tid, [])
        for vid, name in channels:
            # 优先匹配独立 LOGO，未配置则降级为 YouTube 视频缩略图
            custom_logo = self.get_channel_logo(vid)
            pic_url = custom_logo if custom_logo else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self._get_proxy_pic_url(pic_url),
                "vod_remarks": "LIVE"
            })
        return {"list": items, "page": 1, "pagecount": 1, "limit": len(items), "total": len(items)}

    def detailContent(self, ids):
        vid = ids[0]
        # 拦截并单独生成两条宣传视频的播放详情
        if vid == "promo_1":
            date_str = self._get_current_date_str()
            promo_1_pic = self.get_channel_logo("promo_1") or f"https://epg.112114.xyz/logo/更新时间{date_str}.png"
            return {"list": [{
                "vod_id": "promo_1",
                "vod_name": f"更新时间{date_str}",
                "vod_pic": self._get_proxy_pic_url(promo_1_pic),
                "vod_play_from": "OKTVBox宣传",
                "vod_play_url": f"宣传视频1${HEADER_PROMO_1_URL}"
            }]}
        elif vid == "promo_2":
            promo_2_pic = self.get_channel_logo("promo_2") or "https://epg.112114.xyz/logo/永久官网https://maflya.com.png"
            return {"list": [{
                "vod_id": "promo_2",
                "vod_name": "永久官网https://maflya.com",
                "vod_pic": self._get_proxy_pic_url(promo_2_pic),
                "vod_play_from": "OKTVBox宣传",
                "vod_play_url": f"宣传视频2${HEADER_PROMO_2_URL}"
            }]}

        name = vid
        for group_channels in CHANNEL_GROUPS.values():
            for ch_vid, ch_name in group_channels:
                if ch_vid == vid:
                    name = ch_name
                    break
        
        custom_logo = self.get_channel_logo(vid)
        pic_url = custom_logo if custom_logo else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

        return {"list": [{
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": self._get_proxy_pic_url(pic_url),
            "vod_play_from": "YouTube直播",
            "vod_play_url": f"直播线路${vid}@live"
        }]}

    def playerContent(self, flag, pid, vipFlags):
        raw_pid = pid.split('$')[-1]
        video_id = raw_pid.rsplit('@', 1)[0] if '@' in raw_pid else raw_pid
        debug_log('player start', {'video_id': video_id})

        # 1. 拦截直接播放 MP4 格式的宣传视频
        if video_id.endswith('.mp4') or video_id.startswith('http://') or video_id.startswith('https://'):
            debug_log('playing direct video url', {'url': video_id})
            return {
                "parse": 0,
                "jx": 0,
                "url": video_id,
                "header": self.headers
            }

        # 2. 正常解析并播放 YouTube HLS 直播流
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

    # ---------- HLS 智能获取逻辑 ----------
    def _get_hls_with_proxy(self, video_id):
        """
        按顺序迭代代理。对同一条代理：
        1. 尝试使用 Player API (web -> android -> ios) 获取 HLS。
        2. API 全部失败后，尝试在该代理下进行页面解析。
        3. 同一代理的 API 和页面解析均失败后，再按原始顺序切换下一条代理。
        """
        watch_url = f'https://www.youtube.com/watch?v={video_id}'

        for proxy in iter_proxies_in_order():
            proxies = get_proxies_dict(proxy)
            debug_log('trying proxy for hls', {'video_id': video_id, 'proxy': proxy})
            
            # 步骤 1：同代理 API 尝试
            hls_api = self._try_player_api_with_single_proxy(video_id, watch_url, proxy, proxies)
            if hls_api:
                debug_log('hls obtained via player api', {'proxy': proxy})
                return hls_api

            # 步骤 2：同代理 页面 HTML 解析尝试
            hls_page = self._try_page_extract_with_single_proxy(watch_url, proxies)
            if hls_page:
                debug_log('hls obtained via page scraping', {'proxy': proxy})
                return hls_page

        return ''

    def _try_player_api_with_single_proxy(self, video_id, watch_url, proxy, proxies):
        """在单条代理下尝试通过 Player API 获取 HLS 链接"""
        try:
            resp = self.session.get(watch_url, proxies=proxies, timeout=12)
            if resp.status_code != 200:
                return ''
            page = resp.text
            api_key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', page)
            if not api_key_match:
                return ''
            api_key = api_key_match.group(1)
            api_url = f'https://www.youtube.com/youtubei/v1/player?key={api_key}'

            client_configs = [
                ('web', {'clientName': 'WEB', 'clientVersion': '2.20240310.01.00'}),
                ('android', {'clientName': 'ANDROID', 'clientVersion': '21.02.35', 'androidSdkVersion': 30}),
                ('ios', {'clientName': 'IOS', 'clientVersion': '21.02.3'}),
            ]

            for c_name, config in client_configs:
                try:
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
                    api_resp = self.session.post(api_url, json=payload, headers=headers, proxies=proxies, timeout=10)
                    if api_resp.status_code == 200:
                        data = api_resp.json()
                        hls = data.get('streamingData', {}).get('hlsManifestUrl', '')
                        if hls:
                            return hls
                except Exception:
                    continue
        except Exception:
            pass
        return ''

    def _try_page_extract_with_single_proxy(self, watch_url, proxies):
        """在单条代理下解析网页内容提取 HLS 链接"""
        try:
            resp = self.session.get(watch_url, proxies=proxies, timeout=12)
            if resp.status_code == 200:
                return self._extract_hls_from_page(resp.text)
        except Exception:
            pass
        return ''

    def _extract_hls_from_page(self, page):
        if not page:
            return ''
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
            except Exception:
                pass
        
        matches = re.findall(r'"(https://[^"]*?\.m3u8[^"]*)"', page)
        if matches:
            return matches[0].replace(r'\/', '/')
        return ''

    # ---------- 本地代理与数据转发 ----------
    def _get_proxy_pic_url(self, original_url):
        """保留原有图片 Base64 编码本地代理格式"""
        if not original_url:
            return ""
        encoded = base64.b64encode(original_url.encode('utf-8')).decode('utf-8')
        return f'http://127.0.0.1:9978/proxy?do=py&type=pic&url={encoded}'

    def _cache_hls_url(self, target_url, video_id='', kind='media'):
        """生成本地 HLS 转发缓存链接"""
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
        """图片代理：按原始顺序尝试代理，支持代理失败按序平滑切换"""
        try:
            encoded_url = params.get('url') or ''
            try:
                original_url = base64.b64decode(encoded_url).decode('utf-8')
            except Exception:
                return [400, 'text/plain', 'Invalid Base64 URL']

            cache_key = f'pic_{encoded_url[:60]}'
            if cache_key in self.hls_cache:
                item = self.hls_cache[cache_key]
                if item.get('expires', 0) > time.time():
                    return [200, item.get('content_type', 'image/jpeg'), item.get('content'),
                            {'Cache-Control': 'public, max-age=3600'}]

            headers = {
                'User-Agent': self.headers['User-Agent'],
                'Referer': 'https://www.youtube.com/',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            }

            resp, _ = self.request_with_proxy_fallback('GET', original_url, headers=headers, timeout=12)

            if resp and resp.status_code == 200:
                content_type = resp.headers.get('content-type', 'image/jpeg')
                content = resp.content
                self.hls_cache[cache_key] = {
                    'content': content,
                    'content_type': content_type,
                    'expires': time.time() + self.hls_ttl.get('pic', 3600)
                }
                return [200, content_type, content, {'Cache-Control': 'public, max-age=3600'}]
            else:
                return [404, 'text/plain', 'Image load failed']
        except Exception as e:
            debug_log('proxy pic error', {'error': str(e)[:200]})
            return [500, 'text/plain', f'Image proxy error: {str(e)}']

    def _proxy_hls(self, params):
        """HLS m3u8 主列表/子列表/TS视频分片代理转发"""
        key = params.get('key') or ''
        item = self.hls_cache.get(key)
        if not item or item.get('expires', 0) < time.time():
            return [404, 'text/plain', 'HLS Cache Expired']

        item['expires'] = time.time() + self.hls_ttl.get(item.get('kind'), 180)
        target_url = item.get('url') or ''

        try:
            headers = self._hls_headers(item.get('kind'))
            resp, _ = self.request_with_proxy_fallback('GET', target_url, headers=headers, stream=True, timeout=15)

            if not resp:
                return [502, 'text/plain', 'HLS proxy request failed across all proxies']

            content_type = resp.headers.get('content-type') or ''
            is_m3u8 = item.get('kind') in ('master', 'playlist') or 'mpegurl' in content_type.lower() or target_url.endswith('.m3u8')
            
            if is_m3u8:
                text = resp.text
                rewritten = self._rewrite_m3u8(text, target_url, item.get('video_id') or '')
                return [resp.status_code, 'application/vnd.apple.mpegurl', rewritten,
                        {'Content-Type': 'application/vnd.apple.mpegurl', 'Cache-Control': 'no-cache'}]
            else:
                return [resp.status_code, content_type or 'application/octet-stream', resp.content,
                        {'Content-Type': content_type or 'application/octet-stream', 'Cache-Control': 'no-cache'}]
        except Exception as e:
            debug_log('local proxy error', {'key': key, 'error': str(e)[:200]})
            return [500, 'text/plain', f'HLS Proxy Error: {str(e)}']

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
        """重写 m3u8 文件，将相对路径转换为绝对路径并代理化"""
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
