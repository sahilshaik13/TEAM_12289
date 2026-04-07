const DWELL_THRESHOLD_MS = 10000;
let dwellTimer = null;

function captureCurrentPage() {
  const documentClone = document.cloneNode(true);
  const article = new Readability(documentClone).parse();

  if (!article || !article.textContent || article.textContent.trim().length < 200) {
    return;
  }

  const payload = {
    type: 'CAPTURE',
    url: window.location.href,
    title: article.title || document.title,
    text: article.textContent.trim().slice(0, 50000),
    source_type: 'web',
  };

  chrome.runtime.sendMessage(payload);
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    dwellTimer = setTimeout(captureCurrentPage, DWELL_THRESHOLD_MS);
  } else {
    clearTimeout(dwellTimer);
  }
});
