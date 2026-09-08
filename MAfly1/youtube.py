# coding=utf-8
import re
import json
import time
import requests
from urllib.parse import quote, urljoin
from base.spider import Spider as BaseSpider

FIXED_CHANNELS = [
    ("vr3XyVCR4T0", "中天新闻 24H直播"),
    ("6IquAgfvYmc", "寰宇新闻 24H直播"),
    ("ylYJSBUgaMA", "民视新闻 24H直播"),
    ("V1p33hqPrUk", "TVBS新闻 24H直播"),
    ("m_dhMSvUCIc", "东森新闻 24H直播"),
    ("fWlRLYXkVxY", "三立新闻 24H直播"),
    ("Ry--eMIjYLQ", "台视新闻 24H直播"),
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

class Spider(BaseSpider):
    def getName(self):
        return 'YouTube新闻直播'

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
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
        debug_log('spider init', {'channels': len(FIXED_CHANNELS)})

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

        # 请求 YouTube 页面（直连，因为开梯子时能访问）
        watch_url = f'https://www.youtube.com/watch?v={video_id}'
        try:
            resp = self.session.get(watch_url, timeout=15)
            page = resp.text
            hls_url = self._extract_hls(page)
            
            if hls_url:
                debug_log('hls extracted', {'video_id': video_id, 'hls_url_len': len(hls_url)})
                
                # 缓存 HLS，返回本地代理地址
                play_url = self._cache_hls_url(hls_url, video_id, 'master')
                debug_log('local proxy url', {'video_id': video_id, 'play_url': play_url})
                
                return {
                    "parse": 0,
                    "jx": 0,
                    "url": play_url,
                    "header": self.headers,
                    "format": "application/x-mpegURL"
                }
        except Exception as e:
            debug_log('extract error', {'video_id': video_id, 'error': repr(e)})

        return {
            "parse": 1,
            "url": watch_url,
            "header": self.headers
        }

    def _extract_hls(self, page):
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

    # ========== 本地代理 ==========
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
            
            debug_log('local proxy request', {
                'key': key,
                'kind': item.get('kind'),
                'url_tail': target_url[-80:]
            })
            
            # 直连请求 HLS（开梯子时能访问）
            response = self.session.get(target_url, headers=headers, stream=True, timeout=20)
            
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
            debug_log('local proxy error', {'key': key, 'error': repr(e)})
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
