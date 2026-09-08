# coding=utf-8
import re
import json
import time
import base64
import requests
from urllib.parse import quote, urljoin
from base.spider import Spider as BaseSpider

# ============================================================
# 📺 频道配置（按分组）
# ============================================================
CHANNEL_GROUPS = {
    "固定新闻": [
        ("vr3XyVCR4T0", "中天新闻 24H直播"),
        ("6IquAgfvYmc", "寰宇新闻 24H直播"),
        ("ylYJSBUgaMA", "民视新闻 24H直播"),
        ("V1p33hqPrUk", "TVBS新闻 24H直播"),
        ("m_dhMSvUCIc", "东森新闻 24H直播"),
        ("fWlRLYXkVxY", "三立新闻 24H直播"),
        ("Ry--eMIjYLQ", "台视新闻 24H直播"),
    ],
    "国际新闻": [
        ("IZK0QUeT2GA", "CGTN LIVE"),
        ("vYRfQo6JMxc", "United Nations联合国"),
        ("yMMTtY_L-y0", "BBC Earth"),
        ("gCNeDWCI0vo", "Al Jazeera English"),
        ("LuKwFajn37U", "DW News"),
        ("vNVp6bxkL1c", "CCTV中文国际"),
        ("Ry--eMIjYLQ", "凤凰卫视"),
    ],
    "实时监测/直播流": [
        ("z_fY1pj1VBw", "象山看台北"),
        ("215ahZ_0rTg", "猫空指南宫"),
        ("_hx5akJfzso", "高雄國際機場"),
        ("My-tDEttvXg", "桃園機場北跑道"),
        ("91PfFoqvuUk", "桃园国际机场即时影像"),
        ("NOZVUBsCDEI", "臺灣桃園國際機場"),
        ("vXvblXi-PGo", "臺北松山機場"),
        ("ygC5wni2DMQ", "香港國際機場即時"),
        ("qQoBmgDKZiI", "東京羽田 3D空港"),
        ("KyT4qSK8lJo", "台灣地震監視"),
        ("ADZTiqEGT8g", "台灣天氣即時監測"),
        ("rvtygG4n6ew", "Live Earthquake"),
        ("iws3rh5vLAQ", "Kilauea Volcano Livestream"),
        ("0FBiyFpV__g", "International Space Station"),
        ("3F0XlKxaqbk", "WorldCam"),
    ],
    "游戏": [
        ("92IaqdAkYO0", "Zelda: Breath Of The Wild"),
    ],
    "儿童动画": [
        ("Fl-WGssGnak", "金刚战士Mighty Morphin Power Rangers"),
        ("bK03WDeq5SI", "啄木鸟Pica-Pau"),
        ("DWPcQ4VlauY", "Shrek 1 - 4 Extended"),
        ("iiRNq1sxr0U", "Rick and Morty"),
        ("L0VqY0s7-5k", "功夫熊猫Kung Fu Panda"),
        ("btP-bWKDVik", "MiniMoments"),
        ("jLzdH2bvle4", "小黄人1-4"),
        ("2Vf5RcQ84z0", "加菲猫"),
        ("q5xC6wv9Ut0", "Nat Geo Kids"),
        ("UavAcv2CBfc", "Shaun the Sheep & Friends"),
        ("rEKifG2XUZg", "TOM and JERRY"),
        ("hNf5__nxw5s", "Marvel HQ"),
        ("SiflAbFG_HI", "Johnny Test - WildBrain"),
        ("RXoDbwZmXV8", "We Bare Bears"),
        ("8B7HWfZ4B9g", "Timmy & Friends"),
        ("JCxdBLVj57g", "Die Schlümpfe"),
        ("uZkaJ3e9nfY", "Adventure Time"),
        ("XfZetbS9084", "Cartoonito"),
        ("OaLXmRtCWO8", "Peppa's Best Bites"),
    ],
    "儿歌/音乐": [
        ("m0TPzUkL57E", "Lalafun - Nursery Rhymes"),
        ("BgAwztE_7hw", "海洋之夜氛围与舒缓睡眠音效"),
        ("q8hw5oKCDp4", "周杰倫24H音樂時光機"),
        ("R62E7cFWX6o", "五月天"),
        ("B7EliniYUrQ", "告五人唱出你的人生BGM"),
        ("SIYoSJ-KvHQ", "YOASOBI - STATION"),
        ("ouGgxvUNhok", "432Hz + 963Hz + 528Hz 深层疗愈"),
        ("PUqkUzXEtuI", "黃明志千萬點閱神曲精選"),
    ],
    "台湾新闻/财经/宗教": [
        ("wIicpuUDgv4", "正德电视台"),
        ("dVkQNH3IfME", "生命电视台"),
        ("m_dhMSvUCIc", "TVBS NEWS"),
        ("o_-hSMgpAzs", "TVBS NEWS1"),
        ("2mCSYvcfhtc", "TVBS 新闻HD"),
        ("kMwoV2js-B4", "三立财经"),
        ("E0zhe2gkXBs", "东森LIVE"),
        ("V1p33hqPrUk", "东森新闻"),
        ("1I2iq41Akmo", "东森财经"),
        ("vr3XyVCR4T0", "中天新闻"),
        ("quwqlazU-c8", "公视新闻"),
        ("wM0g8EoUZ_E", "华视新闻"),
        ("IfRLIAc2HN8", "台视新闻"),
        ("ylYJSBUgaMA", "民视新闻"),
        ("yeYC0mbSIOo", "三立新闻网"),
        ("6IquAgfvYmc", "环宇新闻"),
        ("w87VGpgd90U", "环宇新闻台湾台"),
        ("yAUQQ0DhPxI", "环宇财经"),
        ("5n0y6b0Q25o", "镜新闻"),
        ("xLqt2p6Dowo", "非凡财经"),
    ],
    "电视剧": [
        ("2nhLErwKwbw", "琅琊榜Nirvana in Fire"),
        ("AfaGwTbKH0A", "China Zone 流金岁月"),
        ("eyZ55jMTyMQ", "甄嬛传 24小时"),
        ("et4SqnkNSFo", "潜伏 全集"),
        ("RGCaUT6-hqU", "雍正王朝"),
        ("QF6VpFjkFjw", "康熙王朝"),
        ("wkdREigxTy4", "神断狄仁杰"),
        ("UgOi92IvONg", "86版 西游记"),
        ("G43NInZfoPE", "华纳兄弟"),
        ("89c4owSHL2E", "真人快打MortalKombat"),
        ("sh4N79JlDRo", "变相怪杰TheMask"),
        ("WXbPdjQuCd4", "速度与激情"),
        ("XghNs0Cx6JQ", "尖峰时刻RushHour"),
        ("WVwP298MU7I", "哈利波特HarryPotte"),
        ("5PaRAsJ6gI0", "黑客帝国The Matrix Trilogy"),
        ("AAWoKmDJRaw", "TVB 经典 Sitcom 马拉松"),
        ("HEYnMz9zGhY", "楊麗花歌仔戲24小時"),
    ],
    "电视剧/综艺": [
        ("65bIk97v35Q", "新兵日记"),
        ("NyrdWXddfR4", "台湾奇案"),
        ("K2qsju6byIg", "藍色水玲瓏"),
        ("DSnwGChyQ7M", "我愛我妻我愛子"),
        ("0ePhPlTJbGo", "天才衝衝衝"),
        ("OhA_G0s9pqw", "現代嘉慶君"),
        ("CWT2LdX0H-g", "神機妙算劉伯溫"),
        ("GjXBXz5dl6E", "親戚不計較"),
        ("FOrcD6iEUso", "我的老師叫小賀"),
        ("4PAlNX05N64", "包青天"),
        ("OxL_MrnaHOY", "戲說台灣"),
        ("6ZowCmLBcMY", "台灣靈異事件"),
        ("B4-L2nfGcuE", "BigBearBaldEagleNest老鹰鸟巢"),
        ("S_71wzZMf0M", "憨豆先生Mr Bean"),
    ],
    "科技分享": [
        ("FS7IPxmfEms", "不良林"),
        ("epaQ9FmRooc", "jc-nf那坨"),
        ("u66ExGpIL-s", "爱分享的小企鹅"),
    ],
    "宗教/佛经": [
        ("vWzNi6wDTGI", "華藏衛視"),
        ("xnGL8UoHJYs", "華藏網路念佛堂"),
        ("JCIVsura-0A", "淨空老法師講經直播台"),
        ("XWQTHTOj6VU", "悟道法師講經直播台"),
        ("m5mqdL9704w", "北靈巖山寺"),
        ("oDFtxATBSgY", "淨化音樂"),
        ("Y_OIcysppaA", "大悲咒"),
        ("KSIwUaDOl3A", "心经 The Heart Sutra"),
        ("xJv_2lF1eb4", "地藏菩薩本願經"),
        ("pOFljdLI-M0", "地藏經讀誦"),
        ("jgUdjPLf2tY", "地藏王菩薩心咒"),
        ("180E05O2xWk", "南無地藏王菩薩聖號"),
        ("xCHeilSLxHU", "綠度母心咒 108遍"),
        ("5SFn0nk_mL8", "金刚经-王菲"),
        ("3UyZFJXQ5Is", "觀世音菩薩普門品"),
        ("X6Xw4Ht5-yE", "普庵咒"),
        ("aAZ3-OZb5K4", "安土地真言108遍"),
        ("gahE0BDf_uc", "金剛薩埵百字明咒21遍"),
        ("8TBKZE3rd1Y", "九天應元雷聲普化天尊"),
        ("r6Hj2HeP5kY", "金光神咒"),
        ("Bn7GsaDY614", "八大神咒"),
        ("9m-_A7ubjLQ", "妙觉 24/7 佛曲电台"),
        ("Oc51BmM0dq0", "齊豫 清淨心靈 經典佛曲"),
    ],
    "AI漫剧-华光大帝": [
        ("ri9DQpGs4vk", "第一集：凌霄法会 马耳大王毙命"),
        ("SN37dVZyQno", "第二集：华光降世"),
        ("DS5KoPJy0ZI", "第三集：灵光除龙王"),
        ("5iF_bqQidgI", "第四集：灵耀被封"),
        ("sqmd0GZ7_RA", "第五集：华光大闹琼花会"),
        ("oMLfz35cC98", "第六集：真武大帝出旗"),
        ("1qMuAel0DaI", "第七集：华光收服千里眼"),
        ("zXelKt_Nx2Y", "第八集：华光投萧家庄"),
        ("3PbqdssVy40", "第十集：华光收火鸦"),
        ("VIH7Ar0Mq4w", "第十一集：华光化观音"),
        ("vJ4MvDPRJ34", "第十二集：哪吒三太子大斗华光"),
        ("aiwr2vdyPO8", "第十三集：华光迎娶铁扇公主"),
        ("O7IgJfqiV2U", "第十四集：华光大闹阴司"),
        ("4liYdHJHGe8", "第十五集：华光结义孙悟空"),
    ],
}

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

def get_proxy():
    if HTTP_PROXIES:
        return HTTP_PROXIES[int(time.time()) % len(HTTP_PROXIES)]
    return None

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
        debug_log('spider init', {'http_proxies': len(HTTP_PROXIES), 'groups': len(CHANNEL_GROUPS)})

    def homeContent(self, filter):
        classes = []
        for group_name in CHANNEL_GROUPS.keys():
            classes.append({"type_id": group_name, "type_name": group_name})
        return {"class": classes}

    def homeVideoContent(self):
        # 默认显示第一个分组
        first_group = list(CHANNEL_GROUPS.keys())[0]
        return self.categoryContent(first_group, "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
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
        name = vid
        
        # 在所有分组中查找频道名
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

        # 通过 HTTP 代理获取 HLS
        hls_url = self._get_hls_with_proxy(video_id)
        
        if hls_url:
            debug_log('hls obtained', {'video_id': video_id, 'hls_url_len': len(hls_url)})
            
            # 缓存并返回本地代理地址
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

    def _get_hls_with_proxy(self, video_id):
        """通过 HTTP 代理获取 HLS 地址"""
        watch_url = f'https://www.youtube.com/watch?v={video_id}'
        
        for i, proxy in enumerate(HTTP_PROXIES):
            proxies = {'http': proxy, 'https': proxy}
            
            try:
                debug_log('try proxy', {'video_id': video_id, 'proxy': proxy, 'attempt': i+1})
                
                # 使用不同的客户端尝试
                for client_name in ['web', 'android', 'ios']:
                    try:
                        hls = self._try_player_api(video_id, watch_url, proxy, proxies, client_name)
                        if hls:
                            debug_log('hls from api', {'video_id': video_id, 'proxy': proxy, 'client': client_name})
                            return hls
                    except Exception as e:
                        debug_log('api client failed', {'client': client_name, 'error': str(e)[:100]})
                        continue
                
                # 如果 API 失败，尝试直接解析页面
                resp = self.session.get(watch_url, proxies=proxies, timeout=15)
                page = resp.text
                hls = self._extract_hls_from_page(page)
                if hls:
                    debug_log('hls from page', {'video_id': video_id, 'proxy': proxy})
                    return hls
                    
            except Exception as e:
                debug_log('proxy failed', {'video_id': video_id, 'proxy': proxy, 'error': str(e)[:200]})
                continue
        
        return ''

    def _try_player_api(self, video_id, watch_url, proxy, proxies, client_name):
        """尝试使用 YouTube Internal API 获取 HLS"""
        # 先获取页面获取 api_key
        resp = self.session.get(watch_url, proxies=proxies, timeout=15)
        page = resp.text
        
        # 提取 api_key
        api_key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', page)
        if not api_key_match:
            return ''
        api_key = api_key_match.group(1)
        
        # 构建 API 请求
        api_url = f'https://www.youtube.com/youtubei/v1/player?key={api_key}'
        
        client_configs = {
            'web': {'clientName': 'WEB', 'clientVersion': '2.20240310.01.00'},
            'android': {'clientName': 'ANDROID', 'clientVersion': '21.02.35', 'androidSdkVersion': 30},
            'ios': {'clientName': 'IOS', 'clientVersion': '21.02.3'},
        }
        
        client_config = client_configs.get(client_name, client_configs['web'])
        client = {
            'clientName': client_config['clientName'],
            'clientVersion': client_config['clientVersion'],
            'hl': 'en',
            'gl': 'US'
        }
        if 'androidSdkVersion' in client_config:
            client['androidSdkVersion'] = client_config['androidSdkVersion']
        
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
        
        api_resp = self.session.post(api_url, json=payload, headers=headers, proxies=proxies, timeout=15)
        data = api_resp.json()
        
        hls = data.get('streamingData', {}).get('hlsManifestUrl', '')
        return hls

    def _extract_hls_from_page(self, page):
        # 方法1
        match = re.search(r'"hlsManifestUrl"\s*:\s*"(https:[^"]+)"', page)
        if match:
            return match.group(1).replace(r'\/', '/')
        
        # 方法2
        match2 = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', page, re.S)
        if match2:
            try:
                data = json.loads(match2.group(1))
                hls = data.get('streamingData', {}).get('hlsManifestUrl')
                if hls:
                    return hls
            except:
                pass
        
        # 方法3
        matches = re.findall(r'"(https://[^"]*?\.m3u8[^"]*)"', page)
        if matches:
            return matches[0].replace(r'\/', '/')
        
        return ''

    # ========== 本地代理 ==========
    def _get_proxy_pic_url(self, original_url):
        """生成图片代理URL"""
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
        
        # 处理图片代理
        if params.get('type') == 'pic':
            return self._proxy_pic(params)
        
        # 处理HLS代理
        if params.get('type') == 'hls':
            return self._proxy_hls(params)
        
        return None

    def _proxy_pic(self, params):
        """代理图片请求"""
        try:
            encoded_url = params.get('url') or ''
            original_url = base64.b64decode(encoded_url).decode()
            
            # 设置缓存
            cache_key = f'pic_{encoded_url[:50]}'
            if cache_key in self.hls_cache:
                item = self.hls_cache[cache_key]
                if item.get('expires', 0) > time.time():
                    return [
                        200,
                        item.get('content_type', 'image/jpeg'),
                        item.get('content'),
                        {'Cache-Control': 'public, max-age=3600'}
                    ]
            
            proxy = get_proxy()
            proxies = {'http': proxy, 'https': proxy}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.youtube.com/',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            }
            
            debug_log('proxy pic', {'url': original_url[:80], 'proxy': proxy})
            
            response = self.session.get(original_url, headers=headers, proxies=proxies, timeout=15)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', 'image/jpeg')
                content = response.content
                
                # 缓存图片
                self.hls_cache[cache_key] = {
                    'content': content,
                    'content_type': content_type,
                    'expires': time.time() + self.hls_ttl.get('pic', 3600)
                }
                
                return [
                    200,
                    content_type,
                    content,
                    {'Cache-Control': 'public, max-age=3600'}
                ]
            else:
                debug_log('pic not found', {'status': response.status_code, 'url': original_url[:80]})
                return [404, 'text/plain', 'Image not found']
                
        except Exception as e:
            debug_log('proxy pic error', {'error': str(e)[:200]})
            return [500, 'text/plain', f'Image proxy error: {str(e)}']

    def _proxy_hls(self, params):
        """代理HLS请求"""
        key = params.get('key') or ''
        item = self.hls_cache.get(key)
        if not item or item.get('expires', 0) < time.time():
            return [404, 'text/plain', 'HLS 缓存已过期']
        
        item['expires'] = time.time() + self.hls_ttl.get(item.get('kind'), 180)
        target_url = item.get('url') or ''
        
        try:
            headers = self._hls_headers(item.get('kind'))
            proxy = get_proxy()
            proxies = {'http': proxy, 'https': proxy}
            
            debug_log('local proxy request', {'kind': item.get('kind'), 'proxy': proxy, 'url_tail': target_url[-80:]})
            
            response = self.session.get(target_url, headers=headers, proxies=proxies, stream=True, timeout=20)
            
            content_type = response.headers.get('content-type') or ''
            is_m3u8 = item.get('kind') in ('master', 'playlist') or 'mpegurl' in content_type.lower() or target_url.endswith('.m3u8')
            
            if is_m3u8:
                text = response.text
                rewritten = self._rewrite_m3u8(text, target_url, item.get('video_id') or '')
                return [
                    response.status_code,
                    'application/vnd.apple.mpegurl',
                    rewritten,
                    {'Content-Type': 'application/vnd.apple.mpegurl', 'Cache-Control': 'no-cache'}
                ]
            else:
                return [
                    response.status_code,
                    content_type or 'application/octet-stream',
                    response.content,
                    {'Content-Type': content_type or 'application/octet-stream', 'Cache-Control': 'no-cache'}
                ]
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
