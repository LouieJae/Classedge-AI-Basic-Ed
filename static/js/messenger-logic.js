/* =============================================== */
/* Global Floating Chat System — Logic             */
/* =============================================== */
document.addEventListener('DOMContentLoaded', function() {
  const CURRENT_USER_ID = parseInt(document.body.getAttribute('data-current-user-id'));
  if (!CURRENT_USER_ID) return;

  // Skip on the inbox page to avoid duplicate WebSocket connections
  if (window.location.pathname.includes('social_media_inbox')) return;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const MAX_VISIBLE_HEADS = 3;
  const MAX_VISIBLE_WINDOWS = 3;
  const LS_KEY = 'fc_chat_heads';
  const LS_UNREAD_KEY = 'fc_unread';

  const FC_HEADS = {};    // { recipientId: { name, photo, unread, ws, isOnline, nextPage, loadingMore } }
  const FC_WINDOWS = {};  // { recipientId: windowElement }
  const FC_STATE = {};    // { recipientId: { replyTo: {id,message,sender_name}|null, editMsgId: number|null } }
  const FC_PROCESSED_IDS = new Set(); // track processed message IDs to prevent double-counting
  const FC_EMOJIS = ['😀','😂','😍','😢','😡','👍','👎','🔥','❤️','🎉','😎','🤔','😱','🥳','😴','🤗','😇','🤩','😜','👏','💪','🙏','✨','💯'];
  let FC_MOBILE_ACTIVE = null; // userId of the currently open fullscreen mobile window

  // =============== Audio Notification ===============
  const fcNotificationSound = new Audio('/static/audio/message-receive.wav');
  fcNotificationSound.volume = 0.5;
  let fcSoundMuted = localStorage.getItem('fc_sound_muted') === 'true';
  // Persist the unlocked state across page navigations so we don't have
  // to re-prime the audio on every sidebar click. The prime itself
  // briefly plays the bell at volume 0 to satisfy browser autoplay
  // policies, but persisting the success means it only happens once
  // per browser session at most — never on every menu change.
  let fcAudioUnlocked = sessionStorage.getItem('cl_audio_unlocked') === '1';

  function fcUnlockAudio() {
    if (fcAudioUnlocked) {
      document.removeEventListener('click', fcUnlockAudio);
      document.removeEventListener('keydown', fcUnlockAudio);
      return;
    }
    // Mute the prime so the silent "tick" of play()/pause() doesn't
    // leak even on slow browsers that play a frame or two before pause.
    const restoreVolume = fcNotificationSound.volume;
    fcNotificationSound.volume = 0;
    fcNotificationSound.play().then(() => {
      fcNotificationSound.pause();
      fcNotificationSound.currentTime = 0;
      fcNotificationSound.volume = restoreVolume;
      fcAudioUnlocked = true;
      try { sessionStorage.setItem('cl_audio_unlocked', '1'); } catch (e) {}
      document.removeEventListener('click', fcUnlockAudio);
      document.removeEventListener('keydown', fcUnlockAudio);
    }).catch(() => {
      fcNotificationSound.volume = restoreVolume;
    });
  }
  if (!fcAudioUnlocked) {
    document.addEventListener('click', fcUnlockAudio);
    document.addEventListener('keydown', fcUnlockAudio);
  }

  // Shared sounded-IDs ring buffer in localStorage so this dedup
  // also covers ID's sounded by inbox-logic.js before the user
  // navigated to a different menu — otherwise the bell rings again
  // on the new page for a message you already heard on the inbox.
  const FC_SOUNDED_LS = 'cl_sounded_message_ids';
  function _fcReadSoundedIds() {
    try {
      const raw = localStorage.getItem(FC_SOUNDED_LS);
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function _fcWriteSoundedIds(arr) {
    try { localStorage.setItem(FC_SOUNDED_LS, JSON.stringify(arr.slice(-400))); } catch (e) {}
  }
  function _fcHasSoundedId(id) {
    if (!id) return false;
    return _fcReadSoundedIds().indexOf(String(id)) !== -1;
  }
  function _fcRememberSoundedId(id) {
    if (!id) return;
    const ids = _fcReadSoundedIds();
    const key = String(id);
    if (ids.indexOf(key) === -1) {
      ids.push(key);
      _fcWriteSoundedIds(ids);
    }
  }

  function fcPlayNotification(userId, messageId) {
    if (fcSoundMuted) return;
    // Dedup: skip if sound was already played for this message —
    // covers both in-memory (same page) and cross-page (different
    // menu) repeats.
    if (messageId) {
      if (FC_PROCESSED_IDS.has('sound_' + messageId)) return;
      if (_fcHasSoundedId(messageId)) {
        FC_PROCESSED_IDS.add('sound_' + messageId);
        return;
      }
      FC_PROCESSED_IDS.add('sound_' + messageId);
      _fcRememberSoundedId(messageId);
      if (FC_PROCESSED_IDS.size > 1000) {
        const first = FC_PROCESSED_IDS.values().next().value;
        FC_PROCESSED_IDS.delete(first);
      }
    }
    // Skip if the chat window for this user is visible and the tab is focused
    if (document.hasFocus() && FC_WINDOWS[userId] && FC_WINDOWS[userId].style.display !== 'none') return;
    fcNotificationSound.currentTime = 0;
    fcNotificationSound.play().catch(() => {});
  }

  function fcToggleMute() {
    fcSoundMuted = !fcSoundMuted;
    localStorage.setItem('fc_sound_muted', fcSoundMuted);
    return fcSoundMuted;
  }
  // Expose toggle globally for external UI
  window.fcToggleMute = fcToggleMute;
  window.fcIsMuted = () => fcSoundMuted;

  function _fcIsMobile() {
    return window.innerWidth <= 768;
  }

  const headsContainer = document.getElementById('fc-heads');
  const windowsContainer = document.getElementById('fc-windows');

  // =============== localStorage helpers ===============
  function saveHeadsToStorage() {
    const entries = {};
    Object.keys(FC_HEADS).forEach(uid => {
      const h = FC_HEADS[uid];
      entries[uid] = { name: h.name, photo: h.photo, windowOpen: !!FC_WINDOWS[uid] && FC_WINDOWS[uid].style.display !== 'none' };
    });
    try { localStorage.setItem(LS_KEY, JSON.stringify(entries)); } catch(e) {}
  }

  function loadHeadsFromStorage() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch(e) { return {}; }
  }

  function saveUnreadToStorage() {
    const counts = {};
    Object.keys(FC_HEADS).forEach(uid => {
      if (FC_HEADS[uid].unread > 0) counts[uid] = FC_HEADS[uid].unread;
    });
    try { localStorage.setItem(LS_UNREAD_KEY, JSON.stringify(counts)); } catch(e) {}
  }

  function loadUnreadFromStorage() {
    try {
      const raw = localStorage.getItem(LS_UNREAD_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch(e) { return {}; }
  }

  // =============== Hook into navbar notify WS ===============
  window._fcHandleNotify = function(data) {
    if (data.type === 'notify_message') {
      handleIncomingNotification(data);
    }
  };

  function handleIncomingNotification(data) {
    const senderId = parseInt(data.sender_id);
    const senderName = data.sender_name || 'User';

    // If we already have a chat head with an active WS, the chat WS handler
    // will manage the unread count — skip here to avoid double-counting.
    if (FC_HEADS[senderId]) {
      FC_HEADS[senderId].lastActivity = Date.now();
      if (FC_HEADS[senderId].ws && FC_HEADS[senderId].ws.readyState === WebSocket.OPEN) {
        // Chat WS is connected; it will handle unread increment
        renderAllHeads();
        return;
      }
      // No active chat WS — increment here
      if (_fcIsWindowActive(senderId)) {
        renderAllHeads();
        return;
      }
      FC_HEADS[senderId].unread = (FC_HEADS[senderId].unread || 0) + 1;
      fcPlayNotification(senderId, data.message_id);
      renderAllHeads();
      saveUnreadToStorage();
      return;
    }

    // New sender — fetch photo then create head
    fetch(`/social/friend/friends/`)
      .then(r => r.json())
      .then(friends => {
        const friend = friends.find(f => f.id === senderId);
        const photo = friend ? friend.photo : null;
        createChatHead(senderId, senderName, photo || '/static/assets/img/def_user.jpg', 1);
        fcPlayNotification(senderId, data.message_id);
      })
      .catch(() => {
        createChatHead(senderId, senderName, '/static/assets/img/def_user.jpg', 1);
        fcPlayNotification(senderId, data.message_id);
      });
  }

  // Check if a chat window is currently active and the user is looking at it
  function _fcIsWindowActive(userId) {
    return FC_WINDOWS[userId]
      && FC_WINDOWS[userId].style.display !== 'none'
      && !document.hidden;
  }

  // =============== Chat Head CRUD ===============
  function createChatHead(userId, name, photo, unread, skipSave) {
    if (FC_HEADS[userId]) return;
    FC_HEADS[userId] = {
      name: name,
      photo: photo,
      unread: unread || 0,
      isOnline: false,
      ws: null,
      lastActivity: Date.now()
    };
    renderAllHeads();
    if (!skipSave) {
      saveHeadsToStorage();
      saveUnreadToStorage();
    }
  }

  // =============== Render all heads with overflow ===============
  function renderAllHeads() {
    headsContainer.innerHTML = '';

    const allIds = Object.keys(FC_HEADS).map(Number);
    if (!allIds.length) return;

    // On mobile, start collapsed (only first head visible)
    if (_fcIsMobile() && allIds.length > 1 && !headsContainer.classList.contains('fc-heads-expanded')) {
      headsContainer.classList.add('fc-heads-collapsed');
    }

    // Sort: most recently active first (by lastActivity timestamp)
    allIds.sort((a, b) => (FC_HEADS[b].lastActivity || 0) - (FC_HEADS[a].lastActivity || 0));
    const visibleIds = allIds.slice(0, MAX_VISIBLE_HEADS);
    const overflowIds = allIds.slice(MAX_VISIBLE_HEADS);

    // Render visible heads
    visibleIds.forEach(uid => renderSingleHead(uid));

    // Render "More" bubble if overflow
    if (overflowIds.length > 0) {
      renderMoreBubble(overflowIds);
    }
  }

  function renderSingleHead(userId) {
    const data = FC_HEADS[userId];
    if (!data) return;

    const el = document.createElement('div');
    el.id = `fc-head-${userId}`;
    el.className = 'fc-head';
    el.addEventListener('click', (e) => {
      if (e.target.closest('.fc-close-head')) return;

      // Mobile stack behavior
      if (_fcIsMobile() && headsContainer.classList.contains('fc-heads-collapsed')) {
        // First click on collapsed stack: expand it
        headsContainer.classList.remove('fc-heads-collapsed');
        headsContainer.classList.add('fc-heads-expanded');
        return;
      }

      // On mobile, collapse the stack after selecting a head
      if (_fcIsMobile()) {
        headsContainer.classList.remove('fc-heads-expanded');
        headsContainer.classList.add('fc-heads-collapsed');
      }

      toggleWindow(userId);
    });

    el.innerHTML = `
      <img src="${data.photo}" alt="${data.name}" title="${data.name}">
      ${data.isOnline ? '<span class="fc-online-dot"></span>' : ''}
      ${data.unread > 0 ? `<span class="unread-badge">${data.unread > 9 ? '9+' : data.unread}</span>` : ''}
      <span class="fc-close-head" onclick="event.stopPropagation(); window._fcRemoveHead(${userId})" title="Close">&times;</span>
    `;

    headsContainer.appendChild(el);
  }

  function renderMoreBubble(overflowIds) {
    const totalOverflowUnread = overflowIds.reduce((sum, uid) => sum + (FC_HEADS[uid]?.unread || 0), 0);

    const bubble = document.createElement('div');
    bubble.className = 'fc-more-bubble';
    bubble.id = 'fc-more-bubble';
    bubble.innerHTML = `+${overflowIds.length}`;

    // Badge on the more bubble if any overflow user has unread
    if (totalOverflowUnread > 0) {
      const badge = document.createElement('span');
      badge.className = 'unread-badge';
      badge.style.position = 'absolute';
      badge.style.top = '-4px';
      badge.style.right = '-4px';
      badge.textContent = totalOverflowUnread > 9 ? '9+' : totalOverflowUnread;
      bubble.appendChild(badge);
    }

    // Dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'fc-more-dropdown';
    dropdown.id = 'fc-more-dropdown';

    overflowIds.forEach(uid => {
      const h = FC_HEADS[uid];
      if (!h) return;
      const item = document.createElement('div');
      item.className = 'fc-more-item';

      item.innerHTML = `
        <img src="${h.photo}" alt="${h.name}">
        <span class="fc-more-name">${h.name}</span>
        ${h.unread > 0 ? `<span class="fc-more-badge">${h.unread > 9 ? '9+' : h.unread}</span>` : ''}
        <button class="fc-more-close" onclick="event.stopPropagation(); window._fcRemoveHead(${uid})" title="Remove">&times;</button>
      `;

      item.addEventListener('click', (e) => {
        if (e.target.closest('.fc-more-close')) return;
        dropdown.classList.remove('show');
        toggleWindow(uid);
      });

      dropdown.appendChild(item);
    });

    bubble.appendChild(dropdown);

    bubble.addEventListener('click', (e) => {
      if (e.target.closest('.fc-more-item') || e.target.closest('.fc-more-close')) return;
      dropdown.classList.toggle('show');
    });

    headsContainer.appendChild(bubble);
  }

  // Close more dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#fc-more-bubble')) {
      const dd = document.getElementById('fc-more-dropdown');
      if (dd) dd.classList.remove('show');
    }
  });

  // =============== Remove head ===============
  window._fcRemoveHead = function(userId) {
    // Close WebSocket
    if (FC_HEADS[userId] && FC_HEADS[userId].ws) {
      FC_HEADS[userId].ws.close();
    }
    // Clean up mobile fullscreen
    if (FC_MOBILE_ACTIVE === userId) {
      FC_MOBILE_ACTIVE = null;
    }
    // Remove window
    if (FC_WINDOWS[userId]) {
      FC_WINDOWS[userId].remove();
      delete FC_WINDOWS[userId];
    }
    delete FC_HEADS[userId];
    delete FC_STATE[userId];
    renderAllHeads();
    saveHeadsToStorage();
    saveUnreadToStorage();
  };

  // =============== Enforce max visible windows ===============
  function enforceMaxWindows(excludeUserId) {
    const visibleIds = Object.keys(FC_WINDOWS).filter(uid => {
      return FC_WINDOWS[uid] && FC_WINDOWS[uid].style.display !== 'none';
    }).map(Number);

    // If within limit, nothing to do
    if (visibleIds.length <= MAX_VISIBLE_WINDOWS) return;

    // Minimize the oldest visible windows (those opened first, excluding the one just opened)
    const toMinimize = visibleIds.filter(uid => uid !== excludeUserId);
    while (toMinimize.length > 0 && Object.keys(FC_WINDOWS).filter(uid =>
      FC_WINDOWS[uid] && FC_WINDOWS[uid].style.display !== 'none'
    ).length > MAX_VISIBLE_WINDOWS) {
      const oldest = toMinimize.shift();
      if (FC_WINDOWS[oldest]) {
        FC_WINDOWS[oldest].style.display = 'none';
      }
    }
    saveHeadsToStorage();
  }

  // =============== Toggle / Open window ===============
  function toggleWindow(userId) {
    if (_fcIsMobile()) {
      // Mobile: only one window at a time, fullscreen
      if (FC_MOBILE_ACTIVE && FC_MOBILE_ACTIVE !== userId && FC_WINDOWS[FC_MOBILE_ACTIVE]) {
        // Hide the currently active mobile window
        const prevWin = FC_WINDOWS[FC_MOBILE_ACTIVE];
        prevWin.style.display = 'none';
        prevWin.classList.remove('fc-mobile-fullscreen');
        // Move it back into the windows container
        windowsContainer.appendChild(prevWin);
      }

      if (FC_WINDOWS[userId]) {
        const win = FC_WINDOWS[userId];
        if (win.style.display === 'none' || FC_MOBILE_ACTIVE !== userId) {
          // Show fullscreen
          win.style.display = 'flex';
          win.classList.add('fc-mobile-fullscreen');
          document.body.appendChild(win);
          FC_MOBILE_ACTIVE = userId;
          FC_HEADS[userId].unread = 0;
          renderAllHeads();
          scrollToBottom(userId);
          markAsRead(userId);
          saveUnreadToStorage();
          saveHeadsToStorage();
        } else {
          // Already visible — close it (back to heads)
          _fcMobileBack(userId);
        }
        return;
      }
      // Window doesn't exist yet — create it
      openWindow(userId);
      return;
    }

    // Desktop behavior
    if (FC_WINDOWS[userId]) {
      const win = FC_WINDOWS[userId];
      if (win.style.display === 'none') {
        win.style.display = 'flex';
        enforceMaxWindows(userId);
        FC_HEADS[userId].unread = 0;
        renderAllHeads();
        scrollToBottom(userId);
        markAsRead(userId);
        saveUnreadToStorage();
        saveHeadsToStorage();
      } else {
        win.style.display = 'none';
        saveHeadsToStorage();
      }
      return;
    }
    openWindow(userId);
  }

  function openWindow(userId) {
    const data = FC_HEADS[userId];
    if (!data) return;

    // Reset unread on open
    data.unread = 0;
    renderAllHeads();
    saveUnreadToStorage();

    const win = document.createElement('div');
    win.className = 'fc-window';
    win.id = `fc-window-${userId}`;
    win.innerHTML = `
      <div class="fc-window-header">
        <button class="fc-back-btn" onclick="window._fcMobileBack(${userId})" title="Back"><i class="fas fa-arrow-left"></i></button>
        <img src="${data.photo}" alt="${data.name}">
        <div class="fc-header-info">
          <div class="fc-header-name">${data.name}</div>
          <div class="fc-header-status" id="fc-status-${userId}">${data.isOnline ? 'Active Now' : ''}</div>
        </div>
        <div class="fc-header-actions">
          <button onclick="window._fcMinimize(${userId})" title="Minimize"><i class="fas fa-minus"></i></button>
          <button onclick="window._fcRemoveHead(${userId})" title="Close"><i class="fas fa-times"></i></button>
        </div>
      </div>
      <div class="fc-body-wrapper">
        <div class="fc-window-body" id="fc-body-${userId}">
          <div class="fc-loading"><i class="fas fa-spinner fa-spin me-2"></i> Loading...</div>
        </div>
        <div class="typing-indicator" id="fc-typing-${userId}"></div>
      </div>
      <div class="fc-file-preview" id="fc-file-preview-${userId}"></div>
      <div class="fc-reply-preview" id="fc-reply-preview-${userId}">
        <div class="fc-reply-preview-thumb" id="fc-reply-thumb-${userId}"></div>
        <div class="fc-reply-preview-body">
          <div class="fc-reply-preview-name" id="fc-reply-name-${userId}"></div>
          <div class="fc-reply-preview-text" id="fc-reply-text-${userId}"></div>
        </div>
        <button class="fc-reply-preview-close" id="fc-reply-cancel-${userId}" title="Cancel reply">&times;</button>
      </div>
      <div class="fc-edit-indicator" id="fc-edit-indicator-${userId}">
        <i class="fas fa-pen"></i> <span>Editing message</span>
        <button class="fc-edit-cancel" id="fc-edit-cancel-${userId}" title="Cancel edit">&times;</button>
      </div>
      <div class="fc-window-footer" id="fc-footer-${userId}">
        <div class="fc-emoji-picker" id="fc-emoji-picker-${userId}">
          ${FC_EMOJIS.map(e => `<span data-emoji="${e}">${e}</span>`).join('')}
        </div>
        <input type="file" id="fc-file-input-${userId}" multiple style="display:none">
        <button id="fc-attach-btn-${userId}" title="Attach file"><i class="fas fa-paperclip"></i></button>
        <button id="fc-emoji-btn-${userId}" title="Emoji"><i class="far fa-smile"></i></button>
        <input type="text" id="fc-input-${userId}" placeholder="Aa" autocomplete="off">
        <button onclick="window._fcSendLike(${userId})" id="fc-like-btn-${userId}" title="Like"><i class="fas fa-thumbs-up"></i></button>
        <button onclick="window._fcSendMsg(${userId})" id="fc-send-btn-${userId}" title="Send" style="display:none"><i class="fas fa-paper-plane"></i></button>
      </div>
    `;
    windowsContainer.appendChild(win);
    FC_WINDOWS[userId] = win;
    FC_STATE[userId] = { replyTo: null, editMsgId: null };
    enforceMaxWindows(userId);
    saveHeadsToStorage();

    // Input enter key
    const input = document.getElementById(`fc-input-${userId}`);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        window._fcSendMsg(userId);
      }
    });

    // Reset unread badge when user clicks into the input field
    input.addEventListener('focus', () => {
      if (FC_HEADS[userId] && FC_HEADS[userId].unread > 0) {
        FC_HEADS[userId].unread = 0;
        renderAllHeads();
        saveUnreadToStorage();
        markAsRead(userId);
      }
    });

    // Typing indicator
    let typingTimeout = null;
    input.addEventListener('input', () => {
      if (FC_HEADS[userId] && FC_HEADS[userId].ws && FC_HEADS[userId].ws.readyState === WebSocket.OPEN) {
        FC_HEADS[userId].ws.send(JSON.stringify({ type: 'typing' }));
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => {
          if (FC_HEADS[userId] && FC_HEADS[userId].ws && FC_HEADS[userId].ws.readyState === WebSocket.OPEN) {
            FC_HEADS[userId].ws.send(JSON.stringify({ type: 'stop_typing' }));
          }
        }, 2000);
      }
    });

    // Emoji picker (native Unicode, synced with inbox)
    const emojiPicker = document.getElementById(`fc-emoji-picker-${userId}`);
    const emojiBtn = document.getElementById(`fc-emoji-btn-${userId}`);
    emojiBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      emojiPicker.classList.toggle('show');
    });
    emojiPicker.addEventListener('click', (e) => {
      const span = e.target.closest('[data-emoji]');
      if (span) {
        const emoji = span.dataset.emoji;
        const start = input.selectionStart || input.value.length;
        const end = input.selectionEnd || input.value.length;
        input.value = input.value.substring(0, start) + emoji + input.value.substring(end);
        const newPos = start + emoji.length;
        input.setSelectionRange(newPos, newPos);
        input.focus();
        emojiPicker.classList.remove('show');
      }
    });
    document.addEventListener('click', (e) => {
      if (!emojiPicker.contains(e.target) && !emojiBtn.contains(e.target)) {
        emojiPicker.classList.remove('show');
      }
    });

    // Reply cancel
    document.getElementById(`fc-reply-cancel-${userId}`).addEventListener('click', () => _fcCancelReply(userId));

    // Edit cancel
    document.getElementById(`fc-edit-cancel-${userId}`).addEventListener('click', () => _fcCancelEdit(userId));

    // Toggle send/like button based on input content
    input.addEventListener('input', function() {
      const sendBtn = document.getElementById(`fc-send-btn-${userId}`);
      const likeBtn = document.getElementById(`fc-like-btn-${userId}`);
      if (input.value.trim().length > 0) {
        sendBtn.style.display = '';
        likeBtn.style.display = 'none';
      } else if (!FC_STATE[userId] || !FC_STATE[userId].editMsgId) {
        sendBtn.style.display = 'none';
        likeBtn.style.display = '';
      }
    });

    // File attachment
    const fileInput = document.getElementById(`fc-file-input-${userId}`);
    const attachBtn = document.getElementById(`fc-attach-btn-${userId}`);
    const filePreview = document.getElementById(`fc-file-preview-${userId}`);

    attachBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      const footer = document.getElementById(`fc-footer-${userId}`);
      if (!file) {
        filePreview.innerHTML = '';
        filePreview.classList.remove('show');
        if (footer) footer.classList.remove('has-attachment');
        _fcUpdateSendLike(userId);
        return;
      }
      // Immediately show send button and add attachment class
      if (footer) footer.classList.add('has-attachment');
      const sendBtn = document.getElementById(`fc-send-btn-${userId}`);
      const likeBtn = document.getElementById(`fc-like-btn-${userId}`);
      if (sendBtn) sendBtn.style.display = '';
      if (likeBtn) likeBtn.style.display = 'none';
      const forbidden = ['exe','bat','sh','cmd','js','jar','msi'];
      const ext = file.name.split('.').pop().toLowerCase();
      if (forbidden.includes(ext)) {
        alert(`File type .${ext} is not allowed.`);
        fileInput.value = '';
        filePreview.innerHTML = '';
        filePreview.classList.remove('show');
        if (footer) footer.classList.remove('has-attachment');
        _fcUpdateSendLike(userId);
        return;
      }
      const isImage = file.type.startsWith('image/');
      if (isImage) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          filePreview.innerHTML = `
            <img src="${ev.target.result}" alt="preview">
            <span class="fc-fp-name">${file.name}</span>
            <button class="fc-fp-remove" title="Remove">&times;</button>
          `;
          filePreview.classList.add('show');
          filePreview.querySelector('.fc-fp-remove').addEventListener('click', () => _fcClearFile(userId));
        };
        reader.readAsDataURL(file);
      } else {
        filePreview.innerHTML = `
          <span class="fc-fp-icon"><i class="fas fa-file"></i></span>
          <span class="fc-fp-name">${file.name}</span>
          <button class="fc-fp-remove" title="Remove">&times;</button>
        `;
        filePreview.classList.add('show');
        filePreview.querySelector('.fc-fp-remove').addEventListener('click', () => _fcClearFile(userId));
      }
    });

    // Infinite scroll (backread) — fetch older messages on scroll to top
    const body = document.getElementById(`fc-body-${userId}`);
    if (body) {
      body.addEventListener('scroll', () => {
        if (body.scrollTop === 0 && FC_HEADS[userId] && FC_HEADS[userId].nextPage && !FC_HEADS[userId].loadingMore) {
          loadOlderMessages(userId);
        }
      });
    }

    // Connect WebSocket and load messages
    connectChatWS(userId);
    loadMessages(userId);
    markAsRead(userId);

    // Mobile: make fullscreen immediately
    if (_fcIsMobile()) {
      win.classList.add('fc-mobile-fullscreen');
      document.body.appendChild(win);
      FC_MOBILE_ACTIVE = userId;
    }
  }

  // =============== Window actions ===============
  window._fcMobileBack = function(userId) {
    const win = FC_WINDOWS[userId];
    if (!win) return;
    win.style.display = 'none';
    win.classList.remove('fc-mobile-fullscreen');
    windowsContainer.appendChild(win);
    FC_MOBILE_ACTIVE = null;
    saveHeadsToStorage();
  };

  window._fcMinimize = function(userId) {
    if (_fcIsMobile()) {
      window._fcMobileBack(userId);
      return;
    }
    if (FC_WINDOWS[userId]) {
      FC_WINDOWS[userId].style.display = 'none';
      saveHeadsToStorage();
    }
  };

  function _fcClearFile(userId) {
    const fileInput = document.getElementById(`fc-file-input-${userId}`);
    const filePreview = document.getElementById(`fc-file-preview-${userId}`);
    const footer = document.getElementById(`fc-footer-${userId}`);
    if (fileInput) fileInput.value = '';
    if (filePreview) {
      filePreview.innerHTML = '';
      filePreview.classList.remove('show');
    }
    if (footer) footer.classList.remove('has-attachment');
  }

  window._fcSendMsg = function(userId) {
    const input = document.getElementById(`fc-input-${userId}`);
    const fileInput = document.getElementById(`fc-file-input-${userId}`);
    if (!input) return;

    const text = input.value.trim();
    const file = fileInput ? fileInput.files[0] : null;
    const state = FC_STATE[userId] || {};

    const ws = FC_HEADS[userId] ? FC_HEADS[userId].ws : null;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    // Edit mode: send edit_message event
    if (state.editMsgId) {
      if (!text) return;
      ws.send(JSON.stringify({ type: 'edit_message', message_id: state.editMsgId, message: text }));
      input.value = '';
      _fcCancelEdit(userId);
      return;
    }

    if (!text && !file) return;

    // Bump priority on send
    if (FC_HEADS[userId]) {
      FC_HEADS[userId].lastActivity = Date.now();
      renderAllHeads();
    }

    if (file) {
      const reader = new FileReader();
      reader.onload = function(ev) {
        const payload = {
          message: text || '',
          file: {
            name: file.name,
            type: file.type,
            data: ev.target.result
          }
        };
        if (state.replyTo) payload.reply_to = state.replyTo.id;
        ws.send(JSON.stringify(payload));
        input.value = '';
        _fcClearFile(userId);
        _fcCancelReply(userId);
        _fcUpdateSendLike(userId);
      };
      reader.readAsDataURL(file);
    } else {
      const payload = { message: text };
      if (state.replyTo) payload.reply_to = state.replyTo.id;
      ws.send(JSON.stringify(payload));
      input.value = '';
      _fcCancelReply(userId);
      _fcUpdateSendLike(userId);
    }
  };

  window._fcSendLike = function(userId) {
    const ws = FC_HEADS[userId] ? FC_HEADS[userId].ws : null;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ message: '👍' }));
    }
  };

  // =============== Chat WebSocket ===============
  function connectChatWS(userId) {
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat/${userId}/`);

    ws.onmessage = function(event) {
      const data = JSON.parse(event.data);

      // Silent update guard: reactions and unsend never trigger unread counts or notifications
      if (data.is_reaction || data.type === 'message_deleted') {
        if (data.type === 'reaction_added') {
          // Skip if this is the current user's own reaction — optimistic UI already applied
          if (parseInt(data.user_id) === CURRENT_USER_ID) return;
          const raRow = document.querySelector(`#fc-body-${userId} [data-msg-id="${data.message_id}"]`);
          if (raRow) {
            const raBubble = raRow.querySelector('.fc-msg');
            if (raBubble) {
              let reactions = _fcCollectReactions(raBubble);
              reactions = reactions.filter(r => r.user_id !== data.user_id);
              reactions.push({ emoji: data.emoji, user_id: data.user_id });
              _fcRenderReactions(raBubble, reactions, data.message_id);
            }
          }
          return;
        }
        if (data.type === 'reaction_removed') {
          // Skip if this is the current user's own reaction — optimistic UI already applied
          if (parseInt(data.user_id) === CURRENT_USER_ID) return;
          const rrRow = document.querySelector(`#fc-body-${userId} [data-msg-id="${data.message_id}"]`);
          if (rrRow) {
            const rrBubble = rrRow.querySelector('.fc-msg');
            if (rrBubble) {
              let reactions = _fcCollectReactions(rrBubble);
              reactions = reactions.filter(r => !(r.user_id === data.user_id && r.emoji === data.emoji));
              _fcRenderReactions(rrBubble, reactions, data.message_id);
            }
          }
          return;
        }
        if (data.type === 'message_deleted') {
          const delRow = document.querySelector(`#fc-body-${userId} [data-msg-id="${data.message_id}"]`);
          if (delRow) {
            const reactionsEl = delRow.querySelector('.fc-msg-reactions');
            if (reactionsEl) reactionsEl.remove();
            const bubble = delRow.querySelector('.fc-msg');
            if (bubble) {
              bubble.className = bubble.className.replace(/\bemoji-only\b|\bmedia-only\b/g, '').trim();
              bubble.classList.add('is-unsent');
              bubble.innerHTML = `<span style="font-style:italic;opacity:0.6;"><i class="fas fa-ban me-1"></i>Message unsent</span>`;
              bubble.style.marginBottom = '';
            }
            const actions = delRow.querySelector('.fc-msg-actions');
            if (actions) actions.remove();
            const replyQuote = delRow.querySelector('.fc-msg-reply-quote');
            if (replyQuote) replyQuote.remove();
          }
          return;
        }
        return;
      }

      if (data.type === 'chat_message') {
        const msgId = data.message_id;
        const isSent = parseInt(data.sender_id) === CURRENT_USER_ID;

        // Dedup: skip if this message ID was already processed
        if (msgId && FC_PROCESSED_IDS.has(msgId)) return;
        if (msgId) {
          FC_PROCESSED_IDS.add(msgId);
          // Cap the set size to prevent memory leaks
          if (FC_PROCESSED_IDS.size > 500) {
            const first = FC_PROCESSED_IDS.values().next().value;
            FC_PROCESSED_IDS.delete(first);
          }
        }

        appendMessage(userId, {
          id: msgId,
          message: data.message,
          isSent: isSent,
          time: data.formatted_time,
          file: data.file,
          is_image: data.is_image,
          sender_name: data.sender_name,
          reply_to: data.reply_to || null
        });
        scrollToBottom(userId);

        // Bump priority: move this head to the top
        if (FC_HEADS[userId]) {
          FC_HEADS[userId].lastActivity = Date.now();
        }

        // If window is active and tab is focused, mark as read; otherwise increment unread
        if (!isSent) {
          if (_fcIsWindowActive(userId)) {
            ws.send(JSON.stringify({ type: 'read_receipt' }));
          } else if (FC_HEADS[userId]) {
            FC_HEADS[userId].unread = (FC_HEADS[userId].unread || 0) + 1;
            fcPlayNotification(userId, msgId);
          }
        }
        renderAllHeads();
        saveUnreadToStorage();
      }

      if (data.type === 'typing') {
        const typingEl = document.getElementById(`fc-typing-${userId}`);
        if (!typingEl) return;
        const body = document.getElementById(`fc-body-${userId}`);
        // Clear any existing auto-hide timer
        if (FC_HEADS[userId] && FC_HEADS[userId]._typingTimer) {
          clearTimeout(FC_HEADS[userId]._typingTimer);
          FC_HEADS[userId]._typingTimer = null;
        }
        if (data.is_typing) {
          typingEl.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
          // Auto-scroll so dots are always visible
          if (body) body.scrollTop = body.scrollHeight;
          // Auto-hide after 3 seconds of inactivity
          if (FC_HEADS[userId]) {
            FC_HEADS[userId]._typingTimer = setTimeout(() => {
              typingEl.innerHTML = '';
            }, 3000);
          }
        } else {
          typingEl.innerHTML = '';
        }
      }

      if (data.type === 'presence_update') {
        const online = data.is_online;
        if (FC_HEADS[userId]) {
          FC_HEADS[userId].isOnline = online;
          renderAllHeads();
          const statusEl = document.getElementById(`fc-status-${userId}`);
          if (statusEl) statusEl.textContent = online ? 'Active Now' : '';
        }
      }

      if (data.type === 'message_edited') {
        const row = document.querySelector(`#fc-body-${userId} [data-msg-id="${data.message_id}"]`);
        if (row) {
          const textEl = row.querySelector('.fc-msg-text');
          if (textEl) textEl.textContent = data.new_message;
          // Update data attribute
          row.setAttribute('data-msg-text', data.new_message);
          // Add (edited) label if not already present
          if (!row.querySelector('.fc-msg-edited-label')) {
            const timeEl = row.querySelector('.fc-msg-time');
            if (timeEl) {
              const label = document.createElement('span');
              label.className = 'fc-msg-edited-label';
              label.textContent = '(edited)';
              timeEl.prepend(label);
            }
          }
        }
      }
    };

    ws.onclose = function() {
      setTimeout(() => {
        if (FC_HEADS[userId]) connectChatWS(userId);
      }, 3000);
    };

    if (FC_HEADS[userId]) {
      FC_HEADS[userId].ws = ws;
    }
  }

  // =============== Messages ===============
  function loadMessages(userId) {
    fetch(`/social/chat/?receiver=${userId}&page_size=20`)
      .then(r => r.json())
      .then(data => {
        const body = document.getElementById(`fc-body-${userId}`);
        if (!body) return;
        body.innerHTML = '';

        // Track next page URL for infinite scroll
        if (FC_HEADS[userId]) {
          FC_HEADS[userId].nextPage = data.next || null;
          FC_HEADS[userId].loadingMore = false;
        }

        const messages = data.results || data;
        if (!messages.length) {
          body.innerHTML = '<div class="fc-empty">No messages yet. Say hi!</div>';
          return;
        }

        const sorted = [...messages].reverse();
        sorted.forEach(msg => {
          appendMessage(userId, {
            id: msg.id,
            message: msg.is_deleted ? null : msg.message,
            isSent: msg.is_sent,
            time: msg.formatted_time,
            file: msg.is_deleted ? null : msg.file,
            is_image: msg.file ? /\.(jpg|jpeg|png|gif)$/i.test(msg.file) : false,
            isDeleted: msg.is_deleted,
            is_edited: msg.is_edited || false,
            sender_name: msg.sender_name,
            reply_to: msg.reply_to || null,
            reactions: msg.reactions || []
          });
        });

        scrollToBottom(userId);
      })
      .catch(() => {
        const body = document.getElementById(`fc-body-${userId}`);
        if (body) body.innerHTML = '<div class="fc-empty">Failed to load messages.</div>';
      });
  }

  function loadOlderMessages(userId) {
    const head = FC_HEADS[userId];
    if (!head || !head.nextPage || head.loadingMore) return;

    head.loadingMore = true;
    const body = document.getElementById(`fc-body-${userId}`);
    if (!body) { head.loadingMore = false; return; }

    // Show loading spinner at top
    const spinner = document.createElement('div');
    spinner.className = 'fc-loading';
    spinner.id = `fc-load-more-${userId}`;
    spinner.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Loading...';
    body.prepend(spinner);

    // Record scroll height before prepending
    const previousHeight = body.scrollHeight;

    // Ensure we fetch 20 messages per backread page
    let fetchUrl = head.nextPage;
    if (fetchUrl && !fetchUrl.includes('page_size=')) {
      fetchUrl += (fetchUrl.includes('?') ? '&' : '?') + 'page_size=20';
    }

    fetch(fetchUrl)
      .then(r => r.json())
      .then(data => {
        // Remove spinner
        const sp = document.getElementById(`fc-load-more-${userId}`);
        if (sp) sp.remove();

        // Track next page
        head.nextPage = data.next || null;
        head.loadingMore = false;

        const messages = data.results || data;
        if (!messages.length) return;

        // Messages are in reverse chronological order from API, so they are already oldest-last
        // We need to prepend them in chronological order (reverse the array)
        const sorted = [...messages].reverse();
        const fragment = document.createDocumentFragment();
        sorted.forEach(msg => {
          const div = buildMessageDiv(userId, {
            id: msg.id,
            message: msg.is_deleted ? null : msg.message,
            isSent: msg.is_sent,
            time: msg.formatted_time,
            file: msg.is_deleted ? null : msg.file,
            is_image: msg.file ? /\.(jpg|jpeg|png|gif)$/i.test(msg.file) : false,
            isDeleted: msg.is_deleted,
            is_edited: msg.is_edited || false,
            sender_name: msg.sender_name,
            reply_to: msg.reply_to || null,
            reactions: msg.reactions || []
          });
          fragment.appendChild(div);
        });

        // Prepend older messages
        body.prepend(fragment);

        // Lock scroll position: container.scrollTop = container.scrollHeight - previousHeight
        body.scrollTop = body.scrollHeight - previousHeight;
      })
      .catch(() => {
        const sp = document.getElementById(`fc-load-more-${userId}`);
        if (sp) sp.remove();
        head.loadingMore = false;
      });
  }

  // Regex to detect emoji-only messages (1-3 emojis, no other text)
  const EMOJI_ONLY_RE = /^(\p{Emoji_Presentation}|\p{Extended_Pictographic}){1,3}$/u;

  function buildMessageDiv(userId, msg) {
    // Outer row: flex container holding bubble + action icons
    const row = document.createElement('div');
    const direction = msg.isSent ? 'sent' : 'received';
    row.className = `fc-msg-row ${direction}`;
    row.setAttribute('data-msg-id', msg.id);
    if (msg.message) row.setAttribute('data-msg-text', msg.message);
    if (msg.sender_name) row.setAttribute('data-sender-name', msg.sender_name);

    // Column wrapper: holds reply-quote (if any) + bubble vertically
    const col = document.createElement('div');
    col.className = 'fc-msg-col';

    // Build reply quote element OUTSIDE the bubble
    let replyQuoteEl = null;
    if (!msg.isDeleted && msg.reply_to && (msg.reply_to.message || msg.reply_to.file)) {
      const rName = escapeHtml(msg.reply_to.sender_name || 'User');
      const rFile = msg.reply_to.file || null;
      const rIsImage = rFile && _fcIsImageUrl(rFile);
      let quoteBodyContent = '';

      if (rIsImage) {
        quoteBodyContent += `<img class="fc-reply-quote-thumb" src="${rFile}" alt="">`;
      } else if (rFile) {
        quoteBodyContent += `<i class="fas fa-file-alt fc-reply-quote-file-icon"></i>`;
      }

      const rText = msg.reply_to.message ? escapeHtml(msg.reply_to.message) : (rIsImage ? 'Photo' : (rFile ? rFile.split('/').pop() : ''));
      quoteBodyContent += `<div class="fc-msg-reply-quote-text">${rText}</div>`;

      replyQuoteEl = document.createElement('div');
      replyQuoteEl.className = 'fc-msg-reply-quote';
      replyQuoteEl.setAttribute('data-reply-id', msg.reply_to.id);
      replyQuoteEl.innerHTML =
        `<div class="fc-msg-reply-quote-label"><i class="fas fa-reply"></i> ${rName}</div>` +
        `<div class="fc-msg-reply-quote-body">${quoteBodyContent}</div>`;
      col.appendChild(replyQuoteEl);
    }

    // Bubble
    const bubble = document.createElement('div');
    let content = '';
    let isEmojiOnly = false;
    let isMediaOnly = false;

    if (msg.isDeleted) {
      isMediaOnly = false;
      isEmojiOnly = false;
      content = `<span style="font-style:italic;opacity:0.6;"><i class="fas fa-ban me-1"></i>Message unsent</span>`;
    } else {
      if (msg.file) {
        if (msg.is_image) {
          content += `<div class="fc-msg-file"><img src="${msg.file}" alt="Image" loading="lazy"></div>`;
        } else {
          const fname = msg.file.split('/').pop();
          const fileExt = fname.split('.').pop().toLowerCase();
          const iconCls = ['pdf'].includes(fileExt) ? 'fa-file-pdf' :
                          ['doc','docx'].includes(fileExt) ? 'fa-file-word' :
                          ['xls','xlsx'].includes(fileExt) ? 'fa-file-excel' :
                          ['ppt','pptx'].includes(fileExt) ? 'fa-file-powerpoint' :
                          ['zip','rar','7z'].includes(fileExt) ? 'fa-file-archive' : 'fa-file-alt';
          content += `<div class="fc-msg-file-doc">
            <i class="fas ${iconCls} fc-file-icon"></i>
            <span class="fc-file-name" title="${fname}">${fname}</span>
            <a href="${msg.file}" target="_blank" download class="fc-file-dl" title="Download"><i class="fas fa-download"></i></a>
          </div>`;
        }
        if (!msg.message) isMediaOnly = true;
      }
      if (msg.message) {
        const trimmed = msg.message.trim();
        if (!msg.file && EMOJI_ONLY_RE.test(trimmed)) {
          isEmojiOnly = true;
          content += `<span class="fc-msg-text">${trimmed}</span>`;
        } else {
          content += `<span class="fc-msg-text">${escapeHtml(msg.message)}</span>`;
        }
      }
    }

    let cls = `fc-msg ${direction}`;
    if (msg.isDeleted) cls += ' is-unsent';
    if (isEmojiOnly) cls += ' emoji-only';
    if (isMediaOnly) cls += ' media-only';
    bubble.className = cls;

    bubble.innerHTML = content;
    col.appendChild(bubble);

    // Inner wrapper: holds col + actions (actions are absolutely positioned)
    const inner = document.createElement('div');
    inner.className = 'fc-msg-inner';
    inner.appendChild(col);

    // Render reaction badges on bubble
    if (msg.reactions && msg.reactions.length > 0) {
      _fcRenderReactions(bubble, msg.reactions);
    }

    // Inline action icons (only for non-deleted messages)
    if (!msg.isDeleted) {
      const actions = document.createElement('div');
      actions.className = 'fc-msg-actions';

      // Reply icon
      const replyIcon = document.createElement('button');
      replyIcon.className = 'fc-msg-action-icon';
      replyIcon.title = 'Reply';
      replyIcon.innerHTML = '<i class="fas fa-reply"></i>';
      replyIcon.addEventListener('click', (e) => {
        e.stopPropagation();
        _fcStartReply(userId, msg);
      });
      actions.appendChild(replyIcon);

      // React icon (emoji reaction picker)
      const reactIcon = document.createElement('button');
      reactIcon.className = 'fc-msg-action-icon';
      reactIcon.title = 'React';
      reactIcon.innerHTML = '<i class="far fa-smile"></i>';
      reactIcon.addEventListener('click', (e) => {
        e.stopPropagation();
        _fcToggleReactionBar(userId, msg.id, row, reactIcon);
      });
      actions.appendChild(reactIcon);

      // Ellipsis icon — only for sender's own messages (Edit/Delete)
      if (msg.isSent) {
        const ellipsisIcon = document.createElement('button');
        ellipsisIcon.className = 'fc-msg-action-icon';
        ellipsisIcon.title = 'More';
        ellipsisIcon.innerHTML = '<i class="fas fa-ellipsis-h"></i>';
        ellipsisIcon.addEventListener('click', (e) => {
          e.stopPropagation();
          _fcShowMsgActions(userId, msg, actions, ellipsisIcon);
        });
        actions.appendChild(ellipsisIcon);
      }

      inner.appendChild(actions);
    }

    row.appendChild(inner);

    // Timestamp: outside bubble, direct child of row, shown on hover
    if (msg.time) {
      const timeEl = document.createElement('div');
      timeEl.className = 'fc-msg-time';
      timeEl.innerHTML = `${msg.is_edited ? '<span class="fc-msg-edited-label">(edited)</span> ' : ''}${msg.time}`;
      row.appendChild(timeEl);
    }

    // Click-to-expand lightbox for images
    const imgEl = bubble.querySelector('.fc-msg-file img');
    if (imgEl) {
      imgEl.addEventListener('click', (e) => {
        e.stopPropagation();
        _fcOpenLightbox(imgEl.src);
      });
    }

    // Click on quoted reply to scroll to original message
    const quoteEl = replyQuoteEl || col.querySelector('.fc-msg-reply-quote');
    if (quoteEl) {
      quoteEl.addEventListener('click', (e) => {
        e.stopPropagation();
        const replyId = quoteEl.getAttribute('data-reply-id');
        const target = document.querySelector(`#fc-body-${userId} [data-msg-id="${replyId}"]`);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'center' });
          target.style.transition = 'background 0.3s';
          target.style.background = 'rgba(0,132,255,0.12)';
          setTimeout(() => { target.style.background = ''; }, 1500);
        }
      });
    }

    // Mobile: toggle timestamp on click
    row.addEventListener('click', () => {
      row.classList.toggle('show-time');
    });

    // Mobile: long-press or tap on bubble to show action icons (no hover on touch)
    if (!msg.isDeleted) {
      let touchTimer = null;
      let touchMoved = false;

      bubble.addEventListener('touchstart', (e) => {
        touchMoved = false;
        touchTimer = setTimeout(() => {
          // Long-press: show actions and reaction bar
          e.preventDefault();
          _fcClearTouchActive();
          row.classList.add('fc-touch-active');
          // Also show reaction bar directly on long-press
          const actions = row.querySelector('.fc-msg-actions');
          if (actions) {
            _fcToggleReactionBar(userId, msg.id, row, actions.querySelector('.fc-msg-action-icon[title="React"]'));
          }
        }, 400);
      }, { passive: false });

      bubble.addEventListener('touchmove', () => {
        touchMoved = true;
        clearTimeout(touchTimer);
      });

      bubble.addEventListener('touchend', (e) => {
        clearTimeout(touchTimer);
        if (!touchMoved && !row.classList.contains('fc-touch-active')) {
          // Short tap: toggle action icons
          _fcClearTouchActive();
          row.classList.add('fc-touch-active');
        }
      });
    }

    return row;
  }

  // Clear all touch-active states on any message row
  function _fcClearTouchActive() {
    document.querySelectorAll('.fc-msg-row.fc-touch-active').forEach(r => {
      r.classList.remove('fc-touch-active');
    });
    // Also close any open reaction bars
    document.querySelectorAll('.fc-reaction-bar').forEach(b => b.remove());
  }

  // Global: tap outside a message row clears touch-active
  document.addEventListener('touchstart', (e) => {
    if (!e.target.closest('.fc-msg-row') && !e.target.closest('.fc-reaction-bar') && !e.target.closest('.fc-msg-actions-menu')) {
      _fcClearTouchActive();
    }
  });

  function appendMessage(userId, msg) {
    const body = document.getElementById(`fc-body-${userId}`);
    if (!body) return;

    // Dedup: skip if a message with this ID already exists
    if (msg.id && body.querySelector(`[data-msg-id="${msg.id}"]`)) return;

    const empty = body.querySelector('.fc-empty');
    if (empty) empty.remove();

    body.appendChild(buildMessageDiv(userId, msg));
  }

  // =============== Message Action Handlers ===============
  function _fcShowMsgActions(userId, msg, actionsContainer, ellipsisBtn) {
    // Remove any existing open menus
    document.querySelectorAll('.fc-msg-actions-menu.show').forEach(m => m.remove());

    const menu = document.createElement('div');
    menu.className = 'fc-msg-actions-menu show';

    // Edit — only for own text messages
    if (msg.isSent && msg.message) {
      const editBtn = document.createElement('button');
      editBtn.innerHTML = '<i class="fas fa-pen"></i> Edit';
      editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        menu.remove();
        _fcStartEdit(userId, msg);
      });
      menu.appendChild(editBtn);
    }

    // Unsend — only for own messages
    if (msg.isSent) {
      const delBtn = document.createElement('button');
      delBtn.className = 'fc-action-delete';
      delBtn.innerHTML = '<i class="fas fa-undo-alt"></i> Unsend';
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        menu.remove();
        _fcDeleteMsg(userId, msg.id);
      });
      menu.appendChild(delBtn);
    }

    // If no items (received message from other user), don't show empty menu
    if (menu.children.length === 0) return;

    // Append to .fc-msg-inner for reliable positioning
    const row = actionsContainer.closest('.fc-msg-row');
    const inner = row ? row.querySelector('.fc-msg-inner') : null;
    if (inner) {
      inner.appendChild(menu);
    } else {
      actionsContainer.appendChild(menu);
    }

    // Close menu on outside click
    const closeHandler = (e) => {
      if (!menu.contains(e.target) && e.target !== ellipsisBtn) {
        menu.remove();
        document.removeEventListener('click', closeHandler);
      }
    };
    setTimeout(() => document.addEventListener('click', closeHandler), 0);
  }

  function _fcIsImageUrl(url) {
    return url && /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(url);
  }

  function _fcStartReply(userId, msg) {
    // Cancel any edit in progress
    _fcCancelEdit(userId);

    const state = FC_STATE[userId];
    if (!state) return;

    const hasFile = !!msg.file;
    const isImage = hasFile && (msg.is_image || _fcIsImageUrl(msg.file));

    state.replyTo = {
      id: msg.id,
      message: msg.message || '',
      sender_name: msg.sender_name || (msg.isSent ? 'You' : 'User'),
      file: msg.file || null,
      is_image: isImage
    };

    const preview = document.getElementById(`fc-reply-preview-${userId}`);
    const nameEl = document.getElementById(`fc-reply-name-${userId}`);
    const textEl = document.getElementById(`fc-reply-text-${userId}`);
    const thumbEl = document.getElementById(`fc-reply-thumb-${userId}`);
    if (preview && nameEl && textEl) {
      nameEl.textContent = state.replyTo.sender_name;

      // Build preview text with media context
      if (thumbEl) thumbEl.innerHTML = '';
      if (isImage) {
        if (thumbEl) thumbEl.innerHTML = `<img src="${msg.file}" alt="">`;
        textEl.innerHTML = msg.message
          ? `<i class="fas fa-image text-primary me-1" style="font-size:10px"></i>${escapeHtml(msg.message)}`
          : '<i class="fas fa-image text-primary me-1" style="font-size:10px"></i>Photo';
      } else if (hasFile) {
        const fname = msg.file.split('/').pop();
        if (thumbEl) thumbEl.innerHTML = '<i class="fas fa-file-alt fc-reply-file-icon"></i>';
        textEl.innerHTML = msg.message
          ? `<i class="fas fa-paperclip me-1" style="font-size:10px"></i>${escapeHtml(msg.message)}`
          : `<i class="fas fa-paperclip me-1" style="font-size:10px"></i>${escapeHtml(fname)}`;
      } else {
        textEl.textContent = state.replyTo.message;
      }
      preview.classList.add('show');
    }

    const input = document.getElementById(`fc-input-${userId}`);
    if (input) input.focus();
  }

  function _fcCancelReply(userId) {
    const state = FC_STATE[userId];
    if (state) state.replyTo = null;

    const preview = document.getElementById(`fc-reply-preview-${userId}`);
    if (preview) preview.classList.remove('show');
    const thumbEl = document.getElementById(`fc-reply-thumb-${userId}`);
    if (thumbEl) thumbEl.innerHTML = '';
  }

  function _fcStartEdit(userId, msg) {
    // Cancel any reply in progress
    _fcCancelReply(userId);

    const state = FC_STATE[userId];
    if (!state) return;

    state.editMsgId = msg.id;

    const input = document.getElementById(`fc-input-${userId}`);
    const footer = document.getElementById(`fc-footer-${userId}`);
    const editIndicator = document.getElementById(`fc-edit-indicator-${userId}`);
    const sendBtn = document.getElementById(`fc-send-btn-${userId}`);
    const likeBtn = document.getElementById(`fc-like-btn-${userId}`);

    if (input) {
      input.value = msg.message || '';
      input.focus();
    }
    if (footer) footer.classList.add('editing');
    if (editIndicator) editIndicator.style.display = 'flex';
    if (sendBtn) {
      sendBtn.style.display = '';
      sendBtn.title = 'Save';
      sendBtn.querySelector('i').className = 'fas fa-check';
    }
    if (likeBtn) likeBtn.style.display = 'none';
  }

  function _fcCancelEdit(userId) {
    const state = FC_STATE[userId];
    if (!state || !state.editMsgId) return;

    state.editMsgId = null;

    const input = document.getElementById(`fc-input-${userId}`);
    const footer = document.getElementById(`fc-footer-${userId}`);
    const editIndicator = document.getElementById(`fc-edit-indicator-${userId}`);
    const sendBtn = document.getElementById(`fc-send-btn-${userId}`);
    const likeBtn = document.getElementById(`fc-like-btn-${userId}`);

    if (input) input.value = '';
    if (footer) footer.classList.remove('editing');
    if (editIndicator) editIndicator.style.display = 'none';
    if (sendBtn) {
      sendBtn.style.display = 'none';
      sendBtn.title = 'Send';
      sendBtn.querySelector('i').className = 'fas fa-paper-plane';
    }
    if (likeBtn) likeBtn.style.display = '';
  }

  function _fcDeleteMsg(userId, messageId) {
    const win = FC_WINDOWS[userId];
    if (!win) return;

    // Create confirmation overlay inside the window
    const overlay = document.createElement('div');
    overlay.className = 'fc-delete-confirm';
    overlay.innerHTML = `
      <div class="fc-delete-confirm-box">
        <p>Unsend this message for everyone?</p>
        <div class="fc-del-btns">
          <button class="fc-del-cancel">Cancel</button>
          <button class="fc-del-yes">Unsend</button>
        </div>
      </div>
    `;
    win.appendChild(overlay);

    overlay.querySelector('.fc-del-cancel').addEventListener('click', () => overlay.remove());
    overlay.querySelector('.fc-del-yes').addEventListener('click', () => {
      const ws = FC_HEADS[userId] ? FC_HEADS[userId].ws : null;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'delete_message', message_id: messageId }));
      }
      overlay.remove();
    });
  }

  function _fcUpdateSendLike(userId) {
    const input = document.getElementById(`fc-input-${userId}`);
    const sendBtn = document.getElementById(`fc-send-btn-${userId}`);
    const likeBtn = document.getElementById(`fc-like-btn-${userId}`);
    const fileInput = document.getElementById(`fc-file-input-${userId}`);
    if (!input || !sendBtn || !likeBtn) return;
    const hasText = input.value.trim().length > 0;
    const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
    if (hasText || hasFile) {
      sendBtn.style.display = '';
      likeBtn.style.display = 'none';
    } else {
      sendBtn.style.display = 'none';
      likeBtn.style.display = '';
    }
  }

  // =============== Reactions ===============
  const FC_REACTIONS = ['👍','❤️','😂','😮','😢','😡'];

  function _fcToggleReactionBar(userId, messageId, row, triggerBtn) {
    // Close any existing reaction bars
    document.querySelectorAll('.fc-reaction-bar').forEach(b => b.remove());

    const bar = document.createElement('div');
    bar.className = 'fc-reaction-bar';

    // Check which emoji the current user already reacted with on this message
    const bubble = row.querySelector('.fc-msg');
    let myReactedEmoji = null;
    if (bubble) {
      const myBadge = bubble.querySelector('.fc-reaction-badge[data-user-reacted="true"]');
      if (myBadge) myReactedEmoji = myBadge.getAttribute('data-emoji');
    }

    FC_REACTIONS.forEach(emoji => {
      const span = document.createElement('span');
      span.textContent = emoji;
      if (emoji === myReactedEmoji) span.classList.add('fc-reaction-active');
      span.addEventListener('click', (e) => {
        e.stopPropagation();
        bar.remove();

        // Optimistic UI: update DOM immediately before server responds
        const bbl = row.querySelector('.fc-msg');
        if (bbl) {
          let reactions = _fcCollectReactions(bbl);
          if (emoji === myReactedEmoji) {
            // Toggle off: remove current user's reaction
            reactions = reactions.filter(r => !(r.user_id === CURRENT_USER_ID && r.emoji === emoji));
          } else {
            // Switch or add: remove any previous reaction by current user, add new one
            reactions = reactions.filter(r => r.user_id !== CURRENT_USER_ID);
            reactions.push({ emoji: emoji, user_id: CURRENT_USER_ID });
          }
          _fcRenderReactions(bbl, reactions, messageId);
        }

        _fcSendReaction(userId, messageId, emoji);
      });
      bar.appendChild(span);
    });

    // Attach to the inner wrapper (position: relative) so it floats above the bubble
    const inner = row.querySelector('.fc-msg-inner');
    if (inner) {
      inner.appendChild(bar);
    } else {
      row.appendChild(bar);
    }

    // Close on outside click
    const closeHandler = (e) => {
      if (!bar.contains(e.target) && e.target !== triggerBtn) {
        bar.remove();
        document.removeEventListener('click', closeHandler);
      }
    };
    setTimeout(() => document.addEventListener('click', closeHandler), 0);
  }

  function _fcSendReaction(userId, messageId, emoji) {
    const ws = FC_HEADS[userId] ? FC_HEADS[userId].ws : null;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'add_reaction', message_id: messageId, emoji: emoji }));
    }
  }

  function _fcCollectReactions(bubble) {
    const reactions = [];
    const badges = bubble.querySelectorAll('.fc-reaction-badge');
    badges.forEach(b => {
      const emoji = b.getAttribute('data-emoji') || b.childNodes[0].textContent;
      const usersStr = b.getAttribute('data-users') || '';
      const users = usersStr ? usersStr.split(',').map(Number).filter(Boolean) : [];
      if (users.length > 0) {
        users.forEach(uid => reactions.push({ emoji, user_id: uid }));
      } else {
        const countEl = b.querySelector('.fc-reaction-count');
        const count = countEl ? parseInt(countEl.textContent) : 1;
        for (let i = 0; i < count; i++) reactions.push({ emoji, user_id: 0 });
      }
    });
    return reactions;
  }

  function _fcRenderReactions(bubble, reactions, msgId) {
    // Remove existing badge container
    const existing = bubble.querySelector('.fc-msg-reactions');
    if (existing) existing.remove();

    if (!reactions || reactions.length === 0) {
      bubble.style.marginBottom = '';
      return;
    }

    // Group reactions by emoji, tracking user IDs
    const groups = {};
    reactions.forEach(r => {
      if (!groups[r.emoji]) groups[r.emoji] = [];
      if (r.user_id && !groups[r.emoji].includes(r.user_id)) {
        groups[r.emoji].push(r.user_id);
      }
    });

    const container = document.createElement('div');
    container.className = 'fc-msg-reactions';

    Object.entries(groups).forEach(([emoji, users]) => {
      const count = users.length || 1;
      const badge = document.createElement('span');
      badge.className = 'fc-reaction-badge';
      const userReacted = users.includes(CURRENT_USER_ID);
      if (userReacted) {
        badge.classList.add('fc-reaction-mine');
        badge.setAttribute('data-user-reacted', 'true');
      }
      badge.setAttribute('data-emoji', emoji);
      badge.setAttribute('data-users', users.join(','));
      // Unique ID per message + emoji for targeted DOM lookup
      if (msgId) badge.id = `fc-react-${msgId}-${encodeURIComponent(emoji)}`;
      badge.innerHTML = emoji + (count > 1 ? `<span class="fc-reaction-count">${count}</span>` : '');
      container.appendChild(badge);
    });

    bubble.appendChild(container);

    // Add extra bottom padding to bubble when reactions are present
    bubble.style.marginBottom = '12px';
  }

  // =============== Lightbox ===============
  function _fcOpenLightbox(src) {
    const overlay = document.createElement('div');
    overlay.className = 'fc-lightbox';
    overlay.innerHTML = `
      <button class="fc-lightbox-close" title="Close">&times;</button>
      <img src="${src}" alt="Full size">
    `;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('show'));

    const close = () => {
      overlay.classList.remove('show');
      setTimeout(() => overlay.remove(), 200);
    };
    overlay.querySelector('.fc-lightbox-close').addEventListener('click', close);
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });
    document.addEventListener('keydown', function handler(e) {
      if (e.key === 'Escape') { close(); document.removeEventListener('keydown', handler); }
    });
  }

  // =============== Utilities ===============
  function scrollToBottom(userId) {
    requestAnimationFrame(() => {
      const body = document.getElementById(`fc-body-${userId}`);
      if (body) body.scrollTop = body.scrollHeight;
    });
  }

  function markAsRead(userId) {
    fetch(`/social/chat/mark_read/?receiver=${userId}`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCSRF() }
    }).catch(() => {});
  }

  function getCSRF() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let c of cookies) {
      c = c.trim();
      if (c.startsWith(name + '=')) return decodeURIComponent(c.substring(name.length + 1));
    }
    return '';
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // =============== Tab visibility: mark-as-read when user returns to tab ===============
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    // Tab became visible — reset unread for all open/visible windows
    Object.keys(FC_WINDOWS).forEach(uid => {
      const numUid = parseInt(uid);
      if (FC_WINDOWS[uid] && FC_WINDOWS[uid].style.display !== 'none' && FC_HEADS[numUid]) {
        if (FC_HEADS[numUid].unread > 0) {
          FC_HEADS[numUid].unread = 0;
          markAsRead(numUid);
        }
        // Send read receipt via WS
        if (FC_HEADS[numUid].ws && FC_HEADS[numUid].ws.readyState === WebSocket.OPEN) {
          FC_HEADS[numUid].ws.send(JSON.stringify({ type: 'read_receipt' }));
        }
      }
    });
    renderAllHeads();
    saveUnreadToStorage();
  });

  // =============== Restore from localStorage on page load ===============
  (function restoreFromStorage() {
    const saved = loadHeadsFromStorage();
    const savedUnread = loadUnreadFromStorage();
    const ids = Object.keys(saved);
    if (!ids.length) return;

    ids.forEach(uid => {
      const numUid = parseInt(uid);
      const entry = saved[uid];
      const unread = savedUnread[uid] || 0;
      createChatHead(numUid, entry.name, entry.photo, unread, true);

      // Re-open window if it was open before page change
      if (entry.windowOpen) {
        toggleWindow(numUid);
      }
    });
  })();

  // =============== Global API ===============
  window.openFloatingChat = function(userId, name, photo) {
    createChatHead(userId, name, photo || '/static/assets/img/def_user.jpg', 0);
    toggleWindow(userId);
  };

});
