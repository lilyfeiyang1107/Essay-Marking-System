// GitHub Pages hosts the learning app; an optional HTTPS backend handles AI.
// Local TXT parsing and the public examples do not require that backend.
(() => {
  const config = window.WENMO_SITE;
  if (!config || config.mode !== 'pages') return;
  async function jsonResponse(url, options) {
    let response;
    try { response = await fetch(url, options); }
    catch (error) {
      if (error.name === 'TimeoutError' || error.name === 'AbortError') throw error;
      throw Error(navigator.onLine ? '暂时无法连接批改服务，请稍后重试；当前文字仍保留。' : '当前处于离线状态，请联网后再使用此功能。');
    }
    let data;
    try { data = await response.json(); }
    catch { throw Error('服务返回异常，请联系老师检查批改服务。'); }
    if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : '请检查输入内容后重试。');
    return data;
  }
  async function readTextFile(options) {
    const file = options.body && options.body.get('file');
    if (!file) throw Error('请选择文件。');
    if (!file.name.toLowerCase().endsWith('.txt')) throw Error('文件解析服务尚未连接。请先上传TXT文件，或从PDF、Word复制文字粘贴到正文。');
    if (file.size > 8 * 1024 * 1024) throw Error('文件不能超过8 MB。');
    const bytes = await file.arrayBuffer();
    let text;
    try { text = new TextDecoder('utf-8', {fatal:true}).decode(bytes); }
    catch { try { text = new TextDecoder('gb18030', {fatal:true}).decode(bytes); } catch { throw Error('文字编码无法识别，请另存为UTF-8格式的TXT。'); } }
    text = text.trim();
    if (!text) throw Error('文件中没有可读取的文字。');
    if (text.length > 20000) throw Error('文字超过20000字符，请只上传需要批改的作文。');
    return {text};
  }
  window.WenmoPages = {
    async request(url, options) {
      if (url.startsWith('/api/demo/')) {
        const genre = url.slice('/api/demo/'.length);
        if (!['narrative','argumentative'].includes(genre)) throw Error('未知文体。');
        return jsonResponse(config.basePath + 'examples/' + genre + '.json', options);
      }
      if (!config.apiBase) {
        if (url === '/api/status') return {ai_ready:false, backend_missing:true};
        if (url === '/api/extract') return readTextFile(options);
        throw Error('自动批改服务尚未连接。目前可上传TXT、编辑作文和体验教学示例；请老师连接批改服务后再提交。');
      }
      return jsonResponse(config.apiBase + url, options);
    }
  };
  document.addEventListener('DOMContentLoaded', () => {
    if (config.apiBase) return;
    const notice = document.querySelector('#hosting-notice');
    notice.hidden = false;
    notice.textContent = '欢迎使用文墨：可学习图解课程、上传TXT和体验示例。自动批改服务尚未连接，暂不能为你的作文实时评分。';
  });
})();
