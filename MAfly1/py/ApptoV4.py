import sys, uuid, json
from base.spider import Spider

sys.path.append('..')

class Spider(Spider):
    local_uuid = ''
    config = {}
    parsing_config = {}
    headers = {
        'User-Agent': "Dart/2.19 (dart:io)",
        'Accept-Encoding': "gzip",
        'appto-local-uuid': ''
    }

    def init(self, extend=""):
        try:
            self.host = extend.strip()
            if not self.host.startswith('http'):
                return {}
            self.local_uuid = str(uuid.uuid4())
            self.headers['appto-local-uuid'] = self.local_uuid
            
            # 获取核心配置
            res = self.fetch(f'{self.host}/addons/apptov4/app.php/v1/config/get?p=android&__platform=android', headers=self.headers).json()
            self.config = res.get('data', {})
            
            # 解析播放配置
            parsing_conf = self.config.get('get_parsing', [])
            parsing_config = {}
            for i in parsing_conf:
                if i.get('config'):
                    label = [j['label'] for j in i['config'] if j.get('type') == 'json']
                    if label:
                        parsing_config[i['key']] = label
            self.parsing_config = parsing_config
        except Exception as e:
            print(f'初始化异常：{e}')
            return {}

    def homeContent(self, filter):
        classes = []
        filters = {}
        
        # 1. 优先尝试从 get_home_cate 获取主分类（解决分类消失问题）
        home_cate = self.config.get('get_home_cate', [])
        for i in home_cate:
            cate_id = i.get('cate')
            # 排除 mold=1 的首页推荐，只取有分类 ID 的
            if cate_id is not None and str(cate_id) != '0':
                classes.append({
                    'type_id': str(cate_id),
                    'type_name': i.get('title', '')
                })

        # 2. 从 get_type 获取详细的筛选数据
        types = self.config.get('get_type', [])
        
        # 如果上一步没取到分类，则从 get_type 里取 pid=0 的
        if not classes:
            for t in types:
                if t.get('type_pid') == 0 and t.get('type_name') != '全部':
                    classes.append({
                        'type_id': str(t.get('type_id')),
                        'type_name': t.get('type_name', '').strip()
                    })

        # 3. 组装筛选器 (Filters)
        for t in types:
            t_id = str(t.get('type_id'))
            extend = t.get('type_extend', {})
            f_list = []
            
            def format_filter(key, name, raw_str):
                if not raw_str: return None
                items = [{"n": "全部", "v": ""}]
                for v in raw_str.split(','):
                    if v.strip():
                        items.append({"n": v.strip(), "v": v.strip()})
                return {"key": key, "name": name, "value": items}

            if extend.get('class'):
                f_list.append(format_filter("type_name", "分类", extend['class']))
            if extend.get('area'):
                f_list.append(format_filter("area", "地区", extend['area']))
            if extend.get('lang'):
                f_list.append(format_filter("lang", "语言", extend['lang']))
            if extend.get('year'):
                f_list.append(format_filter("year", "年份", extend['year']))
            
            f_list.append({
                "key": "order",
                "name": "排序",
                "value": [
                    {"n": "最新", "v": "time"},
                    {"n": "最热", "v": "hits"},
                    {"n": "高分", "v": "score"}
                ]
            })
            filters[t_id] = f_list

        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        try:
            # 首页推荐数据
            url = f'{self.host}/addons/apptov4/app.php/v1/home/cateData?id=2&__platform=android'
            res = self.fetch(url, headers=self.headers).json()
            vod_list = []
            sections = res.get('data', {}).get('sections', [])
            for sec in sections:
                for item in sec.get('items', []):
                    vod_list.append({
                        "vod_id": str(item.get('vod_id')),
                        "vod_name": item.get('vod_name'),
                        "vod_pic": item.get('vod_pic'),
                        "vod_remarks": item.get('vod_remarks') or item.get('vod_score') or ''
                    })
            return {'list': vod_list[:30]}
        except:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        params = {
            'type_id': tid,
            'page': pg,
            'pageSize': 21,
            '__platform': 'android',
            'type_name': extend.get('type_name', ''),
            'area': extend.get('area', ''),
            'lang': extend.get('lang', ''),
            'year': extend.get('year', ''),
            'order': extend.get('order', 'time'),
            'sort': 'desc'
        }
        
        url = f"{self.host}/addons/apptov4/app.php/v1/vod/getLists"
        res = self.fetch(url, params=params, headers=self.headers).json()
        data = res.get('data', {})
        return {
            'list': data.get('data', []),
            'page': pg,
            'total': data.get('total', 0)
        }

    def detailContent(self, ids):
        url = f"{self.host}/addons/apptov4/app.php/v1/vod/getVod?id={ids[0]}&__platform=android"
        res = self.fetch(url, headers=self.headers).json()
        data = res.get('data', {})
        
        vod_play_url = []
        vod_play_from = []
        
        for i in data.get('vod_play_list', []):
            play_from = i.get('player_info', {}).get('from', 'default')
            play_show = i.get('player_info', {}).get('show', play_from)
            
            urls = []
            for j in i.get('urls', []):
                urls.append(f"{j['name']}${play_from}@{j['url']}")
            
            vod_play_from.append(play_show)
            vod_play_url.append("#".join(urls))

        video = {
            'vod_id': data.get('vod_id'),
            'vod_name': data.get('vod_name'),
            'vod_pic': data.get('vod_pic'),
            'vod_content': data.get('vod_content'),
            'vod_remarks': data.get('vod_remarks'),
            'vod_director': data.get('vod_director'),
            'vod_actor': data.get('vod_actor'),
            'vod_year': data.get('vod_year'),
            'vod_area': data.get('vod_area'),
            'vod_play_from': "$$$".join(vod_play_from),
            'vod_play_url': "$$$".join(vod_play_url)
        }
        return {'list': [video]}

    def searchContent(self, key, quick, pg='1'):
        # 搜索接口修复
        url = f"{self.host}/addons/apptov4/app.php/v1/vod/getVodSearch?wd={key}&page={pg}&pageSize=20&__platform=android"
        res = self.fetch(url, headers=self.headers).json()
        data = res.get('data', {})
        return {
            'list': data.get('data', []),
            'page': pg,
            'total': data.get('total', 0)
        }

    def playerContent(self, flag, id, vipflags):
        default_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'
        parts = id.split('@')
        if len(parts) != 2:
            return {'parse': 0, 'url': id, 'header': {'User-Agent': default_ua}}
        
        playfrom, rawurl = parts
        label_list = self.parsing_config.get(playfrom, ['默认'])
        
        result = {'parse': 1, 'url': rawurl, 'header': {'User-Agent': default_ua}}
        
        for label in label_list:
            payload = {'play_url': rawurl, 'label': label, 'key': playfrom}
            try:
                proxy_res = self.post(f"{self.host}/addons/apptov4/app.php/v1/parsing/proxy?__platform=android", 
                                     data=payload, headers=self.headers).json()
                if proxy_res.get('code') == 1 and proxy_res.get('data', {}).get('url'):
                    data = proxy_res['data']
                    return {
                        'parse': 0,
                        'url': data.get('url'),
                        'header': {'User-Agent': data.get('UA') or data.get('UserAgent') or default_ua}
                    }
            except:
                continue
        return result

    def getName(self): return "V4修复版"
    def isVideoFormat(self, url): pass
    def manualVideoCheck(self): pass
    def destroy(self): pass
    def localProxy(self, param): pass
