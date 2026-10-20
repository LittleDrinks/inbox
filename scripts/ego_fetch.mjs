import { readFileSync, writeFileSync } from 'node:fs';

const payloadPath = process.env.EGO_PAYLOAD || 'C:/Users/q2635/AppData/Local/Temp/ego_payload.json';
const outputPath = process.env.EGO_OUTPUT || 'C:/Users/q2635/AppData/Local/Temp/ego_output.json';

let config = {};
try {
  config = JSON.parse(readFileSync(payloadPath, 'utf8'));
} catch (e) {
  writeFileSync(outputPath, JSON.stringify({ ok: false, error: 'Read payload failed: ' + e.message }));
  process.exit(1);
}

const { mode, url, options = {} } = config;
const task = await taskSpace(`inbox-${mode}-${Date.now()}`);
const page = task.page("p1");

try {
  await page.goto(url);
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(3000);

  let data = {};

  if (mode === 'xhs') {
    // 滚动加载评论（如果请求抓取评论）
    if (options.withComments) {
      for (let i = 0; i < (options.commentScrolls || 3); i++) {
        await page.evaluate(() => window.scrollBy(0, 1000));
        await page.waitForTimeout(1000);
      }
    }

    data = await page.evaluate((withComments) => {
      const state = window.__INITIAL_STATE__;
      const noteMap = state?.note?.noteDetailMap || {};
      const firstKey = Object.keys(noteMap)[0];
      const note = noteMap[firstKey]?.note;

      const title = note?.title || document.querySelector('#detail-title, .title')?.innerText || document.title;
      const desc = note?.desc || document.querySelector('#detail-desc, .desc')?.innerText || '';
      const author = note?.user?.nickname || document.querySelector('.author-wrapper .name')?.innerText || '';
      const time = note?.time ? new Date(note.time).toISOString() : (document.querySelector('.date')?.innerText || '');

      // 高清原图
      const images = (note?.imageList || []).map(img => img.urlDefault || img.url);

      // 原画视频流
      let videoUrls = [];
      if (note?.video) {
        const stream = note.video.media?.stream || {};
        for (const codec of Object.keys(stream)) {
          for (const item of (stream[codec] || [])) {
            if (item.masterUrl) {
              videoUrls.push({
                format: item.format,
                quality: item.qualityType || item.streamDesc,
                url: item.masterUrl
              });
            }
          }
        }
      }

      // 提取评论
      let comments = [];
      if (withComments) {
        const commentItems = document.querySelectorAll('.comment-item, [class*="comment-item"]');
        commentItems.forEach(el => {
          const cAuthor = el.querySelector('.author, .user-name, [class*="author"], [class*="name"]')?.innerText?.trim();
          const cContent = el.querySelector('.content, .note-text, [class*="content"]')?.innerText?.trim();
          const cDate = el.querySelector('.date, [class*="date"]')?.innerText?.trim();
          const cLike = el.querySelector('.like, [class*="like"]')?.innerText?.trim();
          if (cContent && !comments.some(item => item.content === cContent && item.author === cAuthor)) {
            comments.push({ author: cAuthor, content: cContent, date: cDate, like: cLike });
          }
        });
      }

      return {
        type: videoUrls.length > 0 ? 'video' : 'normal',
        title,
        author,
        desc,
        time,
        images,
        videoUrls,
        comments
      };
    }, Boolean(options.withComments));

  } else if (mode === 'wechat') {
    data = await page.evaluate(() => {
      const title = document.querySelector('#activity-name')?.innerText?.trim() || document.title;
      const author = document.querySelector('#js_name')?.innerText?.trim() || '';
      const date = document.querySelector('#publish_time')?.innerText?.trim() || '';
      const contentEl = document.querySelector('#js_content');
      const content = contentEl ? contentEl.innerText?.trim() : '';
      const images = Array.from(document.querySelectorAll('#js_content img[data-src]')).map(img => img.getAttribute('data-src'));

      return {
        title,
        author,
        date,
        content,
        images
      };
    });

  } else if (mode === 'bilibili') {
    data = await page.evaluate(() => {
      const playinfo = window.__playinfo__;
      const initialState = window.__INITIAL_STATE__;
      const title = initialState?.videoData?.title || document.title;
      const desc = initialState?.videoData?.desc || '';
      const audioStreams = playinfo?.data?.dash?.audio || [];
      const videoStreams = playinfo?.data?.dash?.video || [];

      return {
        title,
        desc,
        duration: initialState?.videoData?.duration,
        audioStreams: audioStreams.map(a => ({ id: a.id, bandwidth: a.bandwidth, baseUrl: a.baseUrl })),
        videoStreams: videoStreams.map(v => ({ id: v.id, bandwidth: v.bandwidth, baseUrl: v.baseUrl }))
      };
    });
  }

  writeFileSync(outputPath, JSON.stringify({ ok: true, data }, null, 2), 'utf8');
} catch (err) {
  writeFileSync(outputPath, JSON.stringify({ ok: false, error: err.message }, null, 2), 'utf8');
} finally {
  await completeTaskSpace(task.spaceId, { keep: false });
}
