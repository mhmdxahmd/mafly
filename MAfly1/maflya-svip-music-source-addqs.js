/*! 
 * @name 👽maflya音源(三改整合版) - 落雪 + sollin 最终兼容版
 * @description 基于安妮独家音源v4 + 星海音乐源v3.2.12 + 汽水音乐重构
 * @version v3.0.2106 | 2026-11-26
 * @author 👽maflya | 裤佬 | 安妮 | 星海
 */

const { EVENT_NAMES, request, on, send } = globalThis.lx;

// ==================== 1. 完整音质与常量声明 ====================
const TIMEOUT = 8000;

const MUSIC_QUALITIES = {
  wy: ['128k', '192k', '320k', 'flac', 'flac24bit', 'hires', 'jyeffect', 'sky', 'jymaster'],
  tx: ['128k', '192k', '320k', 'flac', 'flac24bit', 'hires', 'atmos', 'master'],
  kw: ['128k', '320k', 'flac', 'flac24bit', 'hires', 'atmos', 'atmos_plus', 'master'],
  kg: ['128k', '320k', 'flac', 'flac24bit', 'hires', 'atmos', 'master'],
  mg: ['128k', '320k', 'flac', 'flac24bit', 'hires'],
  qs: ['128k', '320k', 'flac', 'flac24bit'],
  sd: ['128k', '320k', 'flac', 'flac24bit']
};

const QUALITY_ORDER = ['jymaster', 'master', 'atmos_plus', 'atmos', 'sky', 'jyeffect', 'hires', 'flac24bit', 'flac', '320k', '192k', '128k'];

// ==================== 2. 统一请求工具函数 ====================
const httpRequest = (url, options = {}) => new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error('请求超时')), options.timeout || TIMEOUT);
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
    resolve({ body, statusCode: resp.statusCode || 200, headers: resp.headers || {}, url: resp.url });
  });
});

// 并发竞速：只要有一个接口成功，立刻返回
const raceApis = async (apis) => {
  if (!apis || apis.length === 0) throw new Error('无可用接口');
  return await Promise.any(apis.map(fn => fn()));
};

// 酷狗 Hash 深度提取 (源自 Hei Music)
const getKgHash = (info) => {
  if (info._types) {
    if (info._types['flac']?.hash) return info._types['flac'].hash;
    if (info._types['320k']?.hash) return info._types['320k'].hash;
    if (info._types['128k']?.hash) return info._types['128k'].hash;
  }
  return info.SQFileHash || info.HQFileHash || info.FileHash || info.hash || info.songmid || '';
};

// 星海动态 Token 生成 (源自 HelloWorld)
const generateToken = () => {
  const payload = { device_id: 'lx-online', ip: '0.0.0.0', timestamp: Math.floor(Date.now() / 1000), random: Math.random().toString(36).substring(2) };
  return btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
};

// ==================== 3. 全平台搜索模块 ====================
async function searchGeneral(platform, keyword, page = 1, limit = 30) {
  // --- 汽水专属搜索（全网多渠道） ---
  if (platform === 'qs' || platform === 'sd') {
    const text = encodeURIComponent(keyword || '');
    const searchApis = [
      // 渠道 A：开源 API 库 (injahow)
      async () => {
        const res = await httpRequest(`https://api.injahow.cn/meting/?type=search&id=${text}&server=qishui`, { timeout: 4000 });
        if (Array.isArray(res.body) && res.body.length > 0) return res.body;
        throw new Error('injahow empty');
      },
      // 渠道 B：民间代理 (qs.vip)
      async () => {
        const res = await httpRequest(`https://api.qs.vip/music/?act=search&keywords=${text}&page=${page}&pagesize=${limit}&type=music`, { timeout: 4000 });
        if (res.body?.code === 200 && res.body?.data?.list?.length > 0) return res.body.data.list;
        throw new Error('qs.vip empty');
      },
      // 渠道 C：民间代理 (qs.la)
      async () => {
        const res = await httpRequest(`https://api.qs.la/music/?act=search&keywords=${text}&page=${page}&pagesize=${limit}&type=music`, { timeout: 4000 });
        if (res.body?.code === 200 && res.body?.data?.list?.length > 0) return res.body.data.list;
        throw new Error('qs.la empty');
      },
      // 渠道 D：官方 PC 端未加密接口
      async () => {
        const res = await httpRequest(`https://api.qishui.com/luna/pc/search/track?keyword=${text}&limit=${limit}`, { timeout: 4000 });
        if (res.body?.data?.tracks?.length > 0) return res.body.data.tracks;
        throw new Error('qishui pc empty');
      }
    ];

    try {
      const list = await raceApis(searchApis);
      return {
        isEnd: list.length < limit,
        list: list.map(item => ({
          id: String(item.id || item.songmid || item.track_id || ''),
          songmid: String(item.id || item.songmid || item.track_id || ''),
          hash: String(item.id || item.songmid || item.track_id || ''),
          name: item.name || item.title || '',
          singer: item.singer || item.artist || '',
          albumName: item.albumName || item.album || '',
          duration: item.duration || 0,
          pic: item.pic || item.cover || ''
        }))
      };
    } catch (e) {
      return { isEnd: true, list: [] };
    }
  }

  // --- 其他平台通用搜索 (Meting API) ---
  const serverMap = { wy: 'netease', tx: 'tencent', kw: 'kuwo', kg: 'kugou', mg: 'migu' };
  const server = serverMap[platform] || 'netease';
  const urls = [
    `https://api.i-meto.com/meting/api.php?type=search&id=${encodeURIComponent(keyword)}&server=${server}`,
    `https://api.injahow.cn/meting/?type=search&id=${encodeURIComponent(keyword)}&server=${server}`
  ];
  
  for (const url of urls) {
    try {
      const res = await httpRequest(url, { timeout: 4000 });
      if (Array.isArray(res.body) && res.body.length > 0) {
        return {
          isEnd: res.body.length < limit,
          list: res.body.map(item => ({
            id: item.id || item.songmid || item.url_id || '', 
            songmid: item.id || item.songmid || item.url_id || '', 
            hash: item.hash || item.id || '',
            name: item.name || item.title || '', 
            singer: item.artist || item.singer || '',
            albumName: item.album || '', 
            duration: item.duration || 0, 
            pic: item.pic || ''
          }))
        };
      }
    } catch (e) {}
  }
  return { isEnd: true, list: [] };
}

// ==================== 4. 各大平台解析模块 ====================

// 1. 网易云音乐 (全并发)
const resolveWy = async (info, quality) => {
  const id = info.songId || info.id || info.songmid;
  if (!id) throw new Error('缺少网易ID');
  return await raceApis([
    // 念心 MCP
    async () => {
      const lvlMap = { '128k': 'standard', '320k': 'exhigh', 'flac': 'lossless', 'flac24bit': 'hires', 'hires': 'hires', 'jyeffect': 'jyeffect', 'sky': 'sky', 'jymaster': 'jymaster' };
      const res = await httpRequest(`https://mcp.nianxinxz.com/share/ceshi/wy.php?id=${id}&level=${lvlMap[quality] || 'exhigh'}`);
      if (res.body?.url) return res.body.url;
      throw new Error('念心失败');
    },
    // wwwweb
    async () => {
      const res = await httpRequest('https://c.wwwweb.top/music/url', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'wy', musicId: id, quality: quality })
      });
      if (res.body?.code === 200 && res.body?.url) return res.body.url;
      throw new Error('wwwweb失败');
    },
    // 海棠
    async () => {
      const res = await httpRequest('https://musicserver.haitangw.cc/v1/music/resolve-url', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'wy', rid: id, level: quality === 'flac' ? 'lossless' : 'exhigh' })
      });
      if (res.body?.data?.url) return res.body.data.url;
      throw new Error('海棠失败');
    },
    // 星海
    async () => {
      const res = await httpRequest(`https://yy.zddyr.top/lx/api/?source=wy&songmid=${id}&quality=${quality}`, {
        headers: { 'X-Token': generateToken(), 'X-Client': 'YYMusicSource/v1.0.0' }
      });
      if (res.body?.url) return res.body.url;
      throw new Error('星海失败');
    }
  ]);
};

// 2. QQ音乐 (全并发)
const resolveTx = async (info, quality) => {
  const id = info.songmid || info.id;
  if (!id) throw new Error('缺少QQ mid');
  return await raceApis([
    // Tang (强力无鉴权)
    async () => {
      const res = await httpRequest(`https://tang.api.s01s.cn/music_open_api.php?mid=${id}`);
      if (res.body) {
        const fields = ['song_play_url_pq', 'song_play_url_sq', 'song_play_url_hq', 'song_play_url_standard', 'song_play_url'];
        for (const f of fields) {
          if (res.body[f] && typeof res.body[f] === 'string' && res.body[f].startsWith('http')) return res.body[f];
        }
      }
      throw new Error('Tang失败');
    },
    // 103.79
    async () => {
      const res = await httpRequest(`http://103.79.184.97/api/music/url?source=tx&songId=${id}&quality=${quality}&key=6C1F-53W0-GRKI-EVFG`, {
        headers: { 'User-Agent': 'Mozilla/5.0', 'X-Card-Key': '6C1F-53W0-GRKI-EVFG' }
      });
      const url = res.body?.url || res.body?.data?.url || res.body?.data;
      if (typeof url === 'string' && url.startsWith('http')) return url;
      throw new Error('103.79失败');
    },
    // Vkeys
    async () => {
      const res = await httpRequest(`https://api.vkeys.cn/v2/music/tencent/geturl?mid=${id}&quality=8`);
      if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
      throw new Error('Vkeys失败');
    },
    // 星海
    async () => {
      const res = await httpRequest(`https://yy.zddyr.top/lx/api/?source=tx&songmid=${id}&quality=${quality}`, {
        headers: { 'X-Token': generateToken(), 'X-Client': 'YYMusicSource/v1.0.0' }
      });
      if (res.body?.url) return res.body.url;
      throw new Error('星海失败');
    }
  ]);
};

// 3. 酷我音乐 (全并发)
const resolveKw = async (info, quality) => {
  const id = info.rid || info.hash || info.songmid || info.id;
  if (!id) throw new Error('缺少酷我ID');
  return await raceApis([
    // 官方 Mobi
    async () => {
      const brMap = { '128k': '128kmp3', '320k': '320kmp3', 'flac': '2000kflac', 'flac24bit': '4000kflac' };
      const res = await httpRequest(`http://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayerhd_ar_6.6.6.6_tianbao_T1A_qirui.apk&type=convert_url_with_sign&rid=${id}&br=${brMap[quality] || '320kmp3'}`, {
        headers: { 'User-Agent': 'Mozilla/5.0 (Linux; Android) AppleWebKit/537.36' }
      });
      if (res.body?.data?.url) return res.body.data.url;
      throw new Error('mobi失败');
    },
    // 海棠
    async () => {
      const res = await httpRequest('https://musicserver.haitangw.cc/v1/music/resolve-url', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'kw', rid: id, level: quality === 'flac' ? 'lossless' : 'exhigh' })
      });
      if (res.body?.data?.url) return res.body.data.url;
      throw new Error('海棠失败');
    }
  ]);
};

// 4. 酷狗音乐 (全并发)
const resolveKg = async (info, quality) => {
  const hash = getKgHash(info);
  const keyword = encodeURIComponent(`${info.name} ${info.singer}`.trim());
  return await raceApis([
    // 关键字搜
    async () => {
      if (!keyword) throw new Error('无关键词');
      const res = await httpRequest(`https://a.aa.cab/qq.music?msg=${keyword}&n=1&type=${quality}`);
      if (res.body?.data?.music) return res.body.data.music;
      if (res.body?.url) return res.body.url;
      throw new Error('关键字失败');
    },
    // 安妮
    async () => {
      if (!hash) throw new Error('无Hash');
      const res = await httpRequest('https://api.music.lerd.dpdns.org/kg', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: quality === 'flac' ? 'flac' : quality === '320k' ? '320k' : '128k', musicInfo: { source: 'kg', hash } })
      });
      if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
      throw new Error('安妮失败');
    },
    // 103.79
    async () => {
      if (!hash) throw new Error('无Hash');
      const res = await httpRequest(`http://103.79.184.97/api/music/url?source=kg&songId=${hash}&quality=${quality}&key=6C1F-53W0-GRKI-EVFG`, {
        headers: { 'X-Card-Key': '6C1F-53W0-GRKI-EVFG' }
      });
      const url = res.body?.url || res.body?.data?.url || res.body?.data;
      if (typeof url === 'string' && url.startsWith('http')) return url;
      throw new Error('103.79失败');
    },
    // 星海
    async () => {
      if (!hash) throw new Error('无Hash');
      const res = await httpRequest(`https://yy.zddyr.top/lx/api/?source=kg&quality=${quality}&mainHash=${hash}`, {
        headers: { 'X-Token': generateToken(), 'X-Client': 'YYMusicSource/v1.0.0' }
      });
      if (res.body?.url) return res.body.url;
      throw new Error('星海失败');
    }
  ]);
};

// 5. 咪咕音乐 (全并发)
const resolveMg = async (info, quality) => {
  const keyword = encodeURIComponent(`${info.name} ${info.singer}`.trim());
  if (!keyword) throw new Error('缺少歌曲名');
  return await raceApis([
    async () => {
      const res = await httpRequest(`https://oiapi.net/api/MiGu_Music?msg=${keyword}&br=${quality === 'flac' ? 'SQ' : 'HQ'}&n=1`);
      if (res.body?.data?.url || res.body?.url) return res.body.data?.url || res.body.url;
      throw new Error('oiapi失败');
    },
    async () => {
      const res = await httpRequest(`https://yy.zddyr.top/lx/api/?source=migu&songmid=${info.songmid || info.id || ''}&quality=${quality}`, {
        headers: { 'X-Token': generateToken(), 'X-Client': 'YYMusicSource/v1.0.0' }
      });
      if (res.body?.url) return res.body.url;
      throw new Error('星海失败');
    }
  ]);
};

// 6. 汽水音乐 (终极全并发：官方+代理+开源)
const resolveQs = async (info, quality) => {
  const id = info.songmid || info.id;
  const keyword = encodeURIComponent(`${info.name} ${info.singer}`.trim());
  return await raceApis([
    // 渠道 A：官方 H5 接口 (获取试听/免费片段)
    async () => {
      if (!id) throw new Error('无ID');
      const res = await httpRequest(`https://api.qishui.com/luna/h5/seo_track?track_id=${id}`);
      const variants = res.body?.data?.play_variants || [];
      if (variants.length > 0) {
        const best = variants.find(v => v.quality === 'high') || variants[0];
        if (best.url) return best.url;
      }
      throw new Error('官方 H5 失败');
    },
    // 渠道 B：代理 (qs.vip) 直接取流
    async () => {
      if (!id) throw new Error('无ID');
      const res = await httpRequest(`https://api.qs.vip/music/?act=url&id=${id}&quality=${quality}`);
      if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
      throw new Error('qs.vip 失败');
    },
    // 渠道 C：代理 (qs.la) 直接取流
    async () => {
      if (!id) throw new Error('无ID');
      const res = await httpRequest(`https://api.qs.la/music/?act=url&id=${id}&quality=${quality}`);
      if (res.body?.code === 200 && res.body?.data?.url) return res.body.data.url;
      throw new Error('qs.la 失败');
    },
    // 渠道 D：开源 API 搜索兜底 (injahow)
    async () => {
      if (!keyword) throw new Error('无关键词');
      const res = await httpRequest(`https://api.injahow.cn/meting/?type=search&id=${keyword}&server=qishui`);
      if (res.body?.url) return res.body.url;
      throw new Error('injahow 失败');
    }
  ]);
};

const resolvers = { wy: resolveWy, tx: resolveTx, kw: resolveKw, kg: resolveKg, mg: resolveMg, qs: resolveQs, sd: resolveQs };

// ==================== 5. 音质降级与路由 ====================
async function fetchMusicUrl(platform, info, targetQuality) {
  const resolver = resolvers[platform];
  if (!resolver) throw new Error(`不支持平台: ${platform}`);

  const supportList = MUSIC_QUALITIES[platform] || ['128k'];
  const startIndex = QUALITY_ORDER.indexOf(targetQuality);
  const candidates = startIndex !== -1 ? QUALITY_ORDER.slice(startIndex).filter(q => supportList.includes(q)) : [targetQuality];

  const errors = [];
  for (const q of candidates) {
    try {
      const url = await resolver(info, q);
      if (url && typeof url === 'string' && url.startsWith('http')) {
        return url; // 成功即返回
      }
    } catch (e) {
      errors.push(`${q}: ${e.message || e}`);
    }
  }
  throw new Error(`全平台解析失败 (${errors.join(' | ')})`);
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

// ==================== 7. 导出声明 ====================
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
