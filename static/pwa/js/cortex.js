// ============================================================
// DroidCommand PWA // Cortex (Vesper AI Engine & Chat)
// ============================================================

window.Cortex = (function () {
  let lastMessageCount = -1;

  async function sendMessage() {
    const input = document.getElementById('vesperChatInput');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    appendBubble('user', text);

    try {
      const res = await api('/api/brain/chat', {
        method: 'POST',
        body: JSON.stringify({ message: text })
      });

      if (res.success) {
        pushFlow('BRAIN', 'Vesper received transmission.');
        setTimeout(pollChat, 800);
      } else {
        appendBubble('vesper', `*Connection snag: ${res.error || res.message || 'Unknown error'}*`);
      }
    } catch (e) {
      appendBubble('vesper', `*Error communicating with brain: ${e.message}*`);
    }
  }

  async function pollChat() {
    try {
      const res = await api('/api/brain/chat');
      if (!res.success || !res.messages) return;

      if (res.messages.length !== lastMessageCount) {
        lastMessageCount = res.messages.length;
        renderMessages(res.messages);
      }
    } catch (e) {}
  }

  function renderMessages(messages) {
    const stream = document.getElementById('vesperChatStream');
    if (!stream) return;

    stream.innerHTML = '';
    if (messages.length === 0) {
      stream.innerHTML = `
        <div class="chat-bubble vesper">
          <div style="font-size: 11px; color: var(--text-slate); margin-bottom: 4px; font-family: var(--font-mono);">VESPER // RESIDENT CORTEX</div>
          Standing by, mon roi. Give me an objective, or we can recon the target together.
        </div>
      `;
      return;
    }

    messages.forEach((m) => {
      appendBubble(m.role === 'user' ? 'user' : 'vesper', m.content);
    });

    stream.scrollTop = stream.scrollHeight;
  }

  function appendBubble(role, content) {
    const stream = document.getElementById('vesperChatStream');
    if (!stream) return;

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;

    const senderTag = role === 'user' ? 'YOU' : 'VESPER';
    bubble.innerHTML = `
      <div style="font-size: 10px; color: var(--text-slate); margin-bottom: 4px; font-family: var(--font-mono); letter-spacing: 0.05em;">${senderTag}</div>
      <div>${escapeHtml(content).replace(/\n/g, '<br>')}</div>
    `;

    stream.appendChild(bubble);
    stream.scrollTop = stream.scrollHeight;
  }

  async function triggerMission() {
    const input = document.getElementById('missionObjectiveInput');
    if (!input) return;
    const objective = input.value.trim();
    if (!objective) return;

    input.value = '';
    pushFlow('BRAIN', `Deploying autonomous mission: "${objective}"`);

    try {
      const res = await api('/api/brain/task', {
        method: 'POST',
        body: JSON.stringify({ objective })
      });

      if (res.success) {
        pushFlow('HIT', 'Mission armed. Vesper taking control.');
      } else {
        pushFlow('ALERT', `Mission failed to arm: ${res.error || res.message}`);
      }
    } catch (e) {
      pushFlow('ALERT', `Mission error: ${e.message}`);
    }
  }

  // Adaptive heartbeat: 1s while a reply is pending (she's running),
  // 6s idle, zero while the tab is hidden. The wire breathes with her.
  let chatBusyUntil = 0;
  (async function chatHeartbeat() {
    if (document.hidden) {
      setTimeout(chatHeartbeat, 4000);
      return;
    }
    const cadence = Date.now() < chatBusyUntil ? 1000 : 6000;
    const before = lastMessageCount;
    await pollChat();
    if (lastMessageCount !== before) chatBusyUntil = 0; // reply landed, rest
    setTimeout(chatHeartbeat, cadence);
  })();
  setTimeout(pollChat, 1000);
  const _origSendMessage = sendMessage;
  sendMessage = async function () {
    chatBusyUntil = Date.now() + 120000; // expect work; poll fast until she answers
    await _origSendMessage();
  };

  return {
    sendMessage,
    triggerMission
  };
})();
