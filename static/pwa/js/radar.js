// ============================================================
// DroidCommand PWA // Radar (Spectrum Sweep & QR Pairing)
// ============================================================

window.Radar = (function () {
  let isSweeping = false;
  let qrPollTimer = null;

  async function triggerSweep() {
    if (isSweeping) return;
    isSweeping = true;

    const list = document.getElementById('radarTargetsList');
    if (list) {
      list.innerHTML = '<div style="color: var(--text-slate); padding: 12px; font-family: var(--font-mono); font-size: 12px;">Sweeping RF spectrum and local subnets...</div>';
    }
    pushFlow('SYS', 'Active RF & mDNS sweep initiated.');

    try {
      const res = await api('/api/ghost/hunter/sweep', { method: 'POST' });
      isSweeping = false;

      if (res && res.targets) {
        renderTargets(res.targets);
        pushFlow('INFO', `Sweep complete: ${res.targets.length} target(s) detected.`);
      } else {
        if (list) list.innerHTML = '<div style="color: var(--text-slate); padding: 12px;">No targets detected.</div>';
      }
    } catch (e) {
      isSweeping = false;
      if (list) list.innerHTML = `<div style="color: var(--ruby); padding: 12px;">Sweep failed: ${e.message}</div>`;
    }
  }

  function renderTargets(targets) {
    const list = document.getElementById('radarTargetsList');
    if (!list) return;

    if (targets.length === 0) {
      list.innerHTML = '<div style="color: var(--text-slate); padding: 16px; font-family: var(--font-mono); text-align: center;">Airspace clear. No live ADB doors detected.</div>';
      return;
    }

    list.innerHTML = '';
    targets.forEach((t) => {
      const card = document.createElement('div');
      card.className = 'target-card';

      const badgeColor = t.class === 'OPEN_ADB' ? 'var(--emerald)' :
                         t.class === 'PAIRING_DIALOG' ? 'var(--amber)' :
                         t.class === 'STLS' ? '#c084fc' : 'var(--text-slate)';

      card.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="color: ${badgeColor}; font-weight: 600;">[${t.class || 'ADB'}]</span>
          <span style="color: var(--text-bone); font-weight: 500;">${t.ip}:${t.port}</span>
          ${t.model ? `<span style="color: var(--text-slate); font-size: 11px;">(${t.model})</span>` : ''}
        </div>
        <button class="action-pill" style="padding: 4px 12px; font-size: 11px;" onclick="Radar.engage('${t.ip}', ${t.port})">
          Engage
        </button>
      `;

      list.appendChild(card);
    });
  }

  async function engage(ip, port) {
    pushFlow('STRIKE', `Engaging target ${ip}:${port}...`);
    try {
      const res = await api('/api/ghost/hunter/engage', {
        method: 'POST',
        body: JSON.stringify({ ip, port })
      });

      if (res.success) {
        pushFlow('HIT', `Target ${ip}:${port} engaged successfully: ${res.vector || 'walk-in'}`);
        pollDevices();
      } else {
        pushFlow('ALERT', `Engagement failed: ${res.error || 'Door refused'}`);
      }
    } catch (e) {
      pushFlow('ALERT', `Engagement error: ${e.message}`);
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
        clearInterval(qrPollTimer);
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
        clearInterval(qrPollTimer);
      }
    } catch (e) {}
  }

  return {
    triggerSweep,
    engage,
    startQrPairing
  };
})();
