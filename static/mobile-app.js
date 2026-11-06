// Installation UX and learning interactions. No student work is stored here.
let installPrompt = null;
window.addEventListener('beforeinstallprompt', event => {
  event.preventDefault();
  installPrompt = event;
  $('#install-button').textContent = '安装 APP ↗';
});
function installationState() {
  return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
}
async function installApp() {
  if (installPrompt) {
    const prompt = installPrompt;
    installPrompt = null;
    await prompt.prompt();
    await prompt.userChoice;
    return;
  }
  $('#install-context').textContent = installationState()
    ? '你已在独立APP窗口中使用文墨，无需重复安装。'
    : !window.isSecureContext
      ? '当前地址不支持安装。请在公网 HTTPS 地址部署后，用手机浏览器打开并添加到主屏幕。'
      : '如果浏览器未显示安装提示，请按照以下步骤添加到主屏幕。公网使用需要 HTTPS。';
  $('#install-dialog').showModal();
}
$('#install-button').addEventListener('click', installApp);
$('#mobile-install').addEventListener('click', installApp);
['#close-install', '#install-done'].forEach(id => $(id).addEventListener('click', () => $('#install-dialog').close()));
window.addEventListener('appinstalled', () => {
  installPrompt = null;
  $('#install-button').textContent = '已安装 ✓';
});
$('#hero-write').addEventListener('click', () => {
  $('.editor-card').scrollIntoView({behavior:'smooth', block:'start'});
});
$$('[data-start-genre]').forEach(button => button.addEventListener('click', () => {
  if (state.busy) return;
  selectGenre(button.dataset.startGenre);
  switchView('workshop');
  $('.editor-card').scrollIntoView({behavior:'smooth', block:'start'});
}));
$('#mobile-report').addEventListener('click', () => {
  switchView('workshop');
  if (state.report) {
    $$('.mobile-dock button').forEach(b => b.classList.toggle('active', b.id === 'mobile-report'));
    $('#report-section').scrollIntoView({behavior:'smooth', block:'start'});
  } else {
    feedback('还没有批改报告。先上传作文并开始批改，或点击“体验一篇示例”。');
    $('#feedback').scrollIntoView({behavior:'smooth', block:'center'});
  }
});
$$('[data-answer]').forEach(button => button.addEventListener('click', () => {
  $$('[data-answer]').forEach(b => {b.classList.remove('correct','incorrect');b.setAttribute('aria-pressed','false');});
  button.setAttribute('aria-pressed','true');
  const correct = button.dataset.answer === 'correct';
  button.classList.add(correct ? 'correct' : 'incorrect');
  $('#quiz-feedback').textContent = correct
    ? '判断正确！“只要……就一定……”把兴趣当成成功的充分条件。还需考虑能力、资源和持续投入。'
    : '再想一想：“所有人”“一定”是否说得太满？试着找出被忽略的条件。';
}));
function connectivity() { $('#offline-banner').hidden = navigator.onLine; }
window.addEventListener('online', connectivity);
window.addEventListener('offline', connectivity);
connectivity();
if ('serviceWorker' in navigator && window.isSecureContext) {
  navigator.serviceWorker.register('/sw.js').catch(() => {
    // The learning app remains usable online if offline installation is unavailable.
    $('#install-context').textContent = '离线功能暂不可用。你仍可在线使用文墨。';
  });
}
// Small vector navigation icons render consistently across Android and iOS.
const dockIcons = [
  '<path d="m4 16-1 5 5-1L20 8l-4-4L4 16Zm9-9 4 4M3 21l5-1"/>',
  '<path d="M3 5c4-2 6-1 9 1 3-2 5-3 9-1v15c-4-2-6-1-9 1-3-2-5-3-9-1V5Zm9 1v15"/>',
  '<path d="M6 3h12v18H6zM9 8h6m-6 4h6m-6 4h4"/>',
  '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>'
];
$$('.mobile-dock button>span').forEach((span,i) => {
  if (i === 3) { span.innerHTML = '<img src="/static/art/wenmo-192.png" width="26" height="26" alt="">'; return; }
  span.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${dockIcons[i]}</svg>`;
});
