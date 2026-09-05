// ============================================================
// DroidCommand PWA // The Glass (Device Screen & Interaction)
// Real-time touch, drag, swipe, and hardware key controls
// ============================================================

window.Glass = (function () {
  let isStreaming = false;
  let streamTimer = null;
  let deviceResolution = { width: 720, height: 1600 };

  const viewport = document.getElementById('phoneViewport');
  const img = document.getElementById('deviceGlassImg');
  const emptyState = document.getElementById('glassEmptyState');
  const streamBtn = document.getElementById('toggleStreamBtn');

  // Pointer gesture tracking
  let pointerActive = false;
  let pointerStart = null;
  let gestureTrailEl = null;

  async function updateResolution() {
    try {
      const serial = STATE.activeSerial;
      const q = serial ? `?serial=${encodeURIComponent(serial)}` : '';
      const res = await api(`/api/screen/size${q}`);
      if (res.success && res.output) {
        const m = res.output.match(/(\d+)x(\d+)/);
        if (m) {
          deviceResolution.width = parseInt(m[1]);
          deviceResolution.height = parseInt(m[2]);
        }
      }
    } catch (e) {}
  }

  let frameInFlight = false;  // fix: single-flight — slow frames never stack
  let frameBacklog = false;   // fix: trailing request coalesced while in flight
  let frameReady = false;     // fix: gestures stay inert until the first frame paints

  async function fetchFrame() {
    if (!img) return;
    if (frameInFlight) { frameBacklog = true; return; }
    if (!STATE.devices || STATE.devices.length === 0) {
      showEmptyState(true);
      return;
    }

    frameInFlight = true;
    try {
      const serial = STATE.activeSerial;
      const q = serial ? `?serial=${encodeURIComponent(serial)}` : '';
      const token = window.__DC_TOKEN__ || '';

      const res = await fetch(`/api/screen/frame${q}`, {
        headers: { 'X-API-Token': token }
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        img.onload = () => {
          URL.revokeObjectURL(url);
          frameReady = true;
          if (img.naturalWidth && img.naturalHeight) {
            deviceResolution.width = img.naturalWidth;
            deviceResolution.height = img.naturalHeight;
          }
        };
        img.src = url;
        showEmptyState(false);
      } else {
        showEmptyState(true);
      }
    } catch (e) {
      showEmptyState(true);
    } finally {
      frameInFlight = false;
      if (frameBacklog) {
        frameBacklog = false;
        fetchFrame();
      }
    }
  }

  function showEmptyState(show) {
    if (!img) return;  // fix: element guard — one missing node must not throw every tick
    if (show) {
      img.style.display = 'none';
      if (emptyState) emptyState.style.display = 'flex';
    } else {
      img.style.display = 'block';
      if (emptyState) emptyState.style.display = 'none';
    }
  }

  let frameRefreshTimer = null;
  function scheduleFrameRefresh(delay) {
    // fix: single trailing refresh — rapid taps never stack setTimeout fetches
    if (frameRefreshTimer) clearTimeout(frameRefreshTimer);
    frameRefreshTimer = setTimeout(() => { frameRefreshTimer = null; fetchFrame(); }, delay);
  }

  function pumpFrame() {
    // fix: skip painting while the tab is hidden — the wire rests with the operator
    if (!document.hidden) fetchFrame();
  }

  function toggleStream() {
    isStreaming = !isStreaming;
    if (isStreaming) {
      if (streamBtn) {
        streamBtn.textContent = 'Pause Stream';
        streamBtn.classList.add('armed');
      }
      updateResolution();
      fetchFrame();
      if (streamTimer) clearInterval(streamTimer);  // fix: never double-arm the pump
      streamTimer = setInterval(pumpFrame, 750);
      pushFlow('INFO', 'Screen streaming initiated.');
    } else {
      if (streamBtn) {
        streamBtn.textContent = 'Start Stream';
        streamBtn.classList.remove('armed');
      }
      clearInterval(streamTimer);
      streamTimer = null;
      pushFlow('INFO', 'Screen streaming paused.');
    }
  }

  function onHide() {
    // fix: pause the frame pump whenever the glass deck loses the stage
    if (streamTimer) { clearInterval(streamTimer); streamTimer = null; }
  }

  function onShow() {
    if (isStreaming && !streamTimer && !document.hidden) {
      streamTimer = setInterval(pumpFrame, 750);
    }
    fetchFrame();
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) onHide(); else onShow();
  });

  // Calculate pixel-perfect device coordinates taking object-fit: contain into account
  function getDeviceCoordinates(clientX, clientY) {
    if (!img) return { devX: 0, devY: 0, clientX, clientY };

    const rect = img.getBoundingClientRect();
    const nw = img.naturalWidth || deviceResolution.width || 720;
    const nh = img.naturalHeight || deviceResolution.height || 1600;

    const elemRatio = rect.width / rect.height;
    const imgRatio = nw / nh;

    let renderW = rect.width;
    let renderH = rect.height;
    let offsetX = 0;
    let offsetY = 0;

    if (elemRatio > imgRatio) {
      renderW = rect.height * imgRatio;
      offsetX = (rect.width - renderW) / 2;
    } else {
      renderH = rect.width / imgRatio;
      offsetY = (rect.height - renderH) / 2;
    }

    const relX = clientX - rect.left - offsetX;
    const relY = clientY - rect.top - offsetY;

    const clampedX = Math.max(0, Math.min(renderW, relX));
    const clampedY = Math.max(0, Math.min(renderH, relY));

    const devX = Math.round((clampedX / renderW) * nw);
    const devY = Math.round((clampedY / renderH) * nh);

    return { devX, devY, clientX, clientY };
  }

  function onPointerDown(e) {
    if (!img || img.style.display === 'none') return;
    if (!frameReady) return;  // fix: no gestures against a placeholder resolution
    e.preventDefault();

    pointerActive = true;
    const coords = getDeviceCoordinates(e.clientX, e.clientY);
    pointerStart = {
      ...coords,
      time: Date.now()
    };

    try {
      img.setPointerCapture(e.pointerId);
    } catch (err) {}
  }

  function onPointerMove(e) {
    if (!pointerActive || !pointerStart) return;
    e.preventDefault();
  }

  async function onPointerUp(e) {
    if (!pointerActive || !pointerStart) return;
    e.preventDefault();
    pointerActive = false;

    try {
      img.releasePointerCapture(e.pointerId);
    } catch (err) {}

    const pointerEnd = getDeviceCoordinates(e.clientX, e.clientY);
    const dx = pointerEnd.devX - pointerStart.devX;
    const dy = pointerEnd.devY - pointerStart.devY;
    const dist = Math.hypot(dx, dy);
    const duration = Math.max(100, Math.min(600, Date.now() - pointerStart.time));

    if (dist < 18) {
      // Single Tap
      createTouchRipple(pointerStart.clientX, pointerStart.clientY);
      try {
        await api('/api/screen/tap', {
          method: 'POST',
          body: JSON.stringify({
            x: pointerStart.devX,
            y: pointerStart.devY,
            serial: STATE.activeSerial
          })
        });
        scheduleFrameRefresh(300);
      } catch (err) {
        console.warn('Tap error:', err);
      }
    } else {
      // Drag / Swipe Gesture
      createSwipeTrail(pointerStart.clientX, pointerStart.clientY, pointerEnd.clientX, pointerEnd.clientY);
      try {
        await api('/api/screen/swipe', {
          method: 'POST',
          body: JSON.stringify({
            x1: pointerStart.devX,
            y1: pointerStart.devY,
            x2: pointerEnd.devX,
            y2: pointerEnd.devY,
            duration: duration,
            serial: STATE.activeSerial
          })
        });
        scheduleFrameRefresh(400);
      } catch (err) {
        console.warn('Swipe error:', err);
      }
    }

    pointerStart = null;
  }

  function onPointerCancel(e) {
    pointerActive = false;
    pointerStart = null;
  }

  function createTouchRipple(clientX, clientY) {
    const ripple = document.createElement('div');
    ripple.className = 'touch-ripple';
    ripple.style.left = `${clientX}px`;
    ripple.style.top = `${clientY}px`;
    document.body.appendChild(ripple);
    setTimeout(() => ripple.remove(), 400);
  }

  function createSwipeTrail(x1, y1, x2, y2) {
    const trail = document.createElement('div');
    trail.className = 'swipe-trail';
    const length = Math.hypot(x2 - x1, y2 - y1);
    const angle = Math.atan2(y2 - y1, x2 - x1) * (180 / Math.PI);
    trail.style.left = `${x1}px`;
    trail.style.top = `${y1}px`;
    trail.style.width = `${length}px`;
    trail.style.transform = `rotate(${angle}deg)`;
    document.body.appendChild(trail);
    setTimeout(() => trail.remove(), 500);
  }

  // Quick Hardware & Gesture Helpers
  async function quickSwipeUp() {
    try {
      pushFlow('INFO', 'Performing lockscreen swipe-up unlock...');
      await api('/api/system/key', {
        method: 'POST',
        body: JSON.stringify({ code: 224, serial: STATE.activeSerial }) // KEYCODE_WAKEUP
      });
      await api('/api/screen/swipe', {
        method: 'POST',
        body: JSON.stringify({
          // fix: derive from real device resolution — no more hardcoded 720x1600
          x1: Math.round(deviceResolution.width / 2),
          y1: Math.round(deviceResolution.height * 0.8),
          x2: Math.round(deviceResolution.width / 2),
          y2: Math.round(deviceResolution.height * 0.18),
          duration: 250,
          serial: STATE.activeSerial
        })
      });
      scheduleFrameRefresh(400);
    } catch (e) {
      pushFlow('ALERT', 'Swipe up failed');
    }
  }

  async function sendKey(keyCode) {
    try {
      await api('/api/system/key', {
        method: 'POST',
        body: JSON.stringify({
          code: keyCode,
          serial: STATE.activeSerial
        })
      });
      scheduleFrameRefresh(400);
    } catch (e) {
      pushFlow('ALERT', `Keyevent ${keyCode} failed`);
    }
  }

  async function typeText() {
    const input = prompt('Enter text to type onto device:');
    if (!input) return;
    const text = input.slice(0, 512);  // fix: cap — prompt() is uncapped
    try {
      await api('/api/screen/text', {
        method: 'POST',
        body: JSON.stringify({
          text: text,
          serial: STATE.activeSerial
        })
      });
      scheduleFrameRefresh(500);
    } catch (e) {
      pushFlow('ALERT', 'Type text failed');
    }
  }

  function triggerTouchVisual(devX, devY) {
    if (!img || img.style.display === 'none') return;
    const rect = img.getBoundingClientRect();
    const nw = img.naturalWidth || deviceResolution.width || 720;
    const nh = img.naturalHeight || deviceResolution.height || 1600;

    const scaleX = rect.width / nw;
    const scaleY = rect.height / nh;

    const screenX = rect.left + (devX * scaleX);
    const screenY = rect.top + (devY * scaleY);
    createTouchRipple(screenX, screenY);
  }

  // Setup interactive pointer listeners on screen element
  if (img) {
    img.setAttribute('draggable', 'false');
    img.addEventListener('pointerdown', onPointerDown);
    img.addEventListener('pointermove', onPointerMove);
    img.addEventListener('pointerup', onPointerUp);
    img.addEventListener('pointercancel', onPointerCancel);
    img.addEventListener('dragstart', (e) => e.preventDefault());
  }

  // Auto-fetch initial frame once device is discovered
  setTimeout(() => {
    updateResolution();
    fetchFrame();
  }, 1000);

  return {
    toggleStream,
    fetchFrame,
    quickSwipeUp,
    sendKey,
    typeText,
    triggerTouchVisual,
    onShow,
    onHide
  };
})();
