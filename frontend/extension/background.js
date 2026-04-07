const API_URL = 'https://echomemory-api-161866545382.asia-south1.run.app/api/v1';
const FRONTEND_URL = 'https://echomemory-frontend-161866545382.asia-south1.run.app';

// ─── Token helpers ────────────────────────────────────────────────────────────

async function getAuthToken() {
  const result = await chrome.storage.local.get(['auth_token', 'token_expiry']);
  if (!result.auth_token || !result.token_expiry) return null;
  if (Date.now() > result.token_expiry) {
    await chrome.storage.local.remove(['auth_token', 'token_expiry']);
    return null;
  }
  return result.auth_token;
}

async function saveAuthToken(token) {
  // JWT expiry = 7 days (matches backend JWT_EXPIRY_DAYS)
  const expiry = Date.now() + 7 * 24 * 60 * 60 * 1000;
  await chrome.storage.local.set({ auth_token: token, token_expiry: expiry });
}

// ─── Domain / dedup helpers ───────────────────────────────────────────────────

async function isDomainBlocked(url) {
  try {
    const domain = new URL(url).hostname;
    const result = await chrome.storage.local.get(['blocked_domains']);
    const blocked = result.blocked_domains || [];
    return blocked.some(d => domain === d || domain.endsWith('.' + d));
  } catch {
    return false;
  }
}

async function isRecentCapture(url) {
  const cache = await chrome.storage.local.get(['capture_cache']);
  const cacheMap = cache.capture_cache || {};
  const ts = cacheMap[url];
  if (!ts) return false;
  // Re-capture after 24 hours
  if (Date.now() - ts > 24 * 60 * 60 * 1000) {
    delete cacheMap[url];
    await chrome.storage.local.set({ capture_cache: cacheMap });
    return false;
  }
  return true;
}

async function markAsCaptured(url) {
  const cache = await chrome.storage.local.get(['capture_cache']);
  const cacheMap = cache.capture_cache || {};
  cacheMap[url] = Date.now();
  await chrome.storage.local.set({ capture_cache: cacheMap });
}

// ─── Badge ────────────────────────────────────────────────────────────────────

async function updateBadgeCount() {
  const token = await getAuthToken();
  if (!token) {
    chrome.action.setBadgeText({ text: '' });
    return;
  }
  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const user = await res.json();
      const count = user.memory_count || 0;
      chrome.action.setBadgeText({ text: count > 0 ? String(count) : '' });
      chrome.action.setBadgeBackgroundColor({ color: '#4F46E5' });
    } else if (res.status === 401) {
      await chrome.storage.local.remove(['auth_token', 'token_expiry']);
      chrome.action.setBadgeText({ text: '' });
    }
  } catch {
    // offline - keep existing badge
  }
}

// ─── Page capture ─────────────────────────────────────────────────────────────

async function capturePage(tab, text, title) {
  const result = await chrome.storage.local.get(['paused']);
  if (result.paused) return;
  if (!tab?.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) return;
  if (await isDomainBlocked(tab.url)) return;
  if (await isRecentCapture(tab.url)) return;

  const token = await getAuthToken();
  if (!token) return;

  if (!text || text.trim().length < 200) return;

  try {
    const response = await fetch(`${API_URL}/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        source_type: 'web',
        url: tab.url,
        title: title || tab.title || '',
        raw_text: text.trim().slice(0, 50000),
      }),
    });

    if (response.ok) {
      await markAsCaptured(tab.url);
      await updateBadgeCount();
    } else if (response.status === 401) {
      await chrome.storage.local.remove(['auth_token', 'token_expiry']);
    }
  } catch (err) {
    console.error('[EchoMemory] Capture failed:', err);
  }
}

// ─── Message handler ──────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CAPTURE') {
    chrome.tabs.get(sender.tab.id, (tab) => {
      capturePage(tab, message.text, message.title);
    });
  }

  if (message.type === 'SET_PAUSED') {
    chrome.storage.local.set({ paused: message.paused });
  }

  // ── Auth token received from the frontend page after OAuth ──
  // The /auth/complete page calls chrome.runtime.sendMessage({ type: 'AUTH_TOKEN', token })
  if (message.type === 'AUTH_TOKEN' && message.token) {
    saveAuthToken(message.token).then(() => {
      updateBadgeCount();
      sendResponse({ ok: true });
    });
    return true; // Keep channel open for async response
  }

  if (message.type === 'LOGOUT') {
    chrome.storage.local.remove(['auth_token', 'token_expiry']);
    chrome.action.setBadgeText({ text: '' });
  }

  if (message.type === 'GET_TOKEN') {
    getAuthToken().then(token => sendResponse({ token }));
    return true;
  }
});

// ─── Startup ──────────────────────────────────────────────────────────────────

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

chrome.runtime.onStartup.addListener(() => {
  updateBadgeCount();
});
