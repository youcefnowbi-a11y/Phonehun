// ============================================================
// DroidCommand PWA // Radar (Spectrum Sweep & QR Pairing)
// ============================================================

window.Radar = (function () {
  let isSweeping = false;
  let sweepGen = 0;      // fix: generation counter — a superseded sweep never paints
  let engaging = false;  // fix: single-flight engage guard
  let qrPollTimer = null;

  async function triggerSweep() {
    if (isSweeping) return;
    isSweeping = true;
    const gen = ++sweepGen;
    // fix: watchdog — a hung sweep request must never lock the radar forever
    const watchdog = setTimeout(() => { if (gen === sweepGen) isSweeping = false; }, 35000);

    const list = document.getElementById('radarTargetsList');
    if (list) {
      list.innerHTML = '<div style="color: var(--text-slate); padding: 12px; font-family: var(--font-mono); font-size: 12px;">Sweeping RF spectrum and local subnets...</div>';
    }
    pushFlow('SYS', 'Active RF & mDNS sweep initiated.');

    try {
      const res = await api('/api/ghost/hunter/sweep', { method: 'POST' });
      if (gen !== sweepGen) return;  // fix: late stale response discarded

      if (res && res.targets) {
        renderTargets(res.targets);
        pushFlow('INFO', `Sweep complete: ${res.targets.length} target(s) detected.`);
      } else {
        renderTargets([]);  // fix: one shared empty-state, not two divergent ones
      }
    } catch (e) {
      if (list) list.innerHTML = `<div style="color: var(--ruby); padding: 12px;">Sweep failed: ${e.message}</div>`;
    } finally {
      clearTimeout(watchdog);
      if (gen === sweepGen) isSweeping = false;
    }
  }

  function renderTargets(targets) {
    const list = document.getElementById('radarTargetsList');
    if (!list) return;

    if (!targets || targets.length === 0) {
      list.innerHTML = '<div style="color: var(--text-slate); padding: 16px; font-family: var(--font-mono); text-align: center;">Airspace clear. No live ADB doors detected.</div>';
      return;
    }

    list.innerHTML = '';
    targets.forEach((t) => {
      // fix: sweep data arrives from the LAN — other machines control these strings.
      // Build DOM nodes with textContent; broadcast data is never interpolated into HTML.
      const card = document.createElement('div');
      card.className = 'target-card';
      card.style.display = 'flex';
      card.style.alignItems = 'center';
      card.style.justifyContent = 'space-between';
      card.style.gap = '10px';

      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.alignItems = 'center';
      row.style.gap = '10px';

      const badgeColor = t.class === 'OPEN_ADB' ? 'var(--emerald)' :
                         t.class === 'PAIRING_DIALOG' ? 'var(--amber)' :
                         t.class === 'STLS' ? '#c084fc' : 'var(--text-slate)';

      const badge = document.createElement('span');
      badge.style.color = badgeColor;
      badge.style.fontWeight = '600';
      badge.textContent = `[${t.class || 'ADB'}]`;

      const addr = document.createElement('span');
      addr.style.color = 'var(--text-bone)';
      addr.style.fontWeight = '500';
      addr.textContent = `${t.ip}:${t.port}`;

      row.appendChild(badge);
      row.appendChild(addr);
      if (t.model) {
        const model = document.createElement('span');
        model.style.color = 'var(--text-slate)';
        model.style.fontSize = '11px';
        model.textContent = `(${t.model})`;
        row.appendChild(model);
      }

      const btn = document.createElement('button');
      btn.className = 'action-pill';
      btn.style.padding = '4px 12px';
      btn.style.fontSize = '11px';
      btn.textContent = 'Engage';
      btn.addEventListener('click', () => engage(t.ip, t.port));

      card.appendChild(row);
      card.appendChild(btn);
      list.appendChild(card);
    });
  }

  async function engage(ip, port) {
    if (engaging) return;  // fix: double-click never fires two concurrent strikes
    engaging = true;
    const watchdog = setTimeout(() => { engaging = false; }, 10000);
    pushFlow('STRIKE', `Engaging target ${ip}:${port}...`);
    try {
      const res = await api('/api/ghost/hunter/engage', {
        method: 'POST',
        body: JSON.stringify({ ip, port })
      });

      if (res && res.success) {
        pushFlow('HIT', `Target ${ip}:${port} engaged successfully: ${res.vector || 'walk-in'}`);
        pollDevices();
      } else {
        pushFlow('ALERT', `Engagement failed: ${(res && res.error) || 'Door refused'}`);
      }
    } catch (e) {
      pushFlow('ALERT', `Engagement error: ${e.message}`);
    } finally {
      clearTimeout(watchdog);
      engaging = false;
    }
  }

  // QR Code Pairing
  async function startQrPairing() {
    try {
      const res = await api('/api/ghost/qr/start', {
        method: 'POST',
        body: JSON.stringify({ ttl_s: 300 })
      });

      if (res.success && res.qr_svg) {
        const qrContainer = document.getElementById('qrCodeContainer');
        const qrImg = document.getElementById('qrCodeImage');
        const qrMeta = document.getElementById('qrCodeMeta');

        if (qrImg) qrImg.src = res.qr_svg;
        if (qrMeta) qrMeta.textContent = `${res.lan_ip}:${res.port} — Scan with Phone`;
        if (qrContainer) qrContainer.style.display = 'block';

        pushFlow('SYS', 'QR pairing gateway armed. Scan now from Wireless Debugging.');
        if (qrPollTimer) clearInterval(qrPollTimer);
        qrPollTimer = setInterval(pollQrStatus, 2000);
      }
    } catch (e) {
      pushFlow('ALERT', `QR gateway error: ${e.message}`);
    }
  }

  async function pollQrStatus() {
    try {
      const res = await api('/api/ghost/qr/status');
      if (res.paired) {
        clearInterval(qrPollTimer);
        pushFlow('HIT', '*** QR PAIRING COMPLETE: Device authenticated! ***');
        const qrContainer = document.getElementById('qrCodeContainer');
        if (qrContainer) qrContainer.style.display = 'none';
        pollDevices();
      } else if (!res.running) {
        if (qrPollTimer) { clearInterval(qrPollTimer); qrPollTimer = null; }
        const qrContainer = document.getElementById('qrCodeContainer');
        if (qrContainer) qrContainer.style.display = 'none';
      }
    } catch (e) {}
  }

  async function rehydrateQr() {
    // fix: after F5 an in-flight server-side pairing was invisible — re-arm the poll
    try {
      const res = await api('/api/ghost/qr/status');
      if (res && res.running) {
        const qrContainer = document.getElementById('qrCodeContainer');
        const qrMeta = document.getElementById('qrCodeMeta');
        if (qrMeta && !qrMeta.textContent) {
          qrMeta.textContent = 'Pairing session in progress — no rescan needed';
        }
        if (qrContainer) qrContainer.style.display = 'block';
        if (!qrPollTimer) qrPollTimer = setInterval(pollQrStatus, 2000);
      }
    } catch (e) {}
  }
  setTimeout(rehydrateQr, 1500);

  return {
    triggerSweep,
    engage,
    startQrPairing,
    onHide: () => {  // fix: teardown on deck exit — the 2s poll stops with the view
      if (qrPollTimer) { clearInterval(qrPollTimer); qrPollTimer = null; }
    }
  };
})();
