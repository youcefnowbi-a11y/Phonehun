// ============================================================
// DroidCommand PWA // Master Application Controller
// ============================================================
/// <reference path="./cockpit-types.d.ts" />
// @ts-check

const STATE = {
  activeView: 'cockpit',
  activeSerial: null,
  isArmed: false,
  devices: [],
  targets: [],
  deferredInstallPrompt: null
};

// Auto-authenticated API Helper
async function api(endpoint, options = {}) {
  const token = window.__DC_TOKEN__ || '';
  const headers = {
    'X-API-Token': token,
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  try {
    const res = await fetch(endpoint, { ...options, headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
      throw new Error(err.error || err.message || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`[API Error] ${endpoint}:`, err);
    throw err;
  }
}

// ============================================================
// PWA Installation Hook
// ============================================================
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  STATE.deferredInstallPrompt = e;
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
  const btn = document.getElementById('installPwaBtn');
  if (btn && !isStandalone) btn.style.display = 'inline-flex';
});

async function installPwa() {
  if (!STATE.deferredInstallPrompt) return;
  STATE.deferredInstallPrompt.prompt();
  const choice = await STATE.deferredInstallPrompt.userChoice;
  if (choice.outcome === 'accepted') {
    const btn = document.getElementById('installPwaBtn');
    if (btn) btn.style.display = 'none';
  }
  STATE.deferredInstallPrompt = null;
}

let CURRENT_MODE = 'ai';

function setPrimaryMode(mode) {
  CURRENT_MODE = mode;
  const btnAi = document.getElementById('btnModeAi');
  const btnPhone = document.getElementById('btnModePhone');
  const btnManual = document.getElementById('btnModeManual');
  const viewAi = document.getElementById('mode-ai-cockpit');
  const viewPhone = document.getElementById('mode-phone-intelligence');
  const viewManual = document.getElementById('mode-manual-toolkit');

  if (btnAi) btnAi.classList.toggle('active', mode === 'ai');
  if (btnPhone) btnPhone.classList.toggle('active', mode === 'phone');
  if (btnManual) btnManual.classList.toggle('active', mode === 'manual');

  if (viewAi) viewAi.style.display = (mode === 'ai') ? 'grid' : 'none';
  if (viewPhone) viewPhone.style.display = (mode === 'phone') ? 'block' : 'none';
  if (viewManual) viewManual.style.display = (mode === 'manual') ? 'block' : 'none';

  if (mode === 'ai') {
    if (window.Glass) window.Glass.onShow();
    if (window.VesperCockpit) window.VesperCockpit.pollStatus();
  } else if (mode === 'phone') {
    if (window.PhoneIntelligence) window.PhoneIntelligence.init();
  }
}

// ============================================================
// View Switcher (For Manual Sub-Decks)
// ============================================================
function switchView(viewName) {
  STATE.activeView = viewName;

  // Update tabs
  document.querySelectorAll('.nav-tab').forEach((tab) => {
    if (tab.dataset.view === viewName) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  // Update view containers
  document.querySelectorAll('.view-section').forEach((sec) => {
    if (sec.id === `view-${viewName}`) {
      sec.style.display = 'grid';
    } else {
      sec.style.display = 'none';
    }
  });

  if (viewName === 'cockpit' && window.Glass) {
    window.Glass.onShow();
  }
  if (viewName === 'skeleton' && window.Skeleton) {
    window.Skeleton.loadPosture();
  }
  if (viewName === 'forensics' && window.Forensics) {
    window.Forensics.switchTab('sms');
  }
}

// ============================================================
// Master Arm / Stand Down Toggle
// ============================================================
async function toggleMasterArm() {
  const btn = document.getElementById('masterArmBtn');
  const targetState = !STATE.isArmed;

  try {
    const res = await api(targetState ? '/api/ghost/hunter/arm' : '/api/ghost/hunter/standdown', {
      method: 'POST'
    });

    if (res.success !== false) {
      STATE.isArmed = targetState;
      updateArmStateUi();
      pushFlow(targetState ? 'SYS' : 'INFO', targetState ? 'HUNTER ARMED — automatic dialog strikes live' : 'HUNTER STOOD DOWN');
    }
  } catch (e) {
    pushFlow('ALERT', `Arm toggle error: ${e.message}`);
  }
}

function updateArmStateUi() {
  const btn = document.getElementById('masterArmBtn');
  const statusPill = document.getElementById('masterStatusPill');

  if (STATE.isArmed) {
    btn.textContent = 'STAND DOWN';
    btn.classList.add('armed');
    statusPill.className = 'status-pill hunting';
    statusPill.innerHTML = '<span class="pulse-dot"></span> HUNTING';
  } else {
    btn.textContent = 'MASTER ARM';
    btn.classList.remove('armed');
    statusPill.className = 'status-pill online';
    statusPill.innerHTML = '<span class="pulse-dot"></span> LISTENING';
  }
}

// ============================================================
// Operation Flow Telemetry Stream
// ============================================================
function pushFlow(tag, message) {
  const stream = document.getElementById('operationFlowStream');
  if (!stream) return;

  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour12: false });

  const row = document.createElement('div');
  row.className = 'flow-row';
  row.innerHTML = `
    <span class="flow-time">${timeStr}</span>
    <span class="flow-tag ${tag}">${tag}</span>
    <span class="flow-msg">${escapeHtml(message)}</span>
  `;

  stream.appendChild(row);
  stream.scrollTop = stream.scrollHeight;

  // Limit memory
  if (stream.children.length > 250) {
    stream.removeChild(stream.firstChild);
  }
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ============================================================
// Poll Devices & Telemetry
// ============================================================
async function pollDevices() {
  try {
    const data = await api('/api/devices');
    const devices = (data.devices || []).filter(d => d.status === 'device');
    STATE.devices = devices;

    const devCountEl = document.getElementById('telemetryDeviceCount');
    if (devCountEl) devCountEl.textContent = devices.length;

    const select = document.getElementById('deviceSerialSelect');
    if (select) {
      const current = select.value;
      select.innerHTML = '<option value="">Default Attached Device</option>';
      devices.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.serial;
        opt.textContent = `${d.model || d.device || d.serial} (${d.serial})`;
        select.appendChild(opt);
      });
      if (current) select.value = current;
      STATE.activeSerial = select.value || (devices[0] ? devices[0].serial : null);
    }
  } catch (e) {
    // Quiet fail on poll
  }
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  // Setup tabs
  document.querySelectorAll('.nav-tab').forEach((tab) => {
    tab.addEventListener('click', () => switchView(tab.dataset.view));
  });

  // Arm Button
  const armBtn = document.getElementById('masterArmBtn');
  if (armBtn) armBtn.addEventListener('click', toggleMasterArm);

  // Install PWA button
  const installBtn = document.getElementById('installPwaBtn');
  if (installBtn) installBtn.addEventListener('click', installPwa);

  // Initial Polls
  pollDevices();
  // Adaptive heartbeat: 4s when idle, 1.2s while the brain is running —
  // narration feels live during missions, the wire rests when she does.
  setInterval(pollDevices, 4000);
  let brainPollMs = 4000;
  (async function brainHeartbeat() {
    try {
      if (document.hidden) { setTimeout(brainHeartbeat, 4000); return; }
      const s = /** @type {import("./cockpit-types.d.ts").BrainStatus} */ (
        await api('/api/brain/status'));
      const busy = s && s.state === 'running';
      const next = busy ? 1200 : 4000;
      if (next !== brainPollMs) brainPollMs = next;
      if (window.VesperCockpit && typeof window.VesperCockpit.pollStatus === 'function') {
        window.VesperCockpit.pollStatus();
      }
      setTimeout(brainHeartbeat, next);
    } catch (e) {
      setTimeout(brainHeartbeat, brainPollMs); // quiet fail, retry at current cadence
    }
  })();

  // Register Service Worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(err => {
      console.warn('[SW] Registration failed:', err);
    });
  }

  // Initialize Vesper AI Cockpit
  if (window.VesperCockpit) {
    window.VesperCockpit.init();
  }

  pushFlow('SYS', 'DroidCommand PWA Cockpit initialized. System ready.');
});

function setHeroBg(variantName, btnElement) {
  const el = document.querySelector('.hero-vitrine-bg');
  if (!el) return;

  const map = {
    'circuits': '/static/pwa/img/variant_a_disassembly.jpg',
    'glass': '/static/pwa/img/variant_b_glassphone.jpg',
    'contact': '/static/pwa/img/variant_c_contactsheet.jpg'
  };

  const imgUrl = map[variantName] || '/static/pwa/img/hero_bg.jpg';
  el.style.backgroundImage = `
    linear-gradient(180deg, 
      rgba(248, 249, 251, 0.25) 0%, 
      rgba(248, 249, 251, 0.65) 280px, 
      rgba(248, 249, 251, 0.95) 540px, 
      var(--canvas) 100%),
    url('${imgUrl}')
  `;

  document.querySelectorAll('.variant-btn').forEach(b => b.classList.remove('active'));
  if (btnElement) btnElement.classList.add('active');
}
