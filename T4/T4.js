// ==================== M3U 转 T4 JSON - 影视仓/MiraPlay 专属终结版 ====================
const M3U_URL = "https://p4.maflya.com/iptv.m3u";

// 📣 全局滚动广告/跑马灯（在此修改你的广告文本）
const AD_TEXT = "🔥 欢迎使用！永久官网：https://maflya.com 。关注TG频道：@flymaf 获取最新动态！";

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  const path = url.pathname.toLowerCase().replace(/\/$/, '');
  const params = url.searchParams;

  if (['', '/', '/iptv', '/live'].includes(path)) {
    try {
      // 1. 抓取并解析 M3U（严格对齐台标和分组规则）
      const m3uText = await fetchM3U();
      const { class: groups, allChannels } = parseM3UToGroups(m3uText);

      const typeId = params.get('t');   // 分类ID
      const ids = params.get('ids');    // 播放/详情ID

      // 【1. 播放/详情路由】
      if (ids) {
        if (ids === 'AD_NOTICE_ID') {
          return jsonResponse({
            list: [{
              vod_id: 'AD_NOTICE_ID',
              vod_name: "系统公告",
              vod_play_from: "direct",
              vod_play_url: `提示$http://0.0.0.0`
            }]
          });
        }
        const targetUrl = b64Decode(ids);
        return jsonResponse({
          list: [{
            vod_id: ids,
            vod_name: "直播流",
            vod_play_from: "direct",
            vod_play_url: `播放$${targetUrl}`
          }]
        });
      }

      // 【2. 分类数据路由】当点击具体的某个分类时
      if (typeId) {
        const decodedType = decodeURIComponent(typeId).trim();
        const filteredChannels = allChannels.filter(ch => ch.type_id.trim() === decodedType);
        
        // 物理去重 Map
        const uniqueVodMap = new Map();
        
        // 📢 强行在当前分类第一行置顶滚动公告卡片
        uniqueVodMap.set('AD_NOTICE_ID', {
          vod_id: "AD_NOTICE_ID",
          vod_name: `📢 滚动通知：${AD_TEXT}`,
          vod_pic: "https://i2.100024.xyz/2024/01/13/qrc37o.webp", // 默认公告Icon
          vod_tag: "tv",
          vod_remarks: "官方通知"
        });

        filteredChannels.forEach(ch => {
          const uniqueId = b64Encode(ch.url);
          if (!uniqueVodMap.has(uniqueId)) {
            uniqueVodMap.set(uniqueId, {
              vod_id: uniqueId,
              vod_name: ch.name,
              vod_pic: ch.logo,            // 100% 对齐标准的 vod_pic 字段
              vod_tag: "tv",
              vod_remarks: "TG频道@flymaf"
            });
          }
        });

        return jsonResponse({
          class: groups,
          list: Array.from(uniqueVodMap.values())
        });

      } else {
        // 【3. 首页初始化路由】每次打开 APP 时走这里！
        // 核心修正：影视仓和 MiraPlay 首次打开时必须在 list 里塞入数据，否则开屏不显示广告卡片
        const homeVodList = [];
        
        // 📢 首页大推荐里强行塞入滚动公告
        homeVodList.push({
          vod_id: "AD_NOTICE_ID",
          vod_name: `📢 滚动通知：${AD_TEXT}`,
          vod_pic: "https://i2.100024.xyz/2024/01/13/qrc37o.webp",
          vod_tag: "tv",
          vod_remarks: "官方通知"
        });

        // 默认挑选前10个频道作为首页推荐展示，顺便直接把台标灌输给 APP
        const previewChannels = allChannels.slice(0, 15);
        previewChannels.forEach(ch => {
          homeVodList.push({
            vod_id: b64Encode(ch.url),
            vod_name: ch.name,
            vod_pic: ch.logo,
            vod_tag: "tv",
            vod_remarks: "TG频道@flymaf"
          });
        });

        return jsonResponse({
          class: groups,
          list: homeVodList // 完美喂饱影视仓开屏数据加载器
        });
      }

    } catch (err) {
      console.error(err);
      return jsonResponse({ error: "M3U 解析或加载失败", details: err.message }, 502);
    }
  }

  return new Response(`T4 Service Active`, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}

// Base64 安全加解密组件
function b64Encode(str) {
  return btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, (match, p1) => String.fromCharCode('0x' + p1)));
}
function b64Decode(str) {
  return decodeURIComponent(atob(str).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''));
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status: status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, HEAD, POST, OPTIONS',
      'Cache-Control': 'no-cache'
    }
  });
}

async function fetchM3U() {
  const resp = await fetch(M3U_URL, {
    headers: { 
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) IPTV/1.0',
      'Accept': 'text/plain, */*'
    }
  });
  if (!resp.ok) throw new Error(`请求 M3U 失败，状态: ${resp.status}`);
  return await resp.text();
}

function parseM3UToGroups(m3uText) {
  const lines = m3uText.split(/\r?\n/);
  const groups = new Map();
  const allChannels = [];
  const seenUrls = new Set();
  let currentGroup = "未分类";

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    if (line.startsWith('#EXTINF:') || line.startsWith('#EXTINF :')) {
      const nameMatch = line.match(/,(.+?)$/);
      
      // 容错率极高的新 tvg-logo 抓取正则，全面包容单引号、双引号及无引号
      const logoMatch = line.match(/tvg-logo=["']?([^"'\s>]+)["']?/i);
      const groupMatch = line.match(/group-title=["']?([^"'\s>]+)["']?/i);

      let name = nameMatch ? nameMatch[1].trim() : '未知频道';
      let logo = (logoMatch && logoMatch[1]) ? logoMatch[1].trim() : '';
      let group = (groupMatch && groupMatch[1]) ? groupMatch[1].trim() : currentGroup;

      currentGroup = group;
      let rawGroupName = group.trim();

      let urlLine = "";
      let j = i + 1;
      while (j < lines.length) {
        const nextLine = lines[j].trim();
        if (nextLine.startsWith('#EXTINF') || nextLine.startsWith('#')) {
          break; 
        }
        if (nextLine.length > 0) {
          urlLine = nextLine;
          i = j; 
          break;
        }
        j++;
      }

      if (urlLine) {
        const mainUrl = urlLine.split('#')[0].trim();
        const uniqueKey = `${rawGroupName}_${mainUrl}`;
        
        if (seenUrls.has(uniqueKey)) {
          continue;
        }
        seenUrls.add(uniqueKey);

        if (!groups.has(rawGroupName) && rawGroupName.length > 0) {
          groups.set(rawGroupName, { type_id: rawGroupName, type_name: rawGroupName });
        }

        // 核心格式修正：对台标进行 100% 安全转义
        let finalLogo = 'https://i2.100024.xyz/2024/01/13/qrc37o.webp';
        if (logo && (logo.startsWith('http://') || logo.startsWith('https://'))) {
          // 清除可能残留在 URL 尾部的多余标点符号
          finalLogo = encodeURI(logo.replace(/[",']/g, ''));
        }

        allChannels.push({
          name: name,
          url: mainUrl, 
          logo: finalLogo, 
          type_id: rawGroupName
        });
      }
    }
  }

  return {
    class: Array.from(groups.values()),
    allChannels
  };
}
