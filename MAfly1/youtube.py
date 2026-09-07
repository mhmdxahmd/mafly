# coding=utf-8
import re
import sys
import json
import html
import time
from urllib.parse import quote, unquote, urljoin, urlparse
import requests
from base.spider import Spider

sys.path.append('..')

DEBUG_LOG = '/sdcard/Download/ytblive_debug.log'

LIVE_CLASSES = [
    {'type_id': 'my_channels', 'type_name': '我的频道直播'}
]

# ================== 配置区域（可在此修改默认值，或通过 extend 参数覆盖） ==================
DEFAULT_CHANNEL_IDS = [
    # 示例频道 ID，请替换为您自己的频道
    # 'UCXuqSBlHAE6Xw-yeJA0Tunw',  # Linus Tech Tips
    # 'UC_x5XG1OV2P6uZZ5FSM9Ttw',  # Google Developers
]
DEFAULT_API_KEY = ''  # 若填写 YouTube Data API v3 Key，将优先使用 API 检测直播，否则使用页面解析
PROXY_BASE = 'https://x.maflya.com/api/proxy?target='  # 免翻代理前缀
# =====================================================================================


def debug_log(message, data=None):
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
    """判断 URL 是否属于 Google/YouTube 相关域名，需要走代理"""
    try:
        host = urlparse(url).hostname or ''
        host = host.lower()
        google_domains = [
            'youtube.com', 'youtu.be', 'ytimg.com', 'googlevideo.com',
            'googleapis.com', 'google.com', 'gstatic.com', 'googleusercontent.com'
        ]
        return any(host == d or host.endswith('.' + d) for d in google_domains)
    except Exception:
        return False


def apply_proxy(url, proxy_base):
    """如果需要代理，则返回代理后的 URL，否则返回原 URL"""
    if is_google_domain(url):
        return proxy_base + quote(url, safe='')
    return url


class YouTubeLiveLite:
    """YouTube 直播流提取器"""
    def __init__(self, session, headers=None, config=None, proxy_base=None):
        self.session = session
        self.headers = headers or {}
        self.config = config or {}
        self.proxy_base = proxy_base or PROXY_BASE
        self.cache = {}
        self.cache_ttl = int(self.config.get('live_cache_ttl') or 45)

    @staticmethod
    def extract_video_id(text):
        text = str(text or '').strip()
        for pattern in [
            r'(?:v=|/v/|/embed/|/shorts/|youtu\.be/)([0-9A-Za-z_-]{11})',
            r'^([0-9A-Za-z_-]{11})$',
        ]:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        raise Exception('无法识别 YouTube 视频 ID')

    def extract_live(self, url_or_id):
        video_id = self.extract_video_id(url_or_id)
        now = time.time()
        cached = self.cache.get(video_id)
        if cached and cached.get('expires', 0) > now:
            debug_log('live cache hit', {'video_id': video_id, 'ttl': int(cached.get('expires', 0) - now)})
            return cached.get('data')

        watch_url = f'https://www.youtube.com/watch?v={video_id}'
        debug_log('live extract start', {'input': url_or_id, 'video_id': video_id})
        response = self._get(watch_url)
        page = response.text
        player_response = self._extract_initial_player_response(page) or {}
        ytcfg = self._extract_ytcfg(page) or {}
        api_key = ytcfg.get('INNERTUBE_API_KEY') or self._search(r'"INNERTUBE_API_KEY":"([^"]+)"', page)
        visitor_data = self._extract_visitor_data(ytcfg, player_response)
        status_obj = player_response.get('playabilityStatus') or {}
        streaming = player_response.get('streamingData') or {}
        details = player_response.get('videoDetails') or {}

        debug_log('live page parsed', {
            'status': status_obj.get('status'),
            'reason': status_obj.get('reason'),
            'is_live': details.get('isLiveContent'),
            'has_hls': bool(streaming.get('hlsManifestUrl')),
            'has_api_key': bool(api_key),
            'has_visitor': bool(visitor_data),
        })

        page_hls_url = streaming.get('hlsManifestUrl') or ''
        hls_source = 'page' if page_hls_url else ''
        api_data = None
        if api_key:
            api_data = self._call_player_api(video_id, api_key, ytcfg, watch_url, visitor_data)
            if api_data:
                api_streaming = api_data.get('streamingData') or {}
                api_details = api_data.get('videoDetails') or {}
                api_hls_url = api_streaming.get('hlsManifestUrl') or ''
                if api_hls_url:
                    streaming = api_streaming
                    hls_source = api_data.get('_client_name') or 'api'
                elif not page_hls_url and api_streaming:
                    streaming = api_streaming
                    hls_source = api_data.get('_client_name') or 'api_no_hls'
                if api_details:
                    details = api_details
                status_obj = api_data.get('playabilityStatus') or status_obj
        if not (streaming.get('hlsManifestUrl') or '') and page_hls_url:
            streaming = dict(streaming or {})
            streaming['hlsManifestUrl'] = page_hls_url
            hls_source = 'page_fallback'

        hls_url = streaming.get('hlsManifestUrl') or ''
        is_live = bool(details.get('isLiveContent') or hls_url)
        status = status_obj.get('status') or ''
        reason = status_obj.get('reason') or ''
        title = details.get('title') or video_id

        data = {
            'id': video_id,
            'title': title,
            'is_live': is_live,
            'status': status,
            'reason': reason,
            'hls_url': hls_url,
            'duration': int(details.get('lengthSeconds') or 0),
        }
        debug_log('live extract result', {
            'video_id': video_id,
            'status': status,
            'is_live': is_live,
            'has_hls': bool(hls_url),
            'hls_source': hls_source,
            'duration': data.get('duration'),
        })
        self.cache[video_id] = {'data': data, 'expires': time.time() + self.cache_ttl}
        return data

    def _get(self, url, **kwargs):
        # 应用代理
        proxied_url = apply_proxy(url, self.proxy_base)
        headers = self.headers.copy()
        headers.update(kwargs.pop('headers', {}) or {})
        response = self.session.get(proxied_url, headers=headers, timeout=kwargs.pop('timeout', 15), **kwargs)
        response.raise_for_status()
        return response

    def _post_json(self, url, payload, headers=None):
        proxied_url = apply_proxy(url, self.proxy_base)
        final_headers = self.headers.copy()
        final_headers.update({'Content-Type': 'application/json', 'Origin': 'https://www.youtube.com'})
        if headers:
            final_headers.update({k: v for k, v in headers.items() if v})
        response = self.session.post(proxied_url, json=payload, headers=final_headers, timeout=15)
        response.raise_for_status()
        return response.json()

    def _call_player_api(self, video_id, api_key, ytcfg, referer, visitor_data=None):
        context = ytcfg.get('INNERTUBE_CONTEXT') or {
            'client': {'clientName': 'WEB', 'clientVersion': '2.20240310.01.00', 'hl': 'en', 'gl': 'US'}
        }
        clients = [
            {'client': {'clientName': 'ANDROID', 'clientVersion': '21.02.35', 'androidSdkVersion': 30, 'userAgent': 'com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip', 'osName': 'Android', 'osVersion': '11', 'hl': 'en', 'gl': 'US'}},
            {'client': {'clientName': 'IOS', 'clientVersion': '21.02.3', 'deviceMake': 'Apple', 'deviceModel': 'iPhone16,2', 'userAgent': 'com.google.ios.youtube/21.02.3 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)', 'osName': 'iPhone', 'osVersion': '18.3.2.22D82', 'hl': 'en', 'gl': 'US'}},
            {'client': {'clientName': 'MWEB', 'clientVersion': '2.20260115.01.00', 'userAgent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', 'hl': 'en', 'gl': 'US'}},
            context,
        ]
        for ctx in clients:
            client = ctx.get('client') or {}
            client_name = client.get('clientName') or 'WEB'
            try:
                url = f'https://www.youtube.com/youtubei/v1/player?key={quote(api_key)}&prettyPrint=false'
                headers = {
                    'Referer': referer,
                    'X-YouTube-Client-Name': str(self._client_name_id(client_name)),
                    'X-YouTube-Client-Version': client.get('clientVersion') or '',
                }
                if visitor_data:
                    headers['X-Goog-Visitor-Id'] = visitor_data
                if client.get('userAgent'):
                    headers['User-Agent'] = client.get('userAgent')
                payload = {
                    'context': ctx,
                    'videoId': video_id,
                    'contentCheckOk': True,
                    'racyCheckOk': True,
                }
                data = self._post_json(url, payload, headers=headers)
                streaming = data.get('streamingData') or {}
                status = (data.get('playabilityStatus') or {}).get('status')
                debug_log('live api client', {
                    'client': client_name,
                    'status': status,
                    'has_hls': bool(streaming.get('hlsManifestUrl')),
                    'has_streaming': bool(streaming),
                })
                if streaming.get('hlsManifestUrl'):
                    data['_client_name'] = client_name
                    return data
            except Exception as e:
                debug_log('live api client error', {'client': client_name, 'error': repr(e)})
        return None

    def _extract_visitor_data(self, ytcfg, player_response):
        return (
            self.config.get('visitor_data')
            or ytcfg.get('VISITOR_DATA')
            or (((ytcfg.get('INNERTUBE_CONTEXT') or {}).get('client') or {}).get('visitorData'))
            or ((player_response.get('responseContext') or {}).get('visitorData'))
        )

    def _extract_ytcfg(self, text):
        match = re.search(r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', text or '', re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except Exception:
            return None

    def _extract_initial_player_response(self, text):
        return self._extract_json_after(text, 'ytInitialPlayerResponse')

    def _extract_json_after(self, text, marker):
        pos = (text or '').find(marker)
        if pos < 0:
            return None
        start = text.find('{', pos)
        if start < 0:
            return None
        depth = 0
        in_str = None
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if in_str:
                if char == in_str:
                    in_str = None
                continue
            if char in ('"', "'"):
                in_str = char
                continue
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:index + 1])
                    except Exception:
                        return None
        return None

    @staticmethod
    def _search(pattern, text, default=None):
        match = re.search(pattern, text or '', re.S)
        return match.group(1) if match else default

    def _client_name_id(self, client_name):
        return {
            'WEB': 1,
            'MWEB': 2,
            'ANDROID': 3,
            'IOS': 5,
            'TVHTML5': 7,
            'ANDROID_VR': 28,
            'WEB_EMBEDDED_PLAYER': 56,
            'WEB_REMIX': 67,
        }.get(client_name, 1)


class Spider(Spider):
    def getName(self):
        return 'YouTube频道直播'

    def init(self, extend):
        try:
            self.extendDict = json.loads(extend) if extend else {}
        except Exception:
            self.extendDict = {}
        # 频道列表：优先使用 extend 中的 channel_ids，否则使用默认值
        channel_ids = self.extendDict.get('channel_ids', '')
        if isinstance(channel_ids, str):
            channel_ids = [cid.strip() for cid in channel_ids.split(',') if cid.strip()]
        elif isinstance(channel_ids, list):
            channel_ids = [str(cid).strip() for cid in channel_ids if str(cid).strip()]
        else:
            channel_ids = []
        self.channel_ids = channel_ids if channel_ids else DEFAULT_CHANNEL_IDS
        # API Key：优先使用 extend 中的 api_key，否则使用默认值
        self.api_key = self.extendDict.get('api_key', DEFAULT_API_KEY).strip()
        if not self.api_key:
            self.api_key = None
        # 代理前缀（默认使用全局 PROXY_BASE，可通过 extend 覆盖）
        self.proxy_base = self.extendDict.get('proxy_base', PROXY_BASE)

        self.session = requests.Session()
        self.proxy_str = None
        proxy_val = self.extendDict.get('proxy')
        if proxy_val:
            if isinstance(proxy_val, dict):
                self.session.proxies = proxy_val
                self.proxy_str = (proxy_val.get('http') or proxy_val.get('https') or '').replace('http://', '').replace('https://', '')
            elif isinstance(proxy_val, str):
                self.proxy_str = proxy_val.replace('http://', '').replace('https://', '')
                proxy_url = f'http://{self.proxy_str}'
                self.session.proxies = {'http': proxy_url, 'https': proxy_url}
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.youtube.com/'
        }
        self.session.headers.update(self.header)
        self.yt = YouTubeLiveLite(self.session, self.header, self.extendDict, proxy_base=self.proxy_base)
        self.hls_url_cache = {}
        self.hls_proxy_enabled = self.extendDict.get('hls_proxy', True) is not False
        debug_log('spider init', {
            'channel_ids': self.channel_ids,
            'api_key': bool(self.api_key),
            'has_proxy': bool(self.proxy_str or self.session.proxies),
            'hls_proxy': self.hls_proxy_enabled,
            'proxy_base': self.proxy_base
        })

    def homeContent(self, filter):
        return {'class': LIVE_CLASSES}

    def homeVideoContent(self):
        return self.categoryContent('my_channels', '1', False, {})

    def categoryContent(self, cid, page, filter, ext):
        if cid != 'my_channels':
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 0, 'total': 0}
        live_videos = self._get_live_videos_from_channels()
        return {
            'list': live_videos,
            'page': 1,
            'pagecount': 1,
            'limit': len(live_videos),
            'total': len(live_videos)
        }

    def detailContent(self, did):
        video_id = did[0]
        title = self._get_video_title(video_id)
        status = '直播'
        try:
            data = self.yt.extract_live(video_id)
            title = data.get('title') or title
            if data.get('hls_url'):
                status = '直播中'
            elif data.get('status') == 'LIVE_STREAM_OFFLINE':
                status = data.get('reason') or '未开播'
            elif data.get('status') and data.get('status') != 'OK':
                status = data.get('reason') or data.get('status')
            else:
                status = '无HLS'
        except Exception as e:
            debug_log('detail live error', {'video_id': video_id, 'error': repr(e)})
        safe_title = self._safe_title(title)
        vod = {
            'vod_id': video_id,
            'vod_name': title,
            'vod_pic': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
            'vod_remarks': status,
            'vod_play_from': '直播',
            'vod_play_url': f'{safe_title}${video_id}@live'
        }
        return {'list': [vod]}

    def playerContent(self, flag, pid, vipFlags):
        raw_pid = pid.split('$')[-1]
        video_id = raw_pid.rsplit('@', 1)[0] if '@' in raw_pid else raw_pid
        debug_log('player live', {'flag': flag, 'pid': pid, 'video_id': video_id})
        try:
            data = self.yt.extract_live(video_id)
            hls_url = data.get('hls_url') or ''
            if not hls_url:
                status = data.get('status') or 'NO_HLS'
                reason = data.get('reason') or '未获取到直播 HLS 地址'
                debug_log('player live no hls', {'video_id': video_id, 'status': status, 'reason': reason})
                raise Exception(reason)
            if self.extendDict.get('hls_probe'):
                self._probe_hls(video_id, hls_url)
            play_url = hls_url
            if self.hls_proxy_enabled:
                play_url = self._cache_hls_url(hls_url, video_id, 'master')
            debug_log('return live hls', {'video_id': video_id, 'url_len': len(hls_url), 'status': data.get('status'), 'proxy': self.hls_proxy_enabled})
            return {
                'parse': 0,
                'jx': 0,
                'url': play_url,
                'header': self.header,
                'format': 'application/x-mpegURL'
            }
        except Exception as e:
            debug_log('player live error', {'video_id': video_id, 'error': repr(e)})
            return {'parse': 1, 'jx': 1, 'url': pid}

    # ========== 获取频道直播视频 ID ==========
    def _get_live_videos_from_channels(self):
        live_videos = []
        seen_ids = set()
        for channel_id in self.channel_ids:
            try:
                if self.api_key:
                    video_id, title = self._get_live_video_from_api(channel_id)
                else:
                    video_id, title = self._get_live_video_from_page(channel_id)
                if video_id and video_id not in seen_ids:
                    seen_ids.add(video_id)
                    live_videos.append({
                        'vod_id': video_id,
                        'vod_name': title or video_id,
                        'vod_pic': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                        'vod_remarks': '直播'
                    })
            except Exception as e:
                debug_log('channel live check error', {'channel_id': channel_id, 'error': repr(e)})
        return live_videos

    def _get_live_video_from_api(self, channel_id):
        url = 'https://www.googleapis.com/youtube/v3/search'
        params = {
            'part': 'snippet',
            'channelId': channel_id,
            'eventType': 'live',
            'type': 'video',
            'key': self.api_key,
            'maxResults': 1
        }
        try:
            # 该请求也是 Google 域名，需要代理
            proxied_url = apply_proxy(url, self.proxy_base)
            resp = self.session.get(proxied_url, params=params, timeout=10)
            data = resp.json()
            items = data.get('items', [])
            if items:
                item = items[0]
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                return video_id, title
            return None, None
        except Exception as e:
            debug_log('api search error', {'channel_id': channel_id, 'error': repr(e)})
            return None, None

    def _get_live_video_from_page(self, channel_id):
        live_url = f'https://www.youtube.com/channel/{channel_id}/live'
        try:
            proxied_url = apply_proxy(live_url, self.proxy_base)
            resp = self.session.get(proxied_url, allow_redirects=False, timeout=10)
            debug_log('channel live page', {
                'channel_id': channel_id,
                'status': resp.status_code,
                'location': resp.headers.get('Location', '')
            })
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get('Location', '')
                match = re.search(r'[?&]v=([0-9A-Za-z_-]{11})', location)
                if match:
                    return match.group(1), ''
            if resp.status_code == 200:
                html_text = resp.text
                match = re.search(r'"videoId":"([0-9A-Za-z_-]{11})"', html_text)
                if match:
                    return match.group(1), ''
            return None, None
        except Exception as e:
            debug_log('channel live page error', {'channel_id': channel_id, 'error': repr(e)})
            return None, None

    # ========== 以下方法保留并适当调整代理 ==========
    def _probe_hls(self, video_id, hls_url):
        try:
            # HLS 请求走代理
            proxied_url = apply_proxy(hls_url, self.proxy_base)
            response = self.session.get(proxied_url, headers=self.header, timeout=10)
            full_text = response.text or ''
            text = full_text[:5000]
            lines = [line.strip() for line in full_text.splitlines() if line.strip()][:12]
            variant_url = self._pick_variant_playlist(hls_url, full_text)
            debug_log('hls master probe', {
                'video_id': video_id,
                'status': response.status_code,
                'content_type': response.headers.get('content-type'),
                'length': len(response.text or ''),
                'has_extm3u': text.startswith('#EXTM3U'),
                'has_stream_inf': '#EXT-X-STREAM-INF' in text,
                'has_media_sequence': '#EXT-X-MEDIA-SEQUENCE' in text,
                'variant': bool(variant_url),
                'sample': lines,
            })
            if variant_url:
                child_proxied = apply_proxy(variant_url, self.proxy_base)
                child = self.session.get(child_proxied, headers=self.header, timeout=10)
                child_text = child.text[:5000] if child.text else ''
                child_lines = [line.strip() for line in child_text.splitlines() if line.strip()][:12]
                debug_log('hls variant probe', {
                    'video_id': video_id,
                    'status': child.status_code,
                    'content_type': child.headers.get('content-type'),
                    'length': len(child.text or ''),
                    'has_extm3u': child_text.startswith('#EXTM3U'),
                    'has_media_sequence': '#EXT-X-MEDIA-SEQUENCE' in child_text,
                    'has_segments': bool(re.search(r'^[^#].+', child_text, re.M)),
                    'sample': child_lines,
                })
        except Exception as e:
            debug_log('hls probe error', {'video_id': video_id, 'error': repr(e)})

    def _pick_variant_playlist(self, base_url, text):
        lines = [line.strip() for line in (text or '').splitlines()]
        best_score = -1
        best_url = ''
        for index, line in enumerate(lines):
            if not line.startswith('#EXT-X-STREAM-INF'):
                continue
            score = 0
            bandwidth = re.search(r'BANDWIDTH=(\d+)', line)
            resolution = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
            if bandwidth:
                score += int(bandwidth.group(1))
            if resolution:
                score += int(resolution.group(1)) * int(resolution.group(2))
            for next_line in lines[index + 1:]:
                if not next_line or next_line.startswith('#'):
                    continue
                if score > best_score:
                    best_score = score
                    best_url = urljoin(base_url, next_line)
                break
        return best_url

    HLS_TTL = {'master': 6 * 3600, 'playlist': 6 * 3600, 'media': 120, 'media_retry': 120}

    def _hls_ttl(self, kind):
        return self.HLS_TTL.get(kind, 180)

    def _prune_hls_cache(self):
        now = time.time()
        expired = [k for k, v in self.hls_url_cache.items() if v.get('expires', 0) < now]
        for k in expired:
            self.hls_url_cache.pop(k, None)

    def _cache_hls_url(self, target_url, video_id='', kind='media'):
        self._prune_hls_cache()
        self._hls_key_seq = getattr(self, '_hls_key_seq', 0) + 1
        key = f'{int(time.time() * 1000)}_{self._hls_key_seq}'
        self.hls_url_cache[key] = {
            'url': target_url,
            'video_id': video_id,
            'kind': kind,
            'expires': time.time() + self._hls_ttl(kind),
        }
        return f'http://127.0.0.1:9978/proxy?do=py&type=hls&key={quote(key)}'

    def localProxy(self, params):
        if params.get('do') != 'py' or params.get('type') != 'hls':
            return None
        key = params.get('key') or ''
        item = self.hls_url_cache.get(key)
        if not item or item.get('expires', 0) < time.time():
            debug_log('hls proxy missing', {'key': key})
            return [404, 'text/plain', 'HLS 缓存已过期']
        item['expires'] = time.time() + self._hls_ttl(item.get('kind'))
        target_url = item.get('url') or ''
        try:
            headers = self._hls_headers(target_url, item.get('kind'))
            # 对 HLS 请求也应用代理
            proxied_url = apply_proxy(target_url, self.proxy_base)
            response = self.session.get(proxied_url, headers=headers, stream=True, timeout=15)
            retried = False
            if item.get('kind') == 'media' and response.status_code == 403:
                retry_headers = self._hls_headers(target_url, 'media_retry')
                response.close()
                retried = True
                response = self.session.get(proxied_url, headers=retry_headers, stream=True, timeout=15)
            content_type = response.headers.get('content-type') or ''
            is_m3u8 = item.get('kind') in ('master', 'playlist') or 'mpegurl' in content_type.lower() or target_url.split('?')[0].endswith('.m3u8')
            debug_log('hls proxy response', {
                'key': key,
                'kind': item.get('kind'),
                'status': response.status_code,
                'content_type': content_type,
                'is_m3u8': is_m3u8,
                'url_len': len(target_url),
                'path_tail': target_url.split('?')[0][-80:],
                'retried': retried,
            })
            if is_m3u8:
                text = response.text
                rewritten = self._rewrite_m3u8(text, target_url, item.get('video_id') or '')
                return [response.status_code, 'application/vnd.apple.mpegurl', rewritten, {'Content-Type': 'application/vnd.apple.mpegurl', 'Cache-Control': 'no-cache'}]
            resp_headers = {'Content-Type': content_type or 'application/octet-stream', 'Cache-Control': 'no-cache'}
            if response.headers.get('content-length'):
                resp_headers['Content-Length'] = response.headers.get('content-length')
            return [response.status_code, content_type or 'application/octet-stream', response.content, resp_headers]
        except Exception as e:
            debug_log('hls proxy error', {'key': key, 'error': repr(e)})
            return [500, 'text/plain', f'HLS 代理失败: {str(e)}']

    def _hls_headers(self, target_url, kind=None):
        if kind == 'media_retry':
            return {
                'User-Agent': 'com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip',
                'Accept': '*/*',
            }
        headers = self.header.copy()
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
            kind = 'playlist' if stripped.endswith('.m3u8') or '/hls_playlist/' in stripped else 'media'
            output.append(self._cache_hls_url(absolute, video_id, kind))
        return '\n'.join(output) + '\n'

    def _rewrite_m3u8_tag(self, line, base_url, video_id=''):
        def replace_uri(match):
            raw_url = match.group(1)
            absolute = urljoin(base_url, raw_url)
            proxied = self._cache_hls_url(absolute, video_id, 'media')
            return f'URI="{proxied}"'
        return re.sub(r'URI="([^"]+)"', replace_uri, line)

    def _get_video_title(self, video_id):
        try:
            url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
            proxied_url = apply_proxy(url, self.proxy_base)
            response = self.session.get(proxied_url, timeout=5)
            return response.json().get('title') or video_id
        except Exception:
            return video_id

    def _safe_title(self, title):
        if not title:
            return 'live'
        return re.sub(r'[#$@%&!?*|\\/:<>]', ' ', title)[:60]
