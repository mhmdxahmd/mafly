/*! 
 * @name 👽maflya音源(三改整合版) - 落雪 + sollin 最终兼容版
 * @description 基于安妮独家音源v4 + 星海音乐源v3.2.12 + 汽水音乐重构
 * @version v3.0.2139| 2026-11-26
 * @author 👽maflya | 裤佬 | 安妮 | 星海
 */

const { EVENT_NAMES, request, on, send, env } = globalThis.lx;

// ==================== 1. 核心配置与常量 ====================
const CACHE_TTL = 1000 * 60 * 20; // 缓存20分钟
const TIMEOUT = 5000; // 全局 5 秒超时，拒绝慢接口
const YNX_API = 'http://ynx.de5.net/API/music.php'; // 小熙同款代理

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

// ==================== 2. 工具函数 ====================
const URL_CACHE = new Map();
const getCache = (key) => {
  const item = URL_CACHE.get(key);
  if (!item) return null;
  if (Date.now() > item.expire) { URL_CACHE.delete(key); return null; }
  return item.data;
};
const setCache = (key, data) => URL_CACHE.set(key, { data, expire: Date.now() + CACHE_TTL });

const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
function getRandomMix(len = 6) {
  let str = '';
  for(let i = 0; i < len; i++) str += chars[Math.floor(Math.random() * chars.length)];
  return str;
}
function randomBytes(size = 4) {
  if (size <= 0) return 0;
  const max = Math.min(Math.pow(256, size) - 1, Number.MAX_SAFE_INTEGER);
  return Math.floor(Math.random() * max);
}

const httpRequest = (url, options = {}) => new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error(`超时`)), options.timeout || TIMEOUT);
  request(url, {
    method: options.method || 'GET',
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
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
    
    // 处理 302 重定向提取真实链接
    const headers = resp.headers || {};
    const location = headers.location || headers.Location;
    if (location && location.startsWith('http')) {
       return resolve({ body: '', statusCode: 302, headers, url: location });
    }

    resolve({ body, statusCode: resp.statusCode || 200, headers, url: resp.url });
  });
});

const raceApis = async (apis) => {
  if (!apis || apis.length === 0) throw new Error('无可用接口');
  return await Promise.any(apis.map(fn => fn()));
};

const generateToken = () => {
  const payload = { device_id: 'lx-online', ip: '0.0.0.0', timestamp: Math.floor(Date.now() / 1000), random: Math.random().toString(36).substring(2) };
  return btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
};

const getKgHash = (info) => {
  if (info._types) {
    if (info._types['flac']?.hash) return info._types['flac'].hash;
    if (info._types['320k']?.hash) return info._types['320k'].hash;
    if (info._types['128k']?.hash) return info._types['128k'].hash;
  }
  return info.SQFileHash || info.HQFileHash || info.FileHash || info.hash || info.songmid || info.id || '';
};

// ==================== 3. 跨平台借流（专治 QQ 音乐 1 分钟） ====================
const searchCrossPlatform = async (name, singer) => {
  if (!name) return null;
  const keyword = encodeURIComponent(`${name} ${singer || ''}`.trim());
  try {
    // 去网易借完整 320k
    const wyRes = await httpRequest(`https://api.injahow.cn/meting/?type=search&id=${keyword}&server=netease`, { timeout: 4000 });
    if (Array.isArray(wyRes.body) && wyRes.body.length > 0) {
      const wyUrlRes = await httpRequest(`https://mcp.nianxinxz.com/share/ceshi/wy.php?id=${wyRes.body[0].id}&level=exhigh`);
      if (wyUrlRes.body?.url) return wyUrlRes.body.url;
    }
    // 去酷狗借
    const kgRes = await httpRequest(`https://api.injahow.cn/meting/?type=search&id=${keyword}&server=tencent`, { timeout: 4000 });
    if (Array.isArray(kgRes.body) && kgRes.body.length > 0) {
      const kgUrlRes = await httpRequest(`https://api.music.lerd.dpdns.org/kg`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: '320k', musicInfo: { source: 'kg', hash: kgRes.body[0].hash || kgRes.body[0].id } })
      });
      if (kgUrlRes.body?.data?.url) return kgUrlRes.body.data.url;
    }
  } catch (e) {}
  return null;
};

// ==================== 4. 各平台专属解析（全量接口） ====================

// 【QQ 音乐】包含 5 路并发 + 跨平台借流
const resolveTx = async (info, q) => {
  const mid = info.songmid || info.id;
  if (!mid) throw new Error('缺少QQ mid');
  
  const apis = [
    async () => {
      const vkeysQc = { '128k': '6', '192k': '7', '320k': '8', 'flac': '10', 'flac24bit': '11', 'hires': '11', 'atmos': '13', 'master': '14' };
      const res = await httpRequest(`https://api.vkeys.cn/v2/music/tencent/geturl?mid=${mid}&quality=${vkeysQc[q] || '8'}`, { timeout: 4000 });
      if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
      throw new Error('Vkeys失败');
    },
    async () => {
      const res = await httpRequest(YNX_API, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'tx', musicId: mid, quality: q }), timeout: 4000
      });
      if (res.body?.code === 200 && res.body?.url) return res.body.url;
      throw new Error('YNX失败');
    },
    async () => {
      const res = await httpRequest(`https://tang.api.s01s.cn/music_open_api.php?mid=${mid}`, { timeout: 4000 });
      if (res.body) {
        const fields = ['song_play_url_pq', 'song_play_url_sq', 'song_play_url_hq', 'song_play_url_standard', 'song_play_url'];
        for (const f of fields) if (res.body[f]?.startsWith('http')) return res.body[f];
      }
      throw new Error('Tang失败');
    },
    async () => {
      const res = await httpRequest(`http://103.79.184.97/api/music/url?source=tx&songId=${mid}&quality=${q}&key=6C1F-53W0-GRKI-EVFG`, {
        headers: { 'X-Card-Key': '6C1F-53W0-GRKI-EVFG' }, timeout: 4000
      });
      const u = res.body?.url || res.body?.data?.url || res.body?.data;
      if (typeof u === 'string' && u.startsWith('http')) return u;
      throw new Error('103.79失败');
    },
    async () => {
      const crossUrl = await searchCrossPlatform(info.name, info.singer);
      if (crossUrl) return crossUrl;
      throw new Error('借流失败');
    }
  ];
  return await raceApis(apis);
};

// 【网易云】4 路并发
const resolveWy = async (info, q) => {
  const id = info.songId || info.id || info.songmid;
  if (!id) throw new Error('缺少网易ID');
  const lvlMap = { '128k': 'standard', '320k': 'exhigh', 'flac': 'lossless', 'flac24bit': 'hires', 'hires': 'hires' };
  const apis = [
    async () => {
      const res = await httpRequest(`https://mcp.nianxinxz.com/share/ceshi/wy.php?id=${id}&level=${lvlMap[q] || 'exhigh'}`, { timeout: 4000 });
      if (res.body?.url) return res.body.url;
      throw new Error('念心失败');
    },
    async () => {
      const res = await httpRequest('https://c.wwwweb.top/music/url', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'wy', musicId: id, quality: q }), timeout: 4000
      });
      if (res.body?.code === 200 && res.body?.url) return res.body.url;
      throw new Error('wwwweb失败');
    },
    async () => {
      const res = await httpRequest('https://musicserver.haitangw.cc/v1/music/resolve-url', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'wy', rid: id, level: q === 'flac' ? 'lossless' : 'exhigh' }), timeout: 4000
      });
      if (res.body?.data?.url) return res.body.data.url;
      throw new Error('海棠失败');
    },
    async () => {
      const res = await httpRequest(`https://yy.zddyr.top/lx/api/?source=wy&songmid=${id}&quality=${q}`, {
        headers: { 'X-Token': generateToken(), 'X-Client': 'YYMusicSource/v1.0.0' }, timeout: 4000
      });
      if (res.body?.url) return res.body.url;
      throw new Error('星海失败');
    }
  ];
  return await raceApis(apis);
};

// 【酷我】包含小熙的 Mobi 签名和流媒体
const resolveKw = async (info, q) => {
  const rid = info.songmid || info.id || info.rid;
  if (!rid) throw new Error('缺少酷我ID');
  if (['atmos','atmos_plus','master'].includes(q)) {
     return `http://175.27.166.236:8928/kwstream?id=${encodeURIComponent(rid)}&level=${q}&stream=1`;
  }
  const qualityMap = { '128k': '128kmp3', '320k': '320kmp3', 'flac': '2000kflac', 'flac24bit': '4000kflac', 'hires': '4000kflac' };
  const apis = [
    async () => {
      const reqUrl = `https://changenotice.kuwo.cn/mobi.s?f=web&user=${Math.floor(Math.random()*10000)}&loginUid=0&source=kwplayercar_ar_6.0.0.9_B_jiakong_vh.apk&type=convert_url_with_sign&rid=${rid}&br=${qualityMap[q] || '320kmp3'}&format=mp3&mode=prefetch&from=PC&surl=1&apiv=1`;
      const res = await httpRequest(reqUrl, { timeout: 4000 });
      if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url.split('?')[0];
      if (res.body?.data?.surl) return res.body.data.surl.split('?')[0];
      throw new Error('Mobi失败');
    },
    async () => {
      const res = await httpRequest('https://musicserver.haitangw.cc/v1/music/resolve-url', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'kw', rid: rid, level: q === 'flac' ? 'lossless' : 'exhigh' }), timeout: 4000
      });
      if (res.body?.data?.url) return res.body.data.url;
      throw new Error('海棠失败');
    }
  ];
  return await raceApis(apis);
};

// 【酷狗】4 路并发
const resolveKg = async (info, q) => {
  const hash = getKgHash(info);
  const keyword = encodeURIComponent(`${info.name} ${info.singer}`.trim());
  const apis = [
    async () => {
      const res = await httpRequest(`https://a.aa.cab/qq.music?msg=${keyword}&n=1&type=${q}`, { timeout: 4000 });
      if (res.body?.data?.music) return res.body.data.music;
      if (res.body?.url) return res.body.url;
      throw new Error('关键字失败');
    },
    async () => {
      if (!hash) throw new Error('无Hash');
      const res = await httpRequest('https://api.music.lerd.dpdns.org/kg', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: q === 'flac' ? 'flac' : q === '320k' ? '320k' : '128k', musicInfo: { source: 'kg', hash } }), timeout: 4000
      });
      if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
      throw new Error('安妮失败');
    },
    async () => {
      if (!hash) throw new Error('无Hash');
      const res = await httpRequest(`http://103.79.184.97/api/music/url?source=kg&songId=${hash}&quality=${q}&key=6C1F-53W0-GRKI-EVFG`, {
        headers: { 'X-Card-Key': '6C1F-53W0-GRKI-EVFG' }, timeout: 4000
      });
      const u = res.body?.url || res.body?.data?.url || res.body?.data;
      if (typeof u === 'string' && u.startsWith('http')) return u;
      throw new Error('103.79失败');
    },
    async () => {
      if (!hash) throw new Error('无Hash');
      const res = await httpRequest(`https://yy.zddyr.top/lx/api/?source=kg&quality=${q}&mainHash=${hash}`, {
        headers: { 'X-Token': generateToken(), 'X-Client': 'YYMusicSource/v1.0.0' }, timeout: 4000
      });
      if (res.body?.url) return res.body.url;
      throw new Error('星海失败');
    }
  ];
  return await raceApis(apis);
};

// 【咪咕】小熙的替换大法
const resolveMg = async (info, q) => {
  const songId = info.songmid || info.songId || info.id;
  if (!songId) throw new Error('缺少咪咕ID');
  const MG_QUALITY = {
    '128k': { replacePath: '标清高清/MP3_128_16_Stero', ext: '.mp3' },
    '320k': { replacePath: '标清高清/MP3_320_16_Stero', ext: '.mp3' },
    'flac': { replacePath: '歌曲下载/flac', ext: '.flac' },
    'flac24bit': { replacePath: '歌曲下载/flac_24bit', ext: '.flac' },
    'hires': { replacePath: '歌曲下载/flac_24bit', ext: '.flac' },
    'atmos': { replacePath: '歌曲下载/wav_3d', ext: '.wav' },
    'master': { replacePath: '歌曲下载/wav_32bit', ext: '.wav' }
  };
  const cfg = MG_QUALITY[q] || MG_QUALITY['128k'];
  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36', 
    'Referer': 'https://m.music.migu.cn/v4/', 
    'channel': '014000D', 
    'By': '3c0effb5be907dd7fc209a9001a18713', 
    'Cookie': `SESSION=LOVELOVEYX${getRandomMix(22)}`
  };
  const res = await httpRequest(`https://app.c.nf.migu.cn/MIGUM2.0/strategy/listen-url/v2.4?lowerQualityContentId=&netType=00&resourceType=2&songId=${songId}&toneFlag=PQ`, { headers, timeout: 4000 });
  if (res.body?.code === '000000' && res.body?.data?.url) {
    const baseUrl = decodeURIComponent(res.body.data.url).split('?')[0];
    const finalUrl = baseUrl.replace('标清高清/MP3_128_16_Stero', cfg.replacePath).replace(/(\.mp3|\.flac)$/i, cfg.ext);
    return encodeURI(finalUrl);
  }
  throw new Error('咪咕失败');
};

// 【汽水】
const resolveQs = async (info, q) => {
  const id = info.songmid || info.id;
  if (!id) throw new Error('缺少汽水ID');
  const apis = [
    async () => {
      const res = await httpRequest(`https://api.qishui.com/luna/h5/seo_track?track_id=${id}`, { timeout: 4000 });
      const variants = res.body?.data?.play_variants || [];
      if (variants.length > 0 && variants[0].url) return variants[0].url;
      throw new Error('官方 H5 失败');
    },
    async () => {
      const res = await httpRequest(`https://api.qs.vip/music/?act=url&id=${id}&quality=${q}`, { timeout: 4000 });
      if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
      throw new Error('qs.vip 失败');
    }
  ];
  return await raceApis(apis);
};

const resolvers = { wy: resolveWy, tx: resolveTx, kw: resolveKw, kg: resolveKg, mg: resolveMg, qs: resolveQs, sd: resolveQs };

// ==================== 5. 路由分发与并发降级 ====================
async function fetchMusicUrl(platform, info, targetQuality) {
  const cacheKey = `${platform}_${info.songmid || info.hash || info.id}_${targetQuality}`;
  const cached = getCache(cacheKey);
  if (cached) return cached;

  const resolver = resolvers[platform];
  if (!resolver) throw new Error(`不支持平台: ${platform}`);

  const supportList = MUSIC_QUALITIES[platform] || ['128k'];
  const startIndex = QUALITY_ORDER.indexOf(targetQuality);
  const candidates = startIndex !== -1 ? QUALITY_ORDER.slice(startIndex).filter(q => supportList.includes(q)) : [targetQuality];

  // 并发所有支持的音质进行尝试
  const tasks = candidates.map(q => async () => {
    const url = await resolver(info, q);
    if (url && typeof url === 'string' && url.startsWith('http')) return url;
    throw new Error('无效');
  });

  try {
    const url = await raceApis(tasks);
    setCache(cacheKey, url);
    return url; 
  } catch (e) {
    throw new Error(`全平台解析失败`);
  }
}

// ==================== 6. 全平台搜索 ====================
async function searchGeneral(platform, keyword, page = 1, limit = 30) {
  const text = encodeURIComponent(keyword || '');
  if (platform === 'qs' || platform === 'sd') {
    try {
      const res = await httpRequest(`https://api.qs.vip/music/?act=search&keywords=${text}&page=${page}&pagesize=${limit}&type=music`, { timeout: 4000 });
      if (res.body?.code === 200 && res.body?.data?.list?.length > 0) {
        const list = res.body.data.list;
        return { isEnd: list.length < limit, list: list.map(item => ({ id: String(item.id), songmid: String(item.id), hash: String(item.id), name: item.name || '', singer: item.singer || '', albumName: item.albumName || '', duration: item.duration || 0, pic: item.pic || '' })) };
      }
    } catch (e) { return { isEnd: true, list: [] }; }
  }

  const serverMap = { wy: 'netease', tx: 'tencent', kw: 'kuwo', kg: 'kugou', mg: 'migu' };
  const server = serverMap[platform] || 'netease';
  try {
    const res = await httpRequest(`https://api.i-meto.com/meting/api.php?type=search&id=${text}&server=${server}`, { timeout: 4000 });
    if (Array.isArray(res.body) && res.body.length > 0) {
      return { isEnd: res.body.length < limit, list: res.body.map(item => ({ id: item.id || item.songmid || '', songmid: item.id || item.songmid || '', hash: item.hash || item.id || '', name: item.name || '', singer: item.artist || '', albumName: item.album || '', duration: item.duration || 0, pic: item.pic || '' })) };
    }
  } catch (e) {}
  return { isEnd: true, list: [] };
}

// ==================== 7. 事件与启动 ====================
on(EVENT_NAMES.request, async ({ action, source, info }) => {
  if (!source) throw new Error('未知音源');
  if (action === 'musicUrl') return await fetchMusicUrl(source, info.musicInfo, info.type);
  if (action === 'search') return await searchGeneral(source, info?.text || '', info?.page || 1, info?.limit || 30);
  if (action === 'lyric') return { lyric: '', tlyric: '' };
  if (action === 'pic') return null;
  throw new Error(`不支持的操作: ${action}`);
});

const sources = {};
Object.keys(MUSIC_QUALITIES).forEach(p => {
  const names = { wy: '网易云音乐', tx: 'QQ音乐', kw: '酷我音乐', kg: '酷狗音乐', mg: '咪咕音乐', qs: '汽水音乐', sd: '汽水音乐' };
  sources[p] = { name: names[p], type: 'music', actions: ['musicUrl', 'search', 'lyric', 'pic'], qualitys: MUSIC_QUALITIES[p] };
});

send(EVENT_NAMES.inited, { status: true, openDevTools: false, sources });
