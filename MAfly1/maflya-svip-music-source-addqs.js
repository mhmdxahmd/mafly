/*! 
 * @name 👽maflya音源(三改整合版) - 落雪 + sollin 最终兼容版
 * @description 基于安妮独家音源v4 + 星海音乐源v3.2.12 + 汽水音乐重构
 * @version v3.0.2120 | 2026-11-26
 * @author 👽maflya | 裤佬 | 安妮 | 星海
 */

const { EVENT_NAMES, request, on, send, env } = globalThis.lx;

// ==================== 1. 核心配置与常量 ====================
const CACHE_TTL = 1000 * 60 * 20; // 缓存20分钟
const YNX_API = 'http://ynx.de5.net/API/music.php'; // 来自小熙脚本的强力代理接口
const TIMEOUT = 10000; // 稍长的超时，应对咪咕、酷我的复杂请求

// 完整音质声明
const MUSIC_QUALITIES = {
  tx: ['128k', '192k', '320k', 'flac', 'flac24bit', 'hires', 'atmos', 'atmos_plus', 'master'],
  wy: ['128k', '320k', 'flac', 'flac24bit', 'hires', 'atmos', 'master'],
  kw: ['128k', '320k', 'flac', 'flac24bit', 'hires', 'atmos', 'atmos_plus', 'master'],
  kg: ['128k', '320k', 'flac', 'flac24bit', 'hires', 'atmos', 'master'],
  mg: ['128k', '320k', 'flac', 'flac24bit', 'hires', 'atmos', 'master'],
  qs: ['128k', '320k', 'flac', 'flac24bit'],
  sd: ['128k', '320k', 'flac', 'flac24bit']
};

const QUALITY_ORDER = ['jymaster', 'master', 'atmos_plus', 'atmos', 'sky', 'jyeffect', 'hires', 'flac24bit', 'flac', '320k', '192k', '128k'];

// ==================== 2. 工具函数 (源自小熙 & Hei Music) ====================
const URL_CACHE = new Map();
const getCache = (key) => {
  const item = URL_CACHE.get(key);
  if (!item) return null;
  if (Date.now() > item.expire) {
    URL_CACHE.delete(key);
    return null;
  }
  return item.data;
};
const setCache = (key, data) => {
  URL_CACHE.set(key, { data, expire: Date.now() + CACHE_TTL });
};

const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
function getRandomMix(len = 6) {
  let str = '';
  for(let i = 0; i < len; i++){
    str += chars[Math.floor(Math.random() * chars.length)];
  }
  return str;
}
function randomBytes(size = 4) {
  if (size <= 0) return 0;
  const max = Math.min(Math.pow(256, size) - 1, Number.MAX_SAFE_INTEGER);
  return Math.floor(Math.random() * max);
}

// 统一请求封装，包含 302 Location 提取
const httpRequest = (url, options = {}) => new Promise((resolve, reject) => {
  const timeoutMs = options.timeout || TIMEOUT;
  const timer = setTimeout(() => reject(new Error(`请求超时 (${timeoutMs}ms)`)), timeoutMs);
  
  request(url, {
    method: options.method || 'GET',
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
      ...options.headers
    },
    ...(options.body !== undefined ? { body: options.body } : {})
  }, (err, resp) => {
    clearTimeout(timer);
    if (err) return reject(err instanceof Error ? err : new Error(String(err)));
    if (!resp) return reject(new Error('空响应'));
    
    let body = resp.body;
    if (typeof body === 'string' && (body.trim().startsWith('{') || body.trim().startsWith('['))) {
      try { body = JSON.parse(body); } catch (e) {}
    }
    
    // 提取重定向
    const headers = resp.headers || {};
    const location = headers.location || headers.Location;
    if (location && location.startsWith('http')) {
       return resolve({ body: '', statusCode: 302, headers, url: location });
    }

    resolve({ body, statusCode: resp.statusCode || 200, headers, url: resp.url });
  });
});

// 探测 302 真实链接
const probeRealUrl = async (url) => {
  try {
    const res = await httpRequest(url, { method: 'GET', headers: { 'Range': 'bytes=0-0' } });
    if (res.url && res.url.startsWith('http')) return res.url;
  } catch (e) {}
  return url;
};

// 全并发竞速
const raceApis = async (apis) => {
  if (!apis || apis.length === 0) throw new Error('无可用接口');
  return await Promise.any(apis.map(fn => fn()));
};

// 星海动态 Token 生成
const generateToken = () => {
  const payload = { device_id: 'lx-online', ip: '0.0.0.0', timestamp: Math.floor(Date.now() / 1000), random: Math.random().toString(36).substring(2) };
  return btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
};

// 酷狗 Hash 深度提取
const getKgHash = (info) => {
  if (info._types) {
    if (info._types['flac']?.hash) return info._types['flac'].hash;
    if (info._types['320k']?.hash) return info._types['320k'].hash;
    if (info._types['128k']?.hash) return info._types['128k'].hash;
  }
  return info.SQFileHash || info.HQFileHash || info.FileHash || info.hash || info.songmid || '';
};

// ==================== 3. 专属解析模块 (小熙原版逻辑) ====================

// 咪咕音乐 (来自小熙的路径替换大法)
const getMgUrl = async (musicInfo, quality) => {
  const songId = musicInfo.songmid || musicInfo.songId || musicInfo.id;
  if (!songId) throw new Error('【咪咕】songmid 为空，无法请求播放接口');
  
  const MG_QUALITY = {
    '128k': { replacePath: '标清高清/MP3_128_16_Stero', ext: '.mp3' },
    '320k': { replacePath: '标清高清/MP3_320_16_Stero', ext: '.mp3' },
    'flac': { replacePath: '歌曲下载/flac', ext: '.flac' },
    'flac24bit': { replacePath: '歌曲下载/flac_24bit', ext: '.flac' },
    'hires': { replacePath: '歌曲下载/flac_24bit', ext: '.flac' },
    'atmos': { replacePath: '歌曲下载/wav_3d', ext: '.wav' },
    'master': { replacePath: '歌曲下载/wav_32bit', ext: '.wav' }
  };
  const mgQueryParts = [];
  mgQueryParts.push('lowerQualityContentId=');
  mgQueryParts.push('netType=00');
  mgQueryParts.push('resourceType=2');
  mgQueryParts.push(`songId=${encodeURIComponent(String(songId))}`);
  mgQueryParts.push('toneFlag=PQ');
  if (musicInfo.albumId) {
    mgQueryParts.push(`albumId=${encodeURIComponent(String(musicInfo.albumId))}`);
  }
  const apiUrl = `https://app.c.nf.migu.cn/MIGUM2.0/strategy/listen-url/v2.4?${mgQueryParts.join('&')}`;
  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36',
    'Connection': 'Keep-Alive',
    'Referer': 'https://m.music.migu.cn/v4/',
    'channel': '014000D',
    'By': '3c0effb5be907dd7fc209a9001a18713',
    'Cookie': `SESSION=LOVELOVEYX${getRandomMix(22)}`
  };
  
  const resp = await httpRequest(apiUrl, { method: 'GET', headers, timeout: 8000 });
  let json = typeof resp.body === 'string' ? JSON.parse(resp.body) : resp.body;
  
  if (!json) throw new Error('咪咕接口返回空JSON对象');
  if (json.code !== '000000') throw new Error(`咪咕接口异常 code:${json.code}, msg:${json.info || json.msg}`);
  if (!json?.data) throw new Error('咪咕返回data字段为空');
  
  const baseUrl = json.data?.url;
  if (!baseUrl) throw new Error('咪咕接口无基础128k播放地址');
  
  const cfg = MG_QUALITY[quality] || MG_QUALITY['128k'];
  const originCfg = MG_QUALITY['128k'];
  let decodeUrl = decodeURIComponent(baseUrl || '');
  decodeUrl = decodeUrl.split('?')[0];
  decodeUrl = decodeUrl.replace(originCfg.replacePath, cfg.replacePath);
  decodeUrl = decodeUrl.replace(/(\.mp3|\.flac)$/i, cfg.ext);
  return encodeURI(decodeUrl);
};

// 酷我流媒体底层 (来自小熙)
const getKwStreamInner = async (musicInfo, quality) => {
  const KW_STREAM_LEVEL_MAP = { 'atmos':'atmos', 'atmos_plus':'atmos_plus', 'master':'master' };
  const level = KW_STREAM_LEVEL_MAP[quality] || 'master';
  const songIdTmp = musicInfo?.songmid || musicInfo?.id || musicInfo?.hash || musicInfo?.songId || musicInfo?.musicId;
  if (!songIdTmp) throw new Error('酷我流媒体: 找不到歌曲ID');
  const songId = String(songIdTmp).trim();
  return 'http://175.27.166.236:8928/kwstream?id=' + encodeURIComponent(songId) + '&level=' + level + '&stream=1';
};

// 酷我音乐 (来自小熙的 Mobi 签名请求)
const getKwUrl = async (musicInfo, quality) => {
  const streamQualities = ['atmos','atmos_plus','master'];
  if(streamQualities.includes(quality)){
    return await getKwStreamInner(musicInfo, quality);
  }
  const rid = musicInfo?.songmid || musicInfo?.id || musicInfo?.rid;
  if (!rid) throw new Error('酷我歌曲ID不存在(songmid为空)');
  
  const qualityMap = {
    '128k': { br:'128k', format:'mp3' },
    '320k': { br:'320kmp3', format:'mp3' },
    'flac': { br:'2000kflac', format:'flac' },
    'flac24bit': { br:'4000kflac', format:'flac' },
    'hires': { br:'4000kflac', format:'flac' }
  };
  const cfg = qualityMap[quality];
  if (!cfg) throw new Error(`酷我不支持的音质: ${quality}`);
  
  const user = randomBytes(4);
  const kwQueryParts = [];
  kwQueryParts.push('f=web');
  kwQueryParts.push('user=' + user);
  kwQueryParts.push('loginUid=0');
  kwQueryParts.push('source=kwplayercar_ar_6.0.0.9_B_jiakong_vh.apk');
  kwQueryParts.push('type=convert_url_with_sign');
  kwQueryParts.push('rid=' + rid);
  kwQueryParts.push('br=' + cfg.br);
  kwQueryParts.push('format=' + cfg.format);
  kwQueryParts.push('mode=prefetch');
  kwQueryParts.push('from=PC');
  kwQueryParts.push('surl=1');
  kwQueryParts.push('apiv=1');
  
  const reqUrl = 'https://changenotice.kuwo.cn/mobi.s?' + kwQueryParts.join('&');
  const res = await httpRequest(reqUrl, {timeout: 10000 });
  
  if(!res?.body) throw new Error('酷我接口无返回内容');
  if (res.body.code !== 200) throw new Error(res.body.msg || '酷我音乐解析失败');
  
  const musicUrl = res.body.data?.surl || res.body.data?.url;
  if (!musicUrl) throw new Error('酷我未获取到有效播放链接');
  return musicUrl.includes('?') ? musicUrl.split('?')[0] : musicUrl;
};

// ==================== 4. 全平台搜索模块 ====================
async function searchGeneral(platform, keyword, page = 1, limit = 30) {
  const text = encodeURIComponent(keyword || '');

  if (platform === 'qs' || platform === 'sd') {
    const searchApis = [
      async () => {
        const res = await httpRequest(`https://api.qs.vip/music/?act=search&keywords=${text}&page=${page}&pagesize=${limit}&type=music`, { timeout: 4000 });
        if (res.body?.code === 200 && res.body?.data?.list?.length > 0) return res.body.data.list;
        throw new Error('qs.vip empty');
      },
      async () => {
        const res = await httpRequest(`https://api.injahow.cn/meting/?type=search&id=${text}&server=qishui`, { timeout: 4000 });
        if (Array.isArray(res.body) && res.body.length > 0) return res.body;
        throw new Error('injahow empty');
      }
    ];
    try {
      const list = await raceApis(searchApis);
      return {
        isEnd: list.length < limit,
        list: list.map(item => ({
          id: String(item.id || item.songmid || ''), songmid: String(item.id || item.songmid || ''), hash: String(item.id || ''),
          name: item.name || '', singer: item.singer || '', albumName: item.albumName || '', duration: item.duration || 0, pic: item.pic || ''
        }))
      };
    } catch (e) { return { isEnd: true, list: [] }; }
  }

  const serverMap = { wy: 'netease', tx: 'tencent', kw: 'kuwo', kg: 'kugou', mg: 'migu' };
  const server = serverMap[platform] || 'netease';
  try {
    const res = await httpRequest(`https://api.i-meto.com/meting/api.php?type=search&id=${text}&server=${server}`, { timeout: 4000 });
    if (Array.isArray(res.body) && res.body.length > 0) {
      return {
        isEnd: res.body.length < limit,
        list: res.body.map(item => ({
          id: item.id || item.songmid || '', songmid: item.id || item.songmid || '', hash: item.hash || item.id || '',
          name: item.name || item.title || '', singer: item.artist || '', albumName: item.album || '', duration: item.duration || 0, pic: item.pic || ''
        }))
      };
    }
  } catch (e) {}
  return { isEnd: true, list: [] };
}

// ==================== 5. 平台总路由 ====================

async function fetchMusicUrl(platform, info, targetQuality) {
  const cacheKey = `${platform}_${info.songmid || info.hash || info.id}_${targetQuality}`;
  const cached = getCache(cacheKey);
  if (cached) return cached;

  const supportList = MUSIC_QUALITIES[platform] || ['128k'];
  const startIndex = QUALITY_ORDER.indexOf(targetQuality);
  const candidates = startIndex !== -1 ? QUALITY_ORDER.slice(startIndex).filter(q => supportList.includes(q)) : [targetQuality];

  for (const q of candidates) {
    try {
      let url = null;
      
      // 1. 走小熙的专属咪咕逻辑
      if (platform === 'mg') {
        url = await getMgUrl(info, q);
      } 
      // 2. 走小熙的专属酷我逻辑
      else if (platform === 'kw') {
        url = await getKwUrl(info, q);
      } 
      // 3. 优先走 YNX 代理 (解决 QQ 50秒)
      else if (platform === 'tx' || platform === 'wy' || platform === 'kg') {
        try {
          const res = await httpRequest(YNX_API, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'User-Agent': 'lx-music-request/YNX' },
            body: JSON.stringify({ source: platform, musicId: info.songmid || info.hash || info.id, quality: q }),
            timeout: 6000
          });
          if (res.body?.code === 200 && res.body?.url) url = res.body.url;
          else if (res.body?.code === 403) throw new Error('YNX接口关闭');
        } catch(e) {
          // YNX 失败则进入下方的并发兜底
        }
      }

      // 4. 如果 YNX 没拿到，走并发兜底池
      if (!url) {
        const apis = [];
        if (platform === 'tx') {
          apis.push(
            async () => {
              const vkeysQc = { '128k': '6', '192k': '7', '320k': '8', 'flac': '10', 'flac24bit': '11', 'hires': '11', 'atmos': '13', 'master': '14' };
              const res = await httpRequest(`https://api.vkeys.cn/v2/music/tencent/geturl?mid=${info.songmid}&quality=${vkeysQc[q] || '8'}`);
              if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
              throw new Error('Vkeys失败');
            },
            async () => {
              const res = await httpRequest(`https://tang.api.s01s.cn/music_open_api.php?mid=${info.songmid}`);
              if (res.body) {
                const fields = ['song_play_url_pq', 'song_play_url_sq', 'song_play_url_hq', 'song_play_url_standard', 'song_play_url'];
                for (const f of fields) if (res.body[f]?.startsWith('http')) return res.body[f];
              }
              throw new Error('Tang失败');
            },
            async () => {
              const res = await httpRequest(`http://103.79.184.97/api/music/url?source=tx&songId=${info.songmid}&quality=${q}&key=6C1F-53W0-GRKI-EVFG`, { headers: { 'X-Card-Key': '6C1F-53W0-GRKI-EVFG' } });
              const u = res.body?.url || res.body?.data?.url || res.body?.data;
              if (typeof u === 'string' && u.startsWith('http')) return u;
              throw new Error('103.79失败');
            }
          );
        } else if (platform === 'wy') {
          apis.push(
            async () => {
              const lvlMap = { '128k': 'standard', '320k': 'exhigh', 'flac': 'lossless', 'flac24bit': 'hires', 'hires': 'hires' };
              const res = await httpRequest(`https://mcp.nianxinxz.com/share/ceshi/wy.php?id=${info.songmid || info.id}&level=${lvlMap[q] || 'exhigh'}`);
              if (res.body?.url) return await probeRealUrl(res.body.url);
              throw new Error('念心失败');
            },
            async () => {
              const res = await httpRequest('https://c.wwwweb.top/music/url', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: 'wy', musicId: info.songmid || info.id, quality: q })
              });
              if (res.body?.code === 200 && res.body?.url) return res.body.url;
              throw new Error('wwwweb失败');
            }
          );
        } else if (platform === 'kg') {
          apis.push(
            async () => {
              const hash = getKgHash(info);
              const keyword = encodeURIComponent(`${info.name} ${info.singer}`.trim());
              if (!keyword) throw new Error('无关键词');
              const res = await httpRequest(`https://a.aa.cab/qq.music?msg=${keyword}&n=1&type=${q}`);
              if (res.body?.data?.music) return res.body.data.music;
              if (res.body?.url) return res.body.url;
              throw new Error('关键字失败');
            },
            async () => {
              const hash = getKgHash(info);
              if (!hash) throw new Error('无Hash');
              const res = await httpRequest('https://api.music.lerd.dpdns.org/kg', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: q === 'flac' ? 'flac' : q === '320k' ? '320k' : '128k', musicInfo: { source: 'kg', hash } })
              });
              if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
              throw new Error('安妮失败');
            }
          );
        } else if (platform === 'qs' || platform === 'sd') {
          apis.push(
            async () => {
              if (!info.id) throw new Error('无ID');
              const res = await httpRequest(`https://api.qishui.com/luna/h5/seo_track?track_id=${info.id}`);
              const variants = res.body?.data?.play_variants || [];
              if (variants.length > 0 && variants[0].url) return variants[0].url;
              throw new Error('官方 H5 失败');
            },
            async () => {
              if (!info.id) throw new Error('无ID');
              const res = await httpRequest(`https://api.qs.vip/music/?act=url&id=${info.id}&quality=${q}`);
              if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
              throw new Error('qs.vip 失败');
            }
          );
        }

        // 如果 YNX 没出，用并发兜底
        if (apis.length > 0) {
          url = await raceApis(apis);
        }
      }

      if (url && typeof url === 'string' && url.startsWith('http')) {
        setCache(cacheKey, url); // 保存缓存
        return url;
      }
    } catch (e) {
      // 当前音质失败，静默降级尝试下一个音质
    }
  }
  throw new Error(`全平台解析失败`);
}

// ==================== 6. 事件监听与注册 ====================
on(EVENT_NAMES.request, async ({ action, source, info }) => {
  if (!source) throw new Error('未知音源');

  if (action === 'musicUrl') {
    if (!info?.musicInfo || !info?.type) throw new Error('参数不完整');
    return await fetchMusicUrl(source, info.musicInfo, info.type);
  }

  if (action === 'search') {
    return await searchGeneral(source, info?.text || '', info?.page || 1, info?.limit || 30);
  }

  if (action === 'lyric') return { lyric: '', tlyric: '' };
  if (action === 'pic') return null;

  throw new Error(`不支持的操作: ${action}`);
});

const sources = {};
Object.keys(MUSIC_QUALITIES).forEach(p => {
  const names = {
    wy: '网易云音乐', tx: 'QQ音乐', kw: '酷我音乐',
    kg: '酷狗音乐', mg: '咪咕音乐', qs: '汽水音乐', sd: '汽水音乐'
  };
  sources[p] = {
    name: names[p],
    type: 'music',
    actions: ['musicUrl', 'search', 'lyric', 'pic'],
    qualitys: MUSIC_QUALITIES[p]
  };
});

send(EVENT_NAMES.inited, {
  status: true,
  openDevTools: false,
  sources
});
