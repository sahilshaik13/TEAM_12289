const API_URL = 'https://echomemory-api-161866545382.asia-south1.run.app/api/v1';

async function getAuthToken() {
  const result = await chrome.storage.local.get(['auth_token', 'token_expiry']);
  if (!result.auth_token || !result.token_expiry) return null;
  if (Date.now() > result.token_expiry) return null;
  return result.auth_token;
}

async function loadPopupState() {
  const token = await getAuthToken();
  const paused = await chrome.storage.local.get(['paused']);
  const isPaused = paused.paused || false;

  if (!token) {
    document.getElementById('authSection').style.display = 'block';
    document.getElementById('mainSection').style.display = 'none';
    document.getElementById('memoryCount').textContent = 'Not signed in';
    return;
  }

  document.getElementById('authSection').style.display = 'none';
  document.getElementById('mainSection').style.display = 'block';

  const dot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  dot.className = isPaused ? 'status-dot paused' : 'status-dot';
  statusText.textContent = isPaused ? 'Paused' : 'Capturing';

  const btn = document.getElementById('togglePauseBtn');
  btn.textContent = isPaused ? 'Resume Capturing' : 'Pause Capturing';

  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (res.ok) {
      const user = await res.json();
      document.getElementById('memoryCount').textContent =
        `${user.memory_count || 0} memories captured`;
    } else {
      document.getElementById('memoryCount').textContent = 'Error loading count';
    }
  } catch {
    document.getElementById('memoryCount').textContent = 'Offline';
  }
}

document.getElementById('togglePauseBtn').addEventListener('click', async () => {
  const result = await chrome.storage.local.get(['paused']);
  const isPaused = result.paused || false;
  const newPaused = !isPaused;
  await chrome.storage.local.set({ paused: newPaused });
  chrome.runtime.sendMessage({ type: 'SET_PAUSED', paused: newPaused });
  loadPopupState();
});

document.getElementById('openDashboardBtn').addEventListener('click', () => {
  chrome.tabs.create({ url: 'http://localhost:3000' });
});

document.getElementById('logoutBtn').addEventListener('click', async () => {
  await chrome.storage.local.remove(['auth_token', 'token_expiry']);
  chrome.runtime.sendMessage({ type: 'SET_PAUSED', paused: false });
  loadPopupState();
});

document.getElementById('loginBtn').addEventListener('click', () => {
  chrome.tabs.create({ url: `${API_URL}/auth/google` });
});

loadPopupState();
