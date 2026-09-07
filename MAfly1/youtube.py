# coding=utf-8
import re
import json
import time
import requests
from urllib.parse import quote, urljoin
from base.spider import Spider as BaseSpider

# ================== 配置区域 ==================
# 固定频道列表（新闻直播一般长期有效）
CHANNELS = [
    {"id": "vr3XyVCR4T0", "name": "中天新闻 24H直播"},
    {"id": "6IquAgfvYmc", "name": "寰宇新闻 24H直播"},
    {"id": "ylYJSBUgaMA", "name": "民视新闻 24H直播"},
]

# 是否启用本地 HLS 代理（强烈建议开启，解决跨域和防盗链）
ENABLE_HLS_PROXY = True

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


class YouTubeLiveExtractor:
    """从 YouTube 页面提取直播 HLS 地址（直连）"""
    def __init__(self, session):
        self.session = session

    def extract_hls(self, video_id):
        """返回直播流的 master m3u8 地址"""
        watch_url = f'https://www.youtube.com/watch?v={video_id}'
        try:
            resp = self.session.get(watch_url, timeout=15)
            resp.raise_for_status()
            page = resp.text

            # 优先从正则匹配 hlsManifestUrl
            match = re.search(r'"hlsManifestUrl"\s*:\s*"(https:[^"]+)"', page)
            if match:
                hls_url = match.group(1).replace(r'\/', '/')
                debug_log('extract hls from page', {'video_id': video_id, 'hls_url': hls_url})
                return hls_url

            # 备用：从 ytInitialPlayerResponse 中提取
            match2 = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', page, re.S)
            if match2:
                try:
                    data = json.loads(match2.group(1))
                    hls_url = data.get('streamingData', {}).get('hlsManifestUrl', '')
                    if hls_url:
                        debug_log('extract hls from player_response', {'video_id': video_id, 'hls_url': hls_url})
                        return hls_url
                except Exception:
                    pass

            debug_log('no hls found', {'video_id': video_id})
            return ''
        except Exception as e:
            debug_log('extract error', {'video_id': video_id, 'error': repr(e)})
            return ''


class Spider(BaseSpider):
    def getName(self):
        return 'YouTube固定频道直播'

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.youtube.com/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.extractor = YouTubeLiveExtractor(self.session)

        # 本地 HLS 代理缓存
        self.hls_cache = {}
        self.hls_key_seq = 0
        self.hls_ttl = {
            'master': 6 * 3600,
            'playlist': 6 * 3600,
            'media': 120,
            'media_retry': 120
        }
        debug_log('spider init', {'enable_hls_proxy': ENABLE_HLS_PROXY})

    def homeContent(self, filter):
        return {
            "class": [{"type_id": "fixed_live", "type_name": "固定频道直播"}]
        }

    def homeVideoContent(self):
        return self.categoryContent("fixed_live", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        items = []
        for ch in CHANNELS:
            items.append({
                "vod_id": ch["id"],
                "vod_name": ch["name"],
                "vod_pic": f"https://i.ytimg.com/vi/{ch['id']}/hqdefault.jpg",
                "vod_remarks": "LIVE"
            })
        return {
            "list": items,
            "page": 1,
            "pagecount": 1,
            "limit": len(items),
            "total": len(items)
        }

    def detailContent(self, ids):
        vid = ids[0]
        name = vid
        for ch in CHANNELS:
            if ch["id"] == vid:
                name = ch["name"]
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
        debug_log('player start', {'video_id': video_id, 'pid': pid})

        # 提取 HLS master 地址
        hls_url = self.extractor.extract_hls(video_id)
        if not hls_url:
            debug_log('hls not found, fallback to web', {'video_id': video_id})
            # 回退：让 TVBox 尝试网页解析
            return {
                "parse": 1,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "header": self.headers
            }

        # 如果启用本地代理，则缓存并返回代理地址
        if ENABLE_HLS_PROXY:
            play_url = self._cache_hls_url(hls_url, video_id, 'master')
        else:
            play_url = hls_url  # 直连原始 HLS

        debug_log('return play url', {'video_id': video_id, 'url_len': len(play_url), 'proxy': ENABLE_HLS_PROXY})
        return {
            "parse": 0,
            "jx": 0,
            "url": play_url,
            "header": self.headers,
            "format": "application/x-mpegURL"
        }

    # ========== 本地 HLS 代理 ==========
    def _cache_hls_url(self, target_url, video_id='', kind='media'):
        self._prune_hls_cache()
        self.hls_key_seq += 1
        key = f'{int(time.time() * 1000)}_{self.hls_key_seq}'
        self.hls_cache[key] = {
            'url': target_url,
            'video_id': video_id,
            'kind': kind,
            'expires': time.time() + self.hls_ttl.get(kind, 180)
        }
        return f'http://127.0.0.1:9978/proxy?do=py&type=hls&key={quote(key)}'

    def _prune_hls_cache(self):
        now = time.time()
        expired = [k for k, v in self.hls_cache.items() if v.get('expires', 0) < now]
        for k in expired:
            self.hls_cache.pop(k, None)

    def localProxy(self, params):
        if params.get('do') != 'py' or params.get('type') != 'hls':
            return None
        key = params.get('key') or ''
        item = self.hls_cache.get(key)
        if not item or item.get('expires', 0) < time.time():
            debug_log('hls proxy missing', {'key': key})
            return [404, 'text/plain', 'HLS 缓存已过期']
        # 续期
        item['expires'] = time.time() + self.hls_ttl.get(item.get('kind'), 180)
        target_url = item.get('url') or ''
        try:
            headers = self._hls_headers(item.get('kind'))
            response = self.session.get(target_url, headers=headers, stream=True, timeout=15)
            retried = False
            if item.get('kind') == 'media' and response.status_code == 403:
                retry_headers = self._hls_headers('media_retry')
                response.close()
                retried = True
                response = self.session.get(target_url, headers=retry_headers, stream=True, timeout=15)
            content_type = response.headers.get('content-type') or ''
            is_m3u8 = item.get('kind') in ('master', 'playlist') or 'mpegurl' in content_type.lower() or target_url.split('?')[0].endswith('.m3u8')
            debug_log('hls proxy response', {
                'key': key,
                'kind': item.get('kind'),
                'status': response.status_code,
                'is_m3u8': is_m3u8,
                'retried': retried
            })
            if is_m3u8:
                text = response.text
                rewritten = self._rewrite_m3u8(text, target_url, item.get('video_id') or '')
                return [response.status_code, 'application/vnd.apple.mpegurl', rewritten,
                        {'Content-Type': 'application/vnd.apple.mpegurl', 'Cache-Control': 'no-cache'}]
            else:
                resp_headers = {'Content-Type': content_type or 'application/octet-stream', 'Cache-Control': 'no-cache'}
                if response.headers.get('content-length'):
                    resp_headers['Content-Length'] = response.headers.get('content-length')
                return [response.status_code, content_type or 'application/octet-stream', response.content, resp_headers]
        except Exception as e:
            debug_log('hls proxy error', {'key': key, 'error': repr(e)})
            return [500, 'text/plain', f'HLS 代理失败: {str(e)}']

    def _hls_headers(self, kind=None):
        if kind == 'media_retry':
            return {
                'User-Agent': 'com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip',
                'Accept': '*/*',
            }
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
