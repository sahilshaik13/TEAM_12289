const DWELL_THRESHOLD_MS = 10000;
const API_URL = 'https://echomemory-api-161866545382.asia-south1.run.app/api/v1';
const MAX_TEXT_LENGTH = 50000;
const DEDUP_CACHE_TTL_MS = 24 * 60 * 60 * 1000;

let dwellTimer = null;
let pausedGlobally = false;

async function getAuthToken() {
  const result = await chrome.storage.local.get(['auth_token', 'token_expiry']);
  if (!result.auth_token || !result.token_expiry) return null;
  if (Date.now() > result.token_expiry) return null;
  return result.auth_token;
}

async function isDomainBlocked(url) {
  try {
    const domain = new URL(url).hostname;
    const result = await chrome.storage.local.get(['blocked_domains']);
    return result.blocked_domains?.includes(domain) || false;
  } catch {
    return false;
  }
}

async function isRecentCapture(url) {
  const cache = await chrome.storage.local.get(['capture_cache']);
  const cacheMap = cache.capture_cache || {};
  return !!cacheMap[url];
}

async function markAsCaptured(url) {
  const cache = await chrome.storage.local.get(['capture_cache']);
  const cacheMap = cache.capture_cache || {};
  cacheMap[url] = Date.now();
  await chrome.storage.local.set({ capture_cache: cacheMap });
}

async function capturePage(tab) {
  if (pausedGlobally) return;
  if (await isDomainBlocked(tab.url)) return;
  if (await isRecentCapture(tab.url)) return;

  const token = await getAuthToken();
  if (!token) {
    console.log('[EchoMemory] Not authenticated');
    return;
  }

  const documentClone = document.cloneNode(true);
  const article = new Readability(documentClone).parse();

  if (!article || !article.textContent || article.textContent.trim().length < 200) {
    return;
  }

  const payload = {
    source_type: 'web',
    url: tab.url,
    title: article.title || tab.title,
    raw_text: article.textContent.trim().slice(0, MAX_TEXT_LENGTH),
  };

  try {
    const response = await fetch(`${API_URL}/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      await markAsCaptured(tab.url);
      await updateBadgeCount();
    }
  } catch (err) {
    console.error('[EchoMemory] Capture failed:', err);
  }
}

async function updateBadgeCount() {
  const token = await getAuthToken();
  if (!token) return;
  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (res.ok) {
      const user = await res.json();
      chrome.action.setBadgeText({ text: String(user.memory_count || 0) });
      chrome.action.setBadgeBackgroundColor({ color: '#4F46E5' });
    }
  } catch {}
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    dwellTimer = setTimeout(() => {
      chrome.runtime.sendMessage({ type: 'TAB_VISIBLE', tabId: chrome.runtime.lastTabId });
    }, DWELL_THRESHOLD_MS);
  } else {
    clearTimeout(dwellTimer);
  }
});

chrome.runtime.onMessage.addListener((message, sender) => {
  if (message.type === 'CAPTURE_TRIGGER') {
    capturePage(message.tab);
  }
  if (message.type === 'SET_PAUSED') {
    pausedGlobally = message.paused;
  }
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    blocked_domains: [
      'mail.google.com',
      'outlook.live.com',
      'accounts.google.com',
      'login.microsoftonline.com',
      'bankofamerica.com',
      'chase.com',
      'paypal.com',
    ],
    paused: false,
  });
});
