const API_URL = 'https://echomemory-api-161866545382.asia-south1.run.app/api/v1';
const FRONTEND_URL = 'https://echomemory-frontend-161866545382.asia-south1.run.app';

async function getAuthToken() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: 'GET_TOKEN' }, (res) => {
      resolve(res?.token || null);
    });
  });
}

async function loadPopupState() {
  const token = await getAuthToken();
  const result = await chrome.storage.local.get(['paused']);
  const isPaused = result.paused || false;

  const authSection = document.getElementById('authSection');
  const mainSection = document.getElementById('mainSection');
  const memCount = document.getElementById('memoryCount');
  const dot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const toggleBtn = document.getElementById('togglePauseBtn');

  if (!token) {
    authSection.style.display = 'block';
    mainSection.style.display = 'none';
    memCount.textContent = 'Not signed in';
    return;
  }

  authSection.style.display = 'none';
  mainSection.style.display = 'block';

  dot.className = isPaused ? 'status-dot paused' : 'status-dot';
  statusText.textContent = isPaused ? 'Paused' : 'Capturing';
  toggleBtn.textContent = isPaused ? 'Resume Capturing' : 'Pause Capturing';

  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const user = await res.json();
      memCount.textContent = `${user.memory_count || 0} memories captured`;
    } else if (res.status === 401) {
      // Token expired — go back to sign-in
      await chrome.storage.local.remove(['auth_token', 'token_expiry']);
      loadPopupState();
    } else {
      memCount.textContent = 'Error loading count';
    }
  } catch {
    memCount.textContent = 'Offline';
  }
}

// ─── Sign in ─────────────────────────────────────────────────────────────────
// Opens the backend OAuth URL in a new tab. After Google auth, the backend
// redirects to the frontend /auth/complete page, which sends AUTH_TOKEN
// back to this extension via chrome.runtime.sendMessage.
document.getElementById('loginBtn').addEventListener('click', () => {
  chrome.tabs.create({ url: `${API_URL}/auth/google` });
  window.close();
});

// ─── Pause / resume ───────────────────────────────────────────────────────────
document.getElementById('togglePauseBtn').addEventListener('click', async () => {
  const result = await chrome.storage.local.get(['paused']);
  const newPaused = !result.paused;
  chrome.runtime.sendMessage({ type: 'SET_PAUSED', paused: newPaused });
  loadPopupState();
});

// ─── Dashboard ────────────────────────────────────────────────────────────────
document.getElementById('openDashboardBtn').addEventListener('click', () => {
  chrome.tabs.create({ url: `${FRONTEND_URL}/dashboard` });
});

// ─── Logout ───────────────────────────────────────────────────────────────────
document.getElementById('logoutBtn').addEventListener('click', async () => {
  chrome.runtime.sendMessage({ type: 'LOGOUT' });
  loadPopupState();
});

loadPopupState();
