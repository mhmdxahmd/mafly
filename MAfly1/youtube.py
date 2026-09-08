# coding=utf-8
import re
import json
import time
import requests
from urllib.parse import quote, urljoin
from base.spider import Spider as BaseSpider

# ================== 配置区域 ==================
# 所有频道列表（带分组）
FIXED_CHANNELS = [
    # 国际新闻
    ("IZK0QUeT2GA", "CGTN LIVE", "国际新闻"),
    ("vYRfQo6JMxc", "United Nations联合国", "国际新闻"),
    ("yMMTtY_L-y0", "BBC Earth", "国际新闻"),
    ("gCNeDWCI0vo", "Al Jazeera English", "国际新闻"),
    ("LuKwFajn37U", "DW News", "国际新闻"),
    ("vNVp6bxkL1c", "CCTV中文国际", "国际新闻"),
    ("Ry--eMIjYLQ", "凤凰卫视", "国际新闻"),
    
    # 实时监测
    ("z_fY1pj1VBw", "象山看台北", "实时监测"),
    ("215ahZ_0rTg", "猫空指南宫", "实时监测"),
    ("_hx5akJfzso", "高雄國際機場", "实时监测"),
    ("My-tDEttvXg", "桃園機場北跑道", "实时监测"),
    ("91PfFoqvuUk", "桃园国际机场即时影像", "实时监测"),
    ("NOZVUBsCDEI", "臺灣桃園國際機場", "实时监测"),
    ("vXvblXi-PGo", "臺北松山機場", "实时监测"),
    ("ygC5wni2DMQ", "香港國際機場即時", "实时监测"),
    ("qQoBmgDKZiI", "東京羽田 3D空港", "实时监测"),
    ("KyT4qSK8lJo", "台灣地震監視", "实时监测"),
    ("ADZTiqEGT8g", "台灣天氣即時監測", "实时监测"),
    ("rvtygG4n6ew", "Live Earthquake", "实时监测"),
    ("iws3rh5vLAQ", "Kilauea Volcano Livestream", "实时监测"),
    ("0FBiyFpV__g", "International Space Station", "实时监测"),
    ("3F0XlKxaqbk", "WorldCam", "实时监测"),
    
    # 游戏
    ("92IaqdAkYO0", "Zelda: Breath Of The Wild", "游戏"),
    
    # 儿童动画
    ("Fl-WGssGnak", "金刚战士Mighty Morphin Power Rangers", "儿童动画"),
    ("bK03WDeq5SI", "啄木鸟Pica-Pau", "儿童动画"),
    ("DWPcQ4VlauY", "Shrek 1 - 4 Extended", "儿童动画"),
    ("iiRNq1sxr0U", "Rick and Morty", "儿童动画"),
    ("L0VqY0s7-5k", "功夫熊猫Kung Fu Panda", "儿童动画"),
    ("btP-bWKDVik", "MiniMoments", "儿童动画"),
    ("jLzdH2bvle4", "小黄人1-4", "儿童动画"),
    ("2Vf5RcQ84z0", "加菲猫", "儿童动画"),
    ("q5xC6wv9Ut0", "Nat Geo Kids", "儿童动画"),
    ("UavAcv2CBfc", "Shaun the Sheep & Friends", "儿童动画"),
    ("rEKifG2XUZg", "TOM and JERRY", "儿童动画"),
    ("hNf5__nxw5s", "Marvel HQ", "儿童动画"),
    ("SiflAbFG_HI", "Johnny Test - WildBrain", "儿童动画"),
    ("RXoDbwZmXV8", "We Bare Bears", "儿童动画"),
    ("8B7HWfZ4B9g", "Timmy & Friends", "儿童动画"),
    ("JCxdBLVj57g", "Die Schlümpfe • Auf Deutsch", "儿童动画"),
    ("uZkaJ3e9nfY", "Adventure Time", "儿童动画"),
    ("XfZetbS9084", "Cartoonito", "儿童动画"),
    ("OaLXmRtCWO8", "Peppa's Best Bites", "儿童动画"),
    
    # 音乐
    ("m0TPzUkL57E", "Lalafun - Nursery Rhymes", "音乐"),
    ("BgAwztE_7hw", "海洋之夜氛围与舒缓睡眠音效", "音乐"),
    ("q8hw5oKCDp4", "周杰倫24H音樂時光機", "音乐"),
    ("R62E7cFWX6o", "五月天", "音乐"),
    ("B7EliniYUrQ", "告五人唱出你的人生BGM", "音乐"),
    ("SIYoSJ-KvHQ", "YOASOBI - STATION", "音乐"),
    ("ouGgxvUNhok", "432Hz + 963Hz + 528Hz 深层疗愈", "音乐"),
    ("PUqkUzXEtuI", "黃明志千萬點閱神曲精選", "音乐"),
    
    # 台湾新闻
    ("wIicpuUDgv4", "正德电视台", "台湾新闻"),
    ("dVkQNH3IfME", "生命电视台", "台湾新闻"),
    ("m_dhMSvUCIc", "TVBS NEWS", "台湾新闻"),
    ("o_-hSMgpAzs", "TVBS NEWS1", "台湾新闻"),
    ("2mCSYvcfhtc", "TVBS 新闻HD", "台湾新闻"),
    ("kMwoV2js-B4", "三立财经", "台湾新闻"),
    ("E0zhe2gkXBs", "东森LIVE", "台湾新闻"),
    ("V1p33hqPrUk", "东森新闻", "台湾新闻"),
    ("1I2iq41Akmo", "东森财经", "台湾新闻"),
    ("vr3XyVCR4T0", "中天新闻", "台湾新闻"),
    ("quwqlazU-c8", "公视新闻", "台湾新闻"),
    ("wM0g8EoUZ_E", "华视新闻", "台湾新闻"),
    ("IfRLIAc2HN8", "台视新闻", "台湾新闻"),
    ("ylYJSBUgaMA", "民视新闻", "台湾新闻"),
    ("yeYC0mbSIOo", "三立新闻网", "台湾新闻"),
    ("6IquAgfvYmc", "环宇新闻", "台湾新闻"),
    ("w87VGpgd90U", "环宇新闻台湾台", "台湾新闻"),
    ("yAUQQ0DhPxI", "环宇财经", "台湾新闻"),
    ("5n0y6b0Q25o", "镜新闻", "台湾新闻"),
    ("xLqt2p6Dowo", "非凡财经", "台湾新闻"),
    
    # 电视剧
    ("2nhLErwKwbw", "琅琊榜Nirvana in Fire", "电视剧"),
    ("AfaGwTbKH0A", "China Zone 流金岁月", "电视剧"),
    ("eyZ55jMTyMQ", "甄嬛传 24小时", "电视剧"),
    ("et4SqnkNSFo", "潜伏 全集", "电视剧"),
    ("RGCaUT6-hqU", "雍正王朝", "电视剧"),
    ("QF6VpFjkFjw", "康熙王朝", "电视剧"),
    ("wkdREigxTy4", "神断狄仁杰", "电视剧"),
    ("UgOi92IvONg", "86版 西游记", "电视剧"),
    ("G43NInZfoPE", "华纳兄弟", "电视剧"),
    ("89c4owSHL2E", "真人快打MortalKombat", "电视剧"),
    ("sh4N79JlDRo", "变相怪杰TheMask", "电视剧"),
    ("WXbPdjQuCd4", "速度与激情", "电视剧"),
    ("XghNs0Cx6JQ", "尖峰时刻RushHour", "电视剧"),
    ("WVwP298MU7I", "哈利波特HarryPotte", "电视剧"),
    ("5PaRAsJ6gI0", "黑客帝国The Matrix Trilogy", "电视剧"),
    ("AAWoKmDJRaw", "TVB 经典 Sitcom 马拉松", "电视剧"),
    ("HEYnMz9zGhY", "楊麗花歌仔戲24小時", "电视剧"),
    
    # 台湾综艺
    ("65bIk97v35Q", "新兵日记", "台湾综艺"),
    ("NyrdWXddfR4", "台湾奇案", "台湾综艺"),
    ("K2qsju6byIg", "藍色水玲瓏", "台湾综艺"),
    ("DSnwGChyQ7M", "我愛我妻我愛子", "台湾综艺"),
    ("0ePhPlTJbGo", "天才衝衝衝", "台湾综艺"),
    ("OhA_G0s9pqw", "現代嘉慶君", "台湾综艺"),
    ("CWT2LdX0H-g", "神機妙算劉伯溫", "台湾综艺"),
    ("GjXBXz5dl6E", "親戚不計較", "台湾综艺"),
    ("FOrcD6iEUso", "我的老師叫小賀", "台湾综艺"),
    ("4PAlNX05N64", "包青天", "台湾综艺"),
    ("OxL_MrnaHOY", "戲說台灣", "台湾综艺"),
    ("6ZowCmLBcMY", "台灣靈異事件", "台湾综艺"),
    ("B4-L2nfGcuE", "BigBearBaldEagleNest老鹰鸟巢", "台湾综艺"),
    ("S_71wzZMf0M", "憨豆先生Mr Bean", "台湾综艺"),
    
    # 科技分享
    ("FS7IPxmfEms", "不良林", "科技分享"),
    ("epaQ9FmRooc", "jc-nf那坨", "科技分享"),
    ("u66ExGpIL-s", "爱分享的小企鹅", "科技分享"),
    
    # 宗教
    ("vWzNi6wDTGI", "華藏衛視", "宗教"),
    ("xnGL8UoHJYs", "華藏網路念佛堂", "宗教"),
    ("JCIVsura-0A", "淨空老法師講經直播台", "宗教"),
    ("XWQTHTOj6VU", "悟道法師講經直播台", "宗教"),
    ("m5mqdL9704w", "北靈巖山寺", "宗教"),
    ("oDFtxATBSgY", "淨化音樂", "宗教"),
    ("Y_OIcysppaA", "大悲咒", "宗教"),
    ("KSIwUaDOl3A", "心经 The Heart Sutra", "宗教"),
    ("xJv_2lF1eb4", "地藏菩薩本願經", "宗教"),
    ("pOFljdLI-M0", "地藏經讀誦2小時18分版本", "宗教"),
    ("jgUdjPLf2tY", "地藏王菩薩心咒", "宗教"),
    ("180E05O2xWk", "南無地藏王菩薩聖號", "宗教"),
    ("xCHeilSLxHU", "綠度母心咒 108遍", "宗教"),
    ("5SFn0nk_mL8", "金刚经-王菲", "宗教"),
    ("3UyZFJXQ5Is", "《觀世音菩薩普門品》念誦", "宗教"),
    ("X6Xw4Ht5-yE", "普庵咒（台語課誦版）", "宗教"),
    ("aAZ3-OZb5K4", "安土地真言108遍", "宗教"),
    ("gahE0BDf_uc", "金剛薩埵百字明咒21遍", "宗教"),
    ("8TBKZE3rd1Y", "九天應元雷聲普化天尊", "宗教"),
    ("r6Hj2HeP5kY", "金光神咒｜吳政憲道長", "宗教"),
    ("Bn7GsaDY614", "《八大神咒》孟圆辉", "宗教"),
    ("9m-_A7ubjLQ", "妙觉 24/7 佛曲电台", "宗教"),
    ("Oc51BmM0dq0", "齊豫 清淨心靈 經典佛曲", "宗教"),
    
    # AI漫剧
    ("ri9DQpGs4vk", "第一集：凌霄法会 马耳大王毙命", "AI漫剧"),
    ("SN37dVZyQno", "第二集：华光降世", "AI漫剧"),
    ("DS5KoPJy0ZI", "第三集：灵光除龙王", "AI漫剧"),
    ("5iF_bqQidgI", "第四集：灵耀被封", "AI漫剧"),
    ("sqmd0GZ7_RA", "第五集：华光大闹琼花会", "AI漫剧"),
    ("oMLfz35cC98", "第六集：真武大帝出旗", "AI漫剧"),
    ("1qMuAel0DaI", "第七集：华光收服千里眼", "AI漫剧"),
    ("zXelKt_Nx2Y", "第八集：华光投萧家庄", "AI漫剧"),
    ("3PbqdssVy40", "第十集：华光收火鸦", "AI漫剧"),
    ("VIH7Ar0Mq4w", "第十一集：华光化观音", "AI漫剧"),
    ("vJ4MvDPRJ34", "第十二集：哪吒三太子大斗华光", "AI漫剧"),
    ("aiwr2vdyPO8", "第十三集：华光迎娶铁扇公主", "AI漫剧"),
    ("O7IgJfqiV2U", "第十四集：华光大闹阴司", "AI漫剧"),
    ("4liYdHJHGe8", "第十五集：华光结义孙悟空", "AI漫剧"),
]

# 默认代理列表（留空，从 extend 参数读取）
DEFAULT_PROXIES = []

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

class Spider(BaseSpider):
    def getName(self):
        return 'YouTube直播'

    def init(self, extend=""):
        # 解析 extend 参数
        self.extendDict = {}
        try:
            if extend:
                if isinstance(extend, str):
                    self.extendDict = json.loads(extend)
                elif isinstance(extend, dict):
                    self.extendDict = extend
        except:
            pass
        
        # 从 extend 参数读取代理列表
        proxy_str = self.extendDict.get('proxies', '')
        if proxy_str:
            if isinstance(proxy_str, str):
                self.HTTP_PROXIES = [p.strip() for p in proxy_str.split(',') if p.strip()]
            elif isinstance(proxy_str, list):
                self.HTTP_PROXIES = [str(p).strip() for p in proxy_str if str(p).strip()]
            else:
                self.HTTP_PROXIES = DEFAULT_PROXIES
        else:
            self.HTTP_PROXIES = DEFAULT_PROXIES
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.youtube.com/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        self.hls_cache = {}
        self.hls_key_seq = 0
        self.hls_ttl = {
            'master': 6 * 3600,
            'playlist': 6 * 3600,
            'media': 120,
        }
        debug_log('spider init', {'channels': len(FIXED_CHANNELS), 'http_proxies': len(self.HTTP_PROXIES)})

    def get_proxy(self):
        if self.HTTP_PROXIES:
            return self.HTTP_PROXIES[int(time.time()) % len(self.HTTP_PROXIES)]
        return None

    def homeContent(self, filter):
        """返回分组列表"""
        # 提取所有唯一分组
        categories = []
        seen = set()
        for vid, name, category in FIXED_CHANNELS:
            if category not in seen:
                seen.add(category)
                categories.append({
                    "type_id": category,
                    "type_name": category
                })
        
        return {"class": categories}

    def homeVideoContent(self):
        # 默认显示第一个分组
        if FIXED_CHANNELS:
            return self.categoryContent(FIXED_CHANNELS[0][2], "1", False, {})
        return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def categoryContent(self, tid, pg, filter, extend):
        """返回指定分组的频道列表"""
        items = []
        for vid, name, category in FIXED_CHANNELS:
            if category == tid:
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
        for ch_vid, ch_name, ch_category in FIXED_CHANNELS:
            if ch_vid == vid:
                name = ch_name
                break
        return {"list": [{
            "vod_id": vid,
            "vod_name": name,
            "vod_play_from": "YouTube直播",
            "vod_play_url": f"直播线路${vid}@live"
        }]}

    def searchContent(self, key, quick, pg=1):
        """搜索 YouTube 视频（免翻）"""
        debug_log('search start', {'key': key, 'page': pg})
        
        search_url = f'https://www.youtube.com/results?search_query={quote(key)}&sp=EgJAAQ%253D%253D'
        
        for proxy in self.HTTP_PROXIES:
            proxies = {'http': proxy, 'https': proxy}
            try:
                resp = self.session.get(search_url, proxies=proxies, timeout=15)
                page = resp.text
                
                videos = self._extract_search_results(page)
                if videos:
                    debug_log('search success', {'key': key, 'proxy': proxy, 'count': len(videos)})
                    return {
                        'list': videos,
                        'page': int(pg),
                        'pagecount': 1,
                        'limit': len(videos),
                        'total': len(videos)
                    }
            except Exception as e:
                debug_log('search proxy failed', {'proxy': proxy, 'error': str(e)[:100]})
                continue
        
        return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 0, 'total': 0}

    def _extract_search_results(self, page):
        videos = []
        seen = set()
        
        match = re.search(r'ytInitialData\s*=\s*({.+?});', page, re.S)
        if not match:
            return videos
        
        try:
            data = json.loads(match.group(1))
            
            def scan(obj):
                if len(videos) >= 30:
                    return
                if isinstance(obj, dict):
                    if 'videoRenderer' in obj:
                        renderer = obj['videoRenderer']
                        video_id = renderer.get('videoId', '')
                        title = ''
                        title_obj = renderer.get('title', {})
                        if 'runs' in title_obj:
                            title = ''.join([r.get('text', '') for r in title_obj['runs']])
                        elif 'simpleText' in title_obj:
                            title = title_obj['simpleText']
                        
                        is_live = False
                        badges = json.dumps(renderer.get('badges', []))
                        if 'LIVE' in badges or 'live' in badges.lower():
                            is_live = True
                        
                        if video_id and video_id not in seen and title:
                            seen.add(video_id)
                            videos.append({
                                'vod_id': video_id,
                                'vod_name': title,
                                'vod_pic': f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',
                                'vod_remarks': 'LIVE' if is_live else '视频'
                            })
                    
                    for value in obj.values():
                        scan(value)
                elif isinstance(obj, list):
                    for item in obj:
                        scan(item)
            
            scan(data)
        except Exception as e:
            debug_log('search parse error', {'error': repr(e)})
        
        return videos[:30]

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

    def _get_hls_with_proxy(self, video_id):
        watch_url = f'https://www.youtube.com/watch?v={video_id}'
        
        for i, proxy in enumerate(self.HTTP_PROXIES):
            proxies = {'http': proxy, 'https': proxy}
            
            try:
                debug_log('try proxy', {'video_id': video_id, 'proxy': proxy, 'attempt': i+1})
                
                for client_name in ['web', 'android', 'ios']:
                    try:
                        hls = self._try_player_api(video_id, watch_url, proxy, proxies, client_name)
                        if hls:
                            debug_log('hls from api', {'video_id': video_id, 'proxy': proxy, 'client': client_name})
                            return hls
                    except Exception as e:
                        debug_log('api client failed', {'client': client_name, 'error': str(e)[:100]})
                        continue
                
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
        resp = self.session.get(watch_url, proxies=proxies, timeout=15)
        page = resp.text
        
        api_key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', page)
        if not api_key_match:
            return ''
        api_key = api_key_match.group(1)
        
        context_match = re.search(r'ytcfg\.set\(({.+?})\);', page, re.S)
        context = {}
        if context_match:
            try:
                context = json.loads(context_match.group(1))
            except:
                pass
        
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
        if params.get('do') != 'py' or params.get('type') != 'hls':
            return None
        
        key = params.get('key') or ''
        item = self.hls_cache.get(key)
        if not item or item.get('expires', 0) < time.time():
            return [404, 'text/plain', 'HLS 缓存已过期']
        
        item['expires'] = time.time() + self.hls_ttl.get(item.get('kind'), 180)
        target_url = item.get('url') or ''
        
        try:
            headers = self._hls_headers(item.get('kind'))
            proxy = self.get_proxy()
            proxies = {'http': proxy, 'https': proxy}
            
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
