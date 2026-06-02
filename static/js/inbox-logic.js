/* ============================================================
   inbox-logic.js  –  Social Media Inbox Chat Logic
   Extracted from social_media_inbox.html
   CURRENT_USER_ID must be set as a global before this file loads.
   ============================================================ */

// ── Global State ──
var activeSockets = {};
var pendingReadReceipts = new Set();
var userPresence = {};
var activePolling = {};
var readThrottleTimeouts = {};
var scrollDebounce = false;
var chatScrollPage = {};
var chatMessageCount = {};
var presenceInfo = {};

// ── Messenger-style "last seen" formatter ─────────────────
// Mirrors Facebook Messenger: "Active a moment ago" / "Active 5m ago"
// / "Active 2h ago" / "Active yesterday at 4:08 PM" / "Active 3 days
// ago" / "Active on Mar 15". Falls back to plain "Offline" when no
// last_seen timestamp is available (a freshly-onboarded peer).
function formatLastSeen(lastSeenISO) {
    if (!lastSeenISO) return 'Offline';
    var lastSeen = new Date(lastSeenISO);
    if (isNaN(lastSeen.getTime())) return 'Offline';

    var now = new Date();
    var diffMs = now - lastSeen;
    var diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1)  return 'Active a moment ago';
    if (diffMin < 60) return 'Active ' + diffMin + 'm ago';

    var diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24 && now.toDateString() === lastSeen.toDateString()) {
        return 'Active ' + diffHours + 'h ago';
    }

    var timeStr = lastSeen.toLocaleTimeString([], {
        hour: 'numeric', minute: '2-digit', hour12: true,
    });

    var yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (yesterday.toDateString() === lastSeen.toDateString()) {
        return 'Active yesterday at ' + timeStr;
    }

    var diffDays = Math.floor((now - lastSeen) / 86400000);
    if (diffDays < 7) return 'Active ' + diffDays + ' days ago';

    var dateStr = lastSeen.toLocaleDateString([], { month: 'short', day: 'numeric' });
    return 'Active on ' + dateStr;
}

// ── Conversation-row time formatter ───────────────────────
// Compact Messenger-style label for "the time of the last message"
// shown on each conversation row. Adapts the unit so the time stays
// short enough to fit in the row's right-edge slot at any viewport:
//   < 1 min       → "now"
//   < 60 min      → "5m"
//   same calendar day → "2:45 PM"
//   yesterday     → "Yesterday"
//   < 7 days      → "Mon"
//   older         → "1/5/25"
// Returns empty string for missing/invalid input so the row's
// .message-time slot collapses gracefully.
function formatChatRowTime(iso) {
    if (!iso) return '';
    var msgDate = new Date(iso);
    if (isNaN(msgDate.getTime())) return '';

    var now = new Date();
    var diffMs = now - msgDate;
    var diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1)  return 'now';
    if (diffMin < 60) return diffMin + 'm';

    if (now.toDateString() === msgDate.toDateString()) {
        return msgDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
    }

    var yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (yesterday.toDateString() === msgDate.toDateString()) return 'Yesterday';

    var diffDays = Math.floor(diffMs / 86400000);
    if (diffDays < 7) {
        return msgDate.toLocaleDateString([], { weekday: 'short' });
    }

    return msgDate.toLocaleDateString([], { month: 'numeric', day: 'numeric', year: '2-digit' });
}

// ── Real-time presence helper ─────────────────────────────
// Server-side presence_update events + the 60s polling fallback can
// lag behind reality. When a peer's WebSocket activity proves they
// are online RIGHT NOW (incoming message, incoming typing event), we
// flip their UI to "Active now" immediately. The next presence poll
// (or push) reconciles the timestamp later.
function markPeerOnline(peerId) {
    if (!peerId || parseInt(peerId) === CURRENT_USER_ID) return;
    var pid = parseInt(peerId);
    presenceInfo[pid] = { last_seen: new Date().toISOString(), is_online: true };

    // Sidebar avatar: flip the dot from offline → online.
    var contactItem = document.querySelector('.chat-contact[data-user-id="' + pid + '"]');
    var avatar = contactItem ? contactItem.querySelector('.avatar') : null;
    if (avatar) {
        avatar.classList.add('status-online');
        avatar.classList.remove('status-offline');
    }

    // Active chat header: flip "Last seen X minutes ago" → "Active now".
    var headerStatus = document.getElementById('status-text-' + pid);
    if (headerStatus) {
        headerStatus.textContent = 'Active now';
        headerStatus.classList.add('text-success');
        headerStatus.classList.remove('text-muted');
    }
}
var scrollHandlers = {};
var chatPagination = {};
var renderedMessageIds = new Set();
var editingMessageId = null;
var unreadCounts = {};
var isLoadingOldMessages = false;
var inboxSoundedMessageIds = new Set();

// ── Audio Notification ──
var inboxNotificationSound = new Audio('/static/audio/message-receive.wav');
inboxNotificationSound.volume = 0.5;
var inboxSoundMuted = localStorage.getItem('inbox_sound_muted') === 'true';
// Honor the messenger-logic.js audio-unlock across page navigations so
// the prime doesn't re-run (which can leak a sliver of the bell on
// each menu change).
var inboxAudioUnlocked = sessionStorage.getItem('cl_audio_unlocked') === '1';

function inboxUnlockAudio() {
    if (inboxAudioUnlocked) {
        document.removeEventListener('click', inboxUnlockAudio);
        document.removeEventListener('keydown', inboxUnlockAudio);
        return;
    }
    // Silence the prime so play()/pause() doesn't briefly chirp.
    var restoreVolume = inboxNotificationSound.volume;
    inboxNotificationSound.volume = 0;
    inboxNotificationSound.play().then(function() {
        inboxNotificationSound.pause();
        inboxNotificationSound.currentTime = 0;
        inboxNotificationSound.volume = restoreVolume;
        inboxAudioUnlocked = true;
        try { sessionStorage.setItem('cl_audio_unlocked', '1'); } catch (e) {}
        document.removeEventListener('click', inboxUnlockAudio);
        document.removeEventListener('keydown', inboxUnlockAudio);
    }).catch(function() {
        inboxNotificationSound.volume = restoreVolume;
    });
}
if (!inboxAudioUnlocked) {
    document.addEventListener('click', inboxUnlockAudio);
    document.addEventListener('keydown', inboxUnlockAudio);
}

// Shared sounded-IDs cache in localStorage — paired with the same
// key in messenger-logic.js so the dedup survives the page transition
// when the user leaves /social/inbox/ for another menu.
var INBOX_SOUNDED_LS = 'cl_sounded_message_ids';
function _inboxReadSoundedIds() {
    try {
        var raw = localStorage.getItem(INBOX_SOUNDED_LS);
        return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
}
function _inboxWriteSoundedIds(arr) {
    try { localStorage.setItem(INBOX_SOUNDED_LS, JSON.stringify(arr.slice(-400))); } catch (e) {}
}
function _inboxHasSoundedId(id) {
    if (!id) return false;
    return _inboxReadSoundedIds().indexOf(String(id)) !== -1;
}
function _inboxRememberSoundedId(id) {
    if (!id) return;
    var ids = _inboxReadSoundedIds();
    var key = String(id);
    if (ids.indexOf(key) === -1) {
        ids.push(key);
        _inboxWriteSoundedIds(ids);
    }
}

function inboxPlayNotification(chatId, isGroup, messageId) {
    if (inboxSoundMuted) return;
    // Dedup: skip if sound was already played for this message. Checks
    // both the in-memory set (same page) AND the cross-page localStorage
    // cache shared with messenger-logic.js so the bell never rings twice
    // for one message across navigation.
    if (messageId) {
        if (inboxSoundedMessageIds.has(messageId)) return;
        if (_inboxHasSoundedId(messageId)) {
            inboxSoundedMessageIds.add(messageId);
            return;
        }
        inboxSoundedMessageIds.add(messageId);
        _inboxRememberSoundedId(messageId);
        // Cap the set size to prevent memory leaks
        if (inboxSoundedMessageIds.size > 500) {
            var first = inboxSoundedMessageIds.values().next().value;
            inboxSoundedMessageIds.delete(first);
        }
    }
    // Skip if this chat is currently open and the tab is focused
    var activeChatId = localStorage.getItem("activeChatId");
    var activeIsGroup = localStorage.getItem("activeIsGroup") === 'true';
    if (document.hasFocus() && activeChatId && parseInt(activeChatId) === parseInt(chatId) && activeIsGroup === isGroup) return;
    inboxNotificationSound.currentTime = 0;
    inboxNotificationSound.play().catch(function() {});
}

function inboxToggleMute() {
    inboxSoundMuted = !inboxSoundMuted;
    localStorage.setItem('inbox_sound_muted', inboxSoundMuted);
    return inboxSoundMuted;
}
window.inboxToggleMute = inboxToggleMute;
window.inboxIsMuted = function() { return inboxSoundMuted; };

// ── DOMContentLoaded ──
document.addEventListener("DOMContentLoaded", function () {
    loadChatList();

    document.getElementById("createGroupModal").addEventListener("show.bs.modal", function() {
        var membersList = document.getElementById("groupMembersList");
        // Use inline style colors that read against the modal's themed paper
        // bg in both light and dark mode (Bootstrap's .text-dark / .text-muted
        // are hardcoded greys that disappear on dark theme).
        var stateStyle =
            "margin:0;padding:14px 12px;text-align:center;font-size:13px;" +
            "color:var(--ink-dim);background:var(--cream-2);" +
            "border:1px dashed var(--border-strong);border-radius:10px;";
        membersList.innerHTML =
            "<p style='" + stateStyle + "'>Loading friends…</p>";

        fetch('/social/friend/friends/')
            .then(function(response) { return response.json(); })
            .then(function(friends) {
                if (!friends.length) {
                    membersList.innerHTML =
                        "<div style='" + stateStyle + "'>" +
                            "<div style='font-size:22px;color:var(--gold);margin-bottom:6px;'>" +
                                "<i class='fas fa-user-slash'></i>" +
                            "</div>" +
                            "<div style='color:var(--ink);font-weight:600;margin-bottom:2px;'>No friends yet</div>" +
                            "<div style='color:var(--ink-dim);font-size:12px;'>" +
                                "Add friends from the Discover page to start a group chat." +
                            "</div>" +
                        "</div>";
                    return;
                }
                membersList.innerHTML = friends.map(function(friend) {
                    return '<div class="form-check">' +
                        '<input class="form-check-input" type="checkbox" value="' + friend.id + '" id="member-' + friend.id + '">' +
                        '<label class="form-check-label" for="member-' + friend.id + '">' + friend.name + '</label></div>';
                }).join("");
            })
            .catch(function() {
                membersList.innerHTML =
                    "<p style='" + stateStyle + ";color:var(--rose);border-color:rgba(192,132,121,0.30);'>" +
                        "Failed to load friends." +
                    "</p>";
            });

        // Teacher-only: populate the 'Create from class roster' selector.
        // Endpoint returns subjects the user teaches in the current
        // semester. If the list is empty (non-teacher or no active
        // assignments), keep the section hidden.
        var subjectSection = document.getElementById('groupFromSubjectSection');
        var subjectSelect = document.getElementById('groupFromSubject');
        if (subjectSection && subjectSelect) {
            subjectSection.style.display = 'none';
            subjectSelect.innerHTML = '<option value="">— Pick a subject to auto-fill members —</option>';
            fetch('/social/group_chat/teacher_subjects/')
                .then(function(r) { return r.ok ? r.json() : []; })
                .then(function(subjects) {
                    if (!Array.isArray(subjects) || !subjects.length) return;
                    subjects.forEach(function(s) {
                        var name = s.name || 'Subject';
                        var count = (s.studentCount !== undefined ? s.studentCount : s.student_count) || 0;
                        var sem = s.semester || '';
                        var opt = document.createElement('option');
                        opt.value = s.id;
                        opt.textContent = name + ' — ' + sem + ' (' + count + ' student' + (count === 1 ? '' : 's') + ')';
                        opt.setAttribute('data-name', name);
                        opt.setAttribute('data-semester', sem);
                        subjectSelect.appendChild(opt);
                    });
                    subjectSection.style.display = '';
                })
                .catch(function() {});
        }
    });

    // When a subject is picked, auto-fill the group name and collapse the
    // manual member checklist (the server-side endpoint fills membership).
    document.body.addEventListener('change', function(e) {
        if (e.target.id !== 'groupFromSubject') return;
        var sel = e.target;
        var membersSection = document.getElementById('groupMembersSection');
        var nameInput = document.getElementById('groupName');
        if (sel.value) {
            var opt = sel.options[sel.selectedIndex];
            var subj = opt.getAttribute('data-name') || '';
            var sem = opt.getAttribute('data-semester') || '';
            if (!nameInput.value || nameInput.dataset.autofilled === '1') {
                nameInput.value = subj + (sem ? (' — ' + sem) : '');
                nameInput.dataset.autofilled = '1';
            }
            if (membersSection) membersSection.style.display = 'none';
        } else {
            if (membersSection) membersSection.style.display = '';
            if (nameInput.dataset.autofilled === '1') {
                nameInput.value = '';
                delete nameInput.dataset.autofilled;
            }
        }
    });

    // Don't open the chat panel until loadChatList resolves — its
    // .then() block reopens the saved activeChatId with fresh
    // presence data populated. Opening it here first caused the
    // status text to flash "Loading status..." → "Offline" → (later)
    // "Active now" because the immediate call hit an empty
    // presenceInfo cache.

    if ("Notification" in window && Notification.permission !== "granted") {
        Notification.requestPermission();
    }

    // Periodically ping all WebSocket connections
    setInterval(function() {
        for (var userId in activeSockets) {
            var socket = activeSockets[userId];
            if (!socket) continue;
            if (socket.readyState === WebSocket.OPEN) {
                try {
                    socket.send(JSON.stringify({ type: "ping" }));
                } catch (err) {
                    console.warn("[Ping] Failed to send ping to user " + userId);
                }
            }
        }
    }, 60000);

    document.body.addEventListener("click", function (e) {
        if (e.target.closest('.contacts-list-show')) {
            localStorage.removeItem('activeChatId');
            localStorage.removeItem('activeChatName');
            localStorage.removeItem('activeChatPhoto');
            var chatCard = document.getElementById('chatCard');
            if (chatCard) chatCard.classList.remove('chat-active');
            // Tear down the mobile scroll lock if it was applied.
            // On desktop the lock is never set (see openChatPanel),
            // so this is a no-op there: clearing `body.style.top`
            // when nothing is set is fine, scrollTo(0,0) only fires
            // if a saved Y exists.
            var wasLocked = document.body.classList.contains('cl-chat-active');
            var lockY = parseInt(document.body.dataset.clChatLockY || '0', 10) || 0;
            document.body.classList.remove('cl-chat-active');
            document.body.style.top = '';
            delete document.body.dataset.clChatLockY;
            if (wasLocked && lockY) window.scrollTo(0, lockY);
        }
    });
});

// ── Utility Functions ──

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&<>"']/g, function(m) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[m];
    });
}

function truncateText(text, maxLength) {
    maxLength = maxLength || 50;
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

function getCSRFToken() {
    return document.cookie.split('; ').find(function(row) { return row.startsWith('csrftoken='); })?.split('=')[1] || '';
}

function getFileIcon(filename) {
    var ext = (filename || '').split('.').pop().toLowerCase();
    var map = {
        pdf: 'fa-file-pdf text-danger',
        doc: 'fa-file-word text-primary', docx: 'fa-file-word text-primary',
        xls: 'fa-file-excel text-success', xlsx: 'fa-file-excel text-success',
        ppt: 'fa-file-powerpoint text-warning', pptx: 'fa-file-powerpoint text-warning',
        zip: 'fa-file-archive text-secondary', rar: 'fa-file-archive text-secondary',
        txt: 'fa-file-alt text-muted',
        csv: 'fa-file-csv text-success',
    };
    return map[ext] || 'fa-file text-muted';
}

// Contact-row preview text for a photo/file message. Uses Messenger-style
// wording so the actor is clear: "You sent a photo" vs "Jane sent a
// photo" / "Jane sent you a photo" depending on direction. `isMine`
// flips the label between first-person (sender) and third-person
// (receiver). `peerName` is the OTHER party's display name.
function buildFilePreviewLabel(isMine, peerName, filePath) {
    var isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(filePath || '');
    var icon = isImage
        ? '<i class="fas fa-image text-primary me-1"></i>'
        : '<i class="fas fa-paperclip text-info me-1"></i>';
    var noun = isImage ? 'photo' : 'file';
    var label = isMine
        ? 'You sent a ' + noun
        : (peerName || 'Someone') + ' sent you a ' + noun;
    return icon + label;
}

// ── Media Modal ──

function openMediaModal(type, src) {
    var modal = document.getElementById('mediaModal');
    var content = document.getElementById('mediaModalContent');
    if (!modal || !content) return;
    if (type === 'image') {
        content.innerHTML = '<img src="' + src + '" alt="Preview">';
    } else if (type === 'video') {
        content.innerHTML = '<video controls autoplay><source src="' + src + '" type="video/' + src.split('.').pop() + '">Your browser does not support the video tag.</video>';
    }
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeMediaModal() {
    var modal = document.getElementById('mediaModal');
    var content = document.getElementById('mediaModalContent');
    if (!modal) return;
    modal.classList.remove('active');
    document.body.style.overflow = '';
    var video = content?.querySelector('video');
    if (video) video.pause();
    setTimeout(function() { if (content) content.innerHTML = ''; }, 200);
}

// Close modal on overlay click, close button, or Escape key
document.addEventListener('DOMContentLoaded', function() {
    var modal = document.getElementById('mediaModal');
    var closeBtn = document.getElementById('mediaModalClose');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) closeMediaModal();
        });
    }
    if (closeBtn) {
        closeBtn.addEventListener('click', closeMediaModal);
    }
});
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeMediaModal();
});

// ── Message Action Bar Builder ──

function buildMsgActions(msgId, isSent, isDeleted, hasFile, messageText, senderName) {
    if (isDeleted) return '';
    var encodedMsg = encodeURIComponent(messageText || '');
    var encodedSender = encodeURIComponent(senderName || '');

    var moreItems = '';
    if (isSent) {
        if (!hasFile) {
            moreItems += '<div class="dropdown-item edit-icon" onclick="editMessagePrompt(' + msgId + ', decodeURIComponent(\'' + encodedMsg + '\'))">' +
                '<i class="fas fa-edit text-primary"></i> Edit</div>';
        }
        moreItems += '<div class="dropdown-item text-danger delete-icon" onclick="if(confirm(\'Are you sure you want to unsend this message?\')) deleteMessage(' + msgId + ')">' +
            '<i class="fas fa-undo-alt"></i> Unsend</div>';
    }

    return '<div class="msg-hover-actions">' +
        '<button type="button" class="msg-action-btn reply-button" title="Reply" onclick="prepareReply(' + msgId + ', decodeURIComponent(\'' + encodedMsg + '\'), decodeURIComponent(\'' + encodedSender + '\'))"><i class="fas fa-reply"></i></button>' +
        '<button type="button" class="msg-action-btn reaction-icon" title="React" onclick="showReactionPicker(event, ' + msgId + ')"><i class="far fa-smile"></i></button>' +
        (moreItems ? '<div style="position:relative; display:inline-block;"><button type="button" class="msg-action-btn" title="More" onclick="toggleMsgDropdown(event, this)"><i class="fas fa-ellipsis-v"></i></button><div class="msg-more-dropdown">' + moreItems + '</div></div>' : '') +
        '</div>';
}

// ── Reply Block Builder ──

function buildReplyBlock(replyTo, isSent, senderName) {
    if (!replyTo) return '';
    var replyFile = replyTo.file || null;
    var isReplyImage = replyFile && /\.(jpg|jpeg|png|gif|webp)$/i.test(replyFile);

    if (isReplyImage) {
        return '<div class="msg-reply-block">' +
            '<div class="msg-reply-label"><i class="fas fa-reply"></i> ' + (isSent ? 'You' : escapeHtml(senderName)) + ' replied to ' + escapeHtml(replyTo.sender_name) + '</div>' +
            '<div class="msg-reply-quoted reply-has-image" onclick="scrollToRepliedMessage(' + replyTo.id + ')">' +
            '<img src="' + replyFile + '" alt="Reply image" class="reply-quoted-thumb"></div></div>';
    }

    var textContent = replyTo.message ? truncateText(escapeHtml(replyTo.message), 120) : 'Attachment';
    return '<div class="msg-reply-block">' +
        '<div class="msg-reply-label"><i class="fas fa-reply"></i> ' + (isSent ? 'You' : escapeHtml(senderName)) + ' replied to ' + escapeHtml(replyTo.sender_name) + '</div>' +
        '<div class="msg-reply-quoted" onclick="scrollToRepliedMessage(' + replyTo.id + ')">' +
        '<div class="reply-quoted-text">' + textContent + '</div></div></div>';
}

// ── Message Content Builder ──

function buildMsgContent(opts) {
    var msgId = opts.msgId, file = opts.file, message = opts.message,
        isDeleted = opts.isDeleted, isSent = opts.isSent, isGroup = opts.isGroup,
        senderName = opts.senderName, isImage = opts.isImage;

    if (isDeleted) {
        return '<div class="chat-message-content" data-message-id="' + msgId + '" style="border-radius: 12px; padding: 10px 14px; background-color: var(--chat-deleted-bg); color: var(--chat-deleted-color); font-style: italic;"><div class="chat-message-text">This message was unsent</div></div>';
    }

    var groupLabel = (!isSent && isGroup && senderName)
        ? '<strong class="d-block mb-1 text-info">' + escapeHtml(senderName) + '</strong>' : '';
    var textContent = message ? escapeHtml(message).replace(/\n/g, '<br>') : '';

    var isImg = file && (/\.(jpg|jpeg|png|gif|webp)$/i.test(file) || isImage);
    var isVideo = file && /\.(mp4|webm|ogg)$/i.test(file);
    var isFile = file && !isImg && !isVideo;

    // IMAGE-ONLY
    if (isImg && !textContent) {
        return '<div class="chat-message-content msg-content-image" data-message-id="' + msgId + '">' + groupLabel +
            '<img src="' + file + '" alt="Image" class="chat-img" style="width:220px; max-width:100%; height:auto;" onclick="openMediaModal(\'image\',\'' + file + '\')"></div>';
    }
    // IMAGE + TEXT
    if (isImg && textContent) {
        return '<div class="chat-message-content" data-message-id="' + msgId + '" style="border-radius: 12px; overflow: hidden; width: fit-content; background-color: ' + (isSent ? 'var(--chat-sent-img-bg)' : 'var(--chat-received-img-bg)') + '; color: ' + (isSent ? 'var(--chat-sent-color)' : 'var(--chat-received-color)') + ';">' + groupLabel +
            '<div style="display:block; cursor:pointer;" onclick="openMediaModal(\'image\',\'' + file + '\')"><img src="' + file + '" alt="Image" class="chat-img" style="border-radius: 0; width:220px; max-width:100%; height: auto; display: block;"></div>' +
            '<div class="chat-message-text" style="padding: 8px 14px;">' + textContent + '</div></div>';
    }
    // VIDEO
    if (isVideo) {
        var videoHtml = '<div class="msg-content-video"><video controls data-media-src="' + file + '"><source src="' + file + '" type="video/' + file.split('.').pop() + '">Your browser does not support the video tag.</video><div class="video-expand-btn" onclick="openMediaModal(\'video\',\'' + file + '\')" title="Expand video"><i class="fas fa-expand"></i></div></div>';
        if (!textContent) {
            return '<div class="chat-message-content msg-content-video" data-message-id="' + msgId + '">' + groupLabel + videoHtml + '</div>';
        }
        return '<div class="chat-message-content" data-message-id="' + msgId + '" style="border-radius: 12px; padding: 10px 14px; background-color: ' + (isSent ? 'var(--chat-sent-bg)' : 'var(--chat-received-bg)') + '; color: ' + (isSent ? 'var(--chat-sent-color)' : 'var(--chat-received-color)') + ';"><div class="chat-message-text">' + groupLabel + videoHtml + textContent + '</div></div>';
    }
    // FILE
    if (isFile) {
        var fileName = decodeURIComponent(file.split('/').pop());
        var iconClass = getFileIcon(fileName);
        var fileHtml = '<a href="' + file + '" download class="msg-content-file"><div class="file-icon"><i class="fas ' + iconClass.split(' ')[0] + '"></i></div><div class="file-info"><div class="file-name" title="' + escapeHtml(fileName) + '">' + escapeHtml(fileName) + '</div><div class="file-size">File</div></div><i class="fas fa-download ms-auto" style="font-size: 14px; opacity: 0.6;"></i></a>';
        if (!textContent) {
            return '<div class="chat-message-content" data-message-id="' + msgId + '" style="background: transparent !important; padding: 0 !important;">' + groupLabel + fileHtml + '</div>';
        }
        return '<div class="chat-message-content" data-message-id="' + msgId + '" style="border-radius: 12px; padding: 10px 14px; background-color: ' + (isSent ? 'var(--chat-sent-bg)' : 'var(--chat-received-bg)') + '; color: ' + (isSent ? 'var(--chat-sent-color)' : 'var(--chat-received-color)') + ';"><div class="chat-message-text">' + groupLabel + fileHtml + '<div class="mt-2">' + textContent + '</div></div></div>';
    }
    // TEXT-ONLY
    return '<div class="chat-message-content" data-message-id="' + msgId + '" style="border-radius: 12px; padding: 10px 14px; background-color: ' + (isSent ? 'var(--chat-sent-bg)' : 'var(--chat-received-bg)') + '; color: ' + (isSent ? 'var(--chat-sent-color)' : 'var(--chat-received-color)') + ';"><div class="chat-message-text">' + groupLabel + textContent + '</div></div>';
}

// ── Burst grouping: only the last bubble in a sender-burst shows its time.
// A bubble ends its burst when (a) it's the last in the list, (b) the next
// bubble has a different sender, or (c) the gap to the next bubble exceeds
// BURST_GAP_MS. Recompute is cheap (single DOM pass) so we call it after
// any insert/remove.
var BURST_GAP_MS = 5 * 60 * 1000;
function recomputeBurstEnds(listEl) {
    if (!listEl) return;
    var wrappers = listEl.querySelectorAll('.chat-message-wrapper');
    for (var i = 0; i < wrappers.length; i++) {
        var curr = wrappers[i];
        var next = wrappers[i + 1];
        var isEnd = true;
        if (next) {
            var sameSender = curr.getAttribute('data-sender-id') === next.getAttribute('data-sender-id');
            var currT = Date.parse(curr.getAttribute('data-created-at') || '');
            var nextT = Date.parse(next.getAttribute('data-created-at') || '');
            var gap = (!isNaN(currT) && !isNaN(nextT)) ? (nextT - currT) : Infinity;
            isEnd = !sameSender || gap > BURST_GAP_MS;
        }
        if (isEnd) curr.setAttribute('data-burst-end', '1');
        else curr.removeAttribute('data-burst-end');
    }
}
window.recomputeBurstEnds = recomputeBurstEnds;

// ── Seen-by avatars for group messages.
// Finds the current user's most recent sent message in `listEl` and appends
// a small stacked-avatar row of readers (max 3 visible + "+N"). Tapping
// the row opens a modal listing every reader with their read_at time.
function renderSeenByForGroup(listEl) {
    if (!listEl) return;
    // Clear any prior seen-by markers so we don't double-render on reload.
    listEl.querySelectorAll('.seen-by-row').forEach(function(el) { el.remove(); });

    var meId = parseInt(CURRENT_USER_ID, 10);
    var wrappers = listEl.querySelectorAll('.chat-message-wrapper[data-sender-id]');
    // Find the LAST wrapper whose sender is current user.
    var target = null;
    for (var i = wrappers.length - 1; i >= 0; i--) {
        if (parseInt(wrappers[i].getAttribute('data-sender-id'), 10) === meId) {
            target = wrappers[i];
            break;
        }
    }
    if (!target) return;
    var raw = target.getAttribute('data-read-by');
    if (!raw) return;
    var readers;
    try { readers = JSON.parse(raw); } catch (_) { return; }
    if (!Array.isArray(readers) || !readers.length) return;

    var visible = readers.slice(0, 3);
    var extra = readers.length - visible.length;
    var row = document.createElement('div');
    row.className = 'seen-by-row d-flex justify-content-end align-items-center mt-1 me-2';
    row.style.cssText = 'gap:0;cursor:pointer;font-size:10px;opacity:.85;';
    row.setAttribute('data-readers', raw);
    row.title = 'Seen by ' + readers.length + ' ' + (readers.length === 1 ? 'person' : 'people');

    var html = '';
    visible.forEach(function(u, idx) {
        html += '<img src="' + (u.photo || '/static/assets/img/def_user.jpg') + '" ' +
            'alt="' + (u.name || '') + '" ' +
            'style="width:16px;height:16px;border-radius:50%;object-fit:cover;border:1.5px solid var(--bs-body-bg,#fff);' +
            (idx === 0 ? '' : 'margin-left:-6px;') + '" />';
    });
    if (extra > 0) {
        html += '<span class="ms-1 text-muted" style="font-size:10px;">+' + extra + '</span>';
    } else {
        html += '<span class="ms-1 text-muted" style="font-size:10px;">Seen</span>';
    }
    row.innerHTML = html;
    target.appendChild(row);
}
window.renderSeenByForGroup = renderSeenByForGroup;

// Tap a seen-by row to reveal a reader list with timestamps.
document.addEventListener('click', function(e) {
    var row = e.target.closest('.seen-by-row');
    if (!row) return;
    var raw = row.getAttribute('data-readers');
    if (!raw) return;
    var readers;
    try { readers = JSON.parse(raw); } catch (_) { return; }
    var lines = readers.map(function(u) {
        var when = '';
        if (u.read_at || u.readAt) {
            try {
                when = new Date(u.read_at || u.readAt).toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' });
            } catch (_) {}
        }
        return (u.name || 'Member') + (when ? ('  ·  ' + when) : '');
    });
    alert('Seen by:\n\n' + lines.join('\n'));
});

// ── Time Divider Functions ──

function formatTimeDivider(dateStr) {
    var date = new Date(dateStr);
    if (isNaN(date.getTime())) return null;
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
    var msgDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    var timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (msgDay.getTime() === today.getTime()) return 'Today, ' + timeStr;
    if (msgDay.getTime() === yesterday.getTime()) return 'Yesterday, ' + timeStr;

    var diffDays = Math.floor((today - msgDay) / 86400000);
    if (diffDays < 7) {
        return date.toLocaleDateString([], { weekday: 'long' }) + ', ' + timeStr;
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) + ', ' + timeStr;
}

function getTimeDividerHtml(prevDateStr, currDateStr, gapMinutes) {
    gapMinutes = gapMinutes || 30;
    if (!prevDateStr || !currDateStr) return '';
    var prev = new Date(prevDateStr);
    var curr = new Date(currDateStr);
    if (isNaN(prev.getTime()) || isNaN(curr.getTime())) return '';
    var diffMs = Math.abs(curr - prev);
    if (diffMs < gapMinutes * 60 * 1000) return '';
    var label = formatTimeDivider(currDateStr);
    if (!label) return '';
    return '<div class="chat-time-divider"><span>' + label + '</span></div>';
}

function createTimeDividerEl(dateStr) {
    var label = formatTimeDivider(dateStr);
    if (!label) return null;
    var div = document.createElement('div');
    div.className = 'chat-time-divider';
    div.innerHTML = '<span>' + label + '</span>';
    return div;
}

// ── Touch/click handler for timestamps ──
document.addEventListener('click', function(e) {
    var bubble = e.target.closest('.chat-message-content');
    if (!bubble) {
        document.querySelectorAll('.chat-timestamp.visible').forEach(function(t) { t.classList.remove('visible'); });
        return;
    }
    var wrapper = bubble.closest('.chat-message-wrapper');
    if (!wrapper) return;
    var ts = wrapper.querySelector('.chat-timestamp');
    if (!ts) return;
    var isVisible = ts.classList.contains('visible');
    document.querySelectorAll('.chat-timestamp.visible').forEach(function(t) { t.classList.remove('visible'); });
    if (!isVisible) ts.classList.add('visible');
});

// ── Dropdown Toggle ──
function toggleMsgDropdown(event, btn) {
    event.stopPropagation();
    var dropdown = btn.parentElement.querySelector('.msg-more-dropdown');
    document.querySelectorAll('.msg-more-dropdown.show').forEach(function(d) {
        if (d !== dropdown) {
            d.classList.remove('show');
            var parentActions = d.closest('.msg-hover-actions');
            if (parentActions) parentActions.classList.remove('show');
        }
    });
    dropdown.classList.toggle('show');

    if (dropdown.classList.contains('show')) {
        var btnRect = btn.getBoundingClientRect();
        var isSent = !!btn.closest('.msg-row.sent');
        var dropdownHeight = dropdown.offsetHeight || 80;
        var top = btnRect.bottom + 4;
        if (top + dropdownHeight > window.innerHeight) {
            top = btnRect.top - dropdownHeight - 4;
        }
        dropdown.style.top = top + 'px';
        if (isSent) {
            dropdown.style.right = (window.innerWidth - btnRect.right) + 'px';
            dropdown.style.left = 'auto';
        } else {
            dropdown.style.left = btnRect.left + 'px';
            dropdown.style.right = 'auto';
        }
    }

    var hoverActions = btn.closest('.msg-hover-actions');
    if (hoverActions) {
        if (dropdown.classList.contains('show')) {
            hoverActions.classList.add('show');
        } else {
            hoverActions.classList.remove('show');
        }
    }
}

// Close dropdowns on outside click
document.addEventListener('click', function(e) {
    if (!e.target.closest('.msg-more-dropdown') && !e.target.closest('.msg-action-btn')) {
        document.querySelectorAll('.msg-more-dropdown.show').forEach(function(d) {
            d.classList.remove('show');
            var parentActions = d.closest('.msg-hover-actions');
            if (parentActions) parentActions.classList.remove('show');
        });
    }
});

// Close fixed dropdowns on scroll
document.addEventListener('scroll', function() {
    document.querySelectorAll('.msg-more-dropdown.show').forEach(function(d) {
        d.classList.remove('show');
        var parentActions = d.closest('.msg-hover-actions');
        if (parentActions) parentActions.classList.remove('show');
    });
}, true);

// ── Long-press on mobile for reaction picker ──
(function() {
    var longPressTimer = null;
    var longPressTriggered = false;

    document.addEventListener('touchstart', function(e) {
        var bubble = e.target.closest('.chat-message-content');
        if (!bubble) return;
        longPressTriggered = false;
        var msgId = bubble.getAttribute('data-message-id');
        if (!msgId) return;
        longPressTimer = setTimeout(function() {
            longPressTriggered = true;
            showReactionPicker(e, parseInt(msgId));
        }, 500);
    }, { passive: true });

    document.addEventListener('touchmove', function() {
        if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
        if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
        if (longPressTriggered) { e.preventDefault(); longPressTriggered = false; }
    });
})();

// ── Read Receipt Throttle ──

function throttleReadReceipt(userId) {
    if (readThrottleTimeouts[userId]) return;

    readThrottleTimeouts[userId] = setTimeout(function() {
        readThrottleTimeouts[userId] = null;
    }, 1000);

    var isGroup = localStorage.getItem('activeIsGroup') === 'true';
    var socketKey = isGroup ? 'group_' + userId : userId;
    var socket = activeSockets[socketKey];

    if (!socket) {
        setTimeout(function() {
            var retrySocket = activeSockets[socketKey];
            if (retrySocket && retrySocket.readyState === WebSocket.OPEN) {
                try { retrySocket.send(JSON.stringify({ type: "read_receipt" })); }
                catch (error) { console.warn("[ReadReceipt] Error after retry for user " + userId); }
            }
        }, 1000);
        return;
    }

    if (socket.readyState !== WebSocket.OPEN) return;

    try { socket.send(JSON.stringify({ type: "read_receipt" })); }
    catch (error) { console.warn("[ReadReceipt] Error sending read receipt for user " + userId); }
}

// ── Load Chat List ──

function loadChatList() {
    fetch('/social/friend/friends/')
        .then(function(response) { return response.json(); })
        .then(function(friends) {
            var chatList = document.getElementById("chat-list");
            chatList.innerHTML = '';

            if (friends.length === 0) {
                chatList.innerHTML =
                    '<div style="margin:24px 16px;padding:18px 14px;text-align:center;' +
                                'background:var(--cream-2);border:1px dashed var(--border-strong);' +
                                'border-radius:12px;">' +
                        '<div style="font-size:22px;color:var(--gold);margin-bottom:6px;">' +
                            '<i class="fas fa-user-slash"></i>' +
                        '</div>' +
                        '<div style="color:var(--ink);font-weight:600;font-size:13.5px;margin-bottom:2px;">' +
                            'No conversations yet' +
                        '</div>' +
                        '<div style="color:var(--ink-dim);font-size:12px;">' +
                            'Add friends from the Discover page to start chatting.' +
                        '</div>' +
                    '</div>';
                return;
            }

            friends.forEach(function(friend) {
                connectWebSocket(friend.id, function() { throttleReadReceipt(friend.id); }, false);
            });

            var chatPromises = friends.map(function(friend) {
                return Promise.all([
                    fetch('/social/chat/last_message/?receiver=' + friend.id).then(function(res) { return res.json(); }),
                    Promise.resolve({ is_online: false, last_seen: null })
                ])
                .then(function(results) {
                    var lastMessage = results[0];
                    var presence = results[1];

                    if (lastMessage.message === undefined && lastMessage.file === undefined) {
                        return null;
                    }
                    // DRF's CamelCaseJSONRenderer converts snake_case to
                    // camelCase, so the REST response can use either form.
                    // Read both. Fall back to the friend's known name when
                    // the API doesn't carry a sender_name (e.g. some legacy
                    // payloads) — otherwise the preview would say "Someone
                    // sent you a photo" because the peerName was empty.
                    var rawSenderId   = (lastMessage.sender_id !== undefined && lastMessage.sender_id !== null)
                        ? lastMessage.sender_id
                        : lastMessage.senderId;
                    var rawSenderName = lastMessage.sender_name || lastMessage.senderName || friend.name || '';
                    var senderName    = rawSenderName;

                    var presenceText = presence.is_online ? "Active now" : formatLastSeen(presence.last_seen);

                    presenceInfo[friend.id] = {
                        last_seen: presence.last_seen,
                        is_online: presence.is_online
                    };

                    var lastMsgText;
                    var lastIsMine = parseInt(rawSenderId, 10) === CURRENT_USER_ID;
                    if (lastMessage.message && lastMessage.message.trim() !== "") {
                        var prefix = lastIsMine ? 'You' : senderName;
                        lastMsgText = prefix + ': ' + lastMessage.message;
                    } else if (lastMessage.file) {
                        lastMsgText = buildFilePreviewLabel(lastIsMine, senderName, lastMessage.file);
                    } else {
                        lastMsgText = "No messages yet";
                    }

                    return {
                        id: friend.id,
                        name: friend.name,
                        photo: friend.photo || '/static/assets/img/def_user.jpg',
                        is_online: presence.is_online,
                        presenceText: presenceText,
                        lastMessageText: lastMsgText,
                        // DRF's CamelCaseJSONRenderer turns created_at into
                        // createdAt in the wire payload — read both so we
                        // work regardless of which renderer is active.
                        lastMessageTime: formatChatRowTime(lastMessage.created_at || lastMessage.createdAt),
                        lastMessageTimestamp: (lastMessage.created_at || lastMessage.createdAt)
                            ? new Date(lastMessage.created_at || lastMessage.createdAt).getTime()
                            : 0
                    };
                })
                .catch(function(error) {
                    console.error("Error loading chat or presence for");
                    return null;
                });
            });

            // Fetch group chats
            var groupChatsPromise = fetch('/social/group_chat/')
                .then(function(res) { return res.json(); })
                .then(function(response) {
                    var groups = response.results || [];
                    return groups.map(function(group) {
                        var gLastMsgText;
                        if (group.last_message) {
                            if (group.last_message.is_deleted) {
                                gLastMsgText = (group.last_message.deleted_by_name || 'Someone') + ': Unsent a message';
                            } else if (group.last_message.message && group.last_message.message.trim()) {
                                gLastMsgText = group.last_message.sender_name + ': ' + group.last_message.message;
                            } else if (group.last_message.file) {
                                var fileLabel = /\.(jpg|jpeg|png|gif|webp)$/i.test(group.last_message.file) ? "🖼️ Image" : "📎 File";
                                gLastMsgText = group.last_message.sender_name + ': ' + fileLabel;
                            } else {
                                gLastMsgText = group.last_message.sender_name + ': No message';
                            }
                        } else {
                            gLastMsgText = "No messages yet";
                        }
                        return {
                            id: group.id,
                            name: group.name,
                            photo: group.photo || '/static/assets/img/def_user.jpg',
                            is_group: true,
                            lastMessageText: gLastMsgText,
                            lastMessageTime: formatChatRowTime(
                                group.last_message && (group.last_message.created_at || group.last_message.createdAt)
                            ),
                            lastMessageTimestamp: (group.last_message && (group.last_message.created_at || group.last_message.createdAt))
                                ? new Date(group.last_message.created_at || group.last_message.createdAt).getTime() : 0
                        };
                    });
                });

            Promise.all([Promise.all(chatPromises), groupChatsPromise]).then(function(results) {
                var chats = results[0];
                var groupChats = results[1];
                groupChats.forEach(function(group) {
                    connectWebSocket(group.id, null, true);
                });
                chats = chats.filter(function(chat) { return chat !== null; });
                var allChats = chats.concat(groupChats).sort(function(a, b) { return b.lastMessageTimestamp - a.lastMessageTimestamp; });

                allChats.forEach(function(chat, index) {
                    var chatItem = document.createElement("div");
                    chatItem.classList.add("hover-actions-trigger", "chat-contact", "nav-item");
                    // No row is auto-marked .active. The .active highlight is now
                    // applied only when the user explicitly clicks a row (see the
                    // click handler below) or when an activeChatId is restored
                    // from localStorage. Previously index === 0 forced a phantom
                    // highlight on the first conversation even when the user
                    // hadn't opened anything.
                    chatItem.setAttribute("role", "tab");
                    chatItem.setAttribute("id", "chat-link-" + index);
                    chatItem.setAttribute("data-bs-toggle", "tab");
                    chatItem.setAttribute("data-bs-target", "#chat-" + index);
                    chatItem.setAttribute("aria-controls", "chat-" + index);
                    chatItem.setAttribute("aria-selected", "false");
                    chatItem.setAttribute("data-user-id", chat.id);
                    chatItem.setAttribute("data-is-group", chat.is_group ? "true" : "false");

                    chatItem.innerHTML =
                        '<div class="d-md-none d-lg-block">' +
                            '<div class="dropdown dropdown-active-trigger dropdown-chat">' +
                                '<button class="hover-actions btn btn-link btn-sm text-400 dropdown-caret-none dropdown-toggle end-0 fs-9 mt-4 me-1 z-1 pb-2 mb-n2" type="button" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">' +
                                    '<span class="fas fa-cog" data-fa-transform="shrink-3 down-4"></span>' +
                                '</button>' +
                                '<div class="dropdown-menu dropdown-menu-end border py-2 rounded-2">' +
                                    '<a class="dropdown-item" href="#">Mute</a>' +
                                    '<div class="dropdown-divider"></div>' +
                                    '<a class="dropdown-item" href="#">Archive</a>' +
                                    '<a class="dropdown-item text-danger" href="#" onclick="deleteConversation(' + chat.id + ', ' + chat.is_group + ')">Delete</a>' +
                                    '<div class="dropdown-divider"></div>' +
                                    '<a class="dropdown-item" href="#">Mark as Unread</a>' +
                                    '<a class="dropdown-item" href="#">Something\'s Wrong</a>' +
                                    '<a class="dropdown-item" href="#">Ignore Messages</a>' +
                                    '<a class="dropdown-item" href="#">Block Messages</a>' +
                                '</div>' +
                            '</div>' +
                        '</div>' +
                        '<div class="d-flex p-3">' +
                            '<div class="avatar avatar-xl ' + (!chat.is_group ? (chat.is_online ? 'status-online' : 'status-offline') : '') + '">' +
                                '<img class="rounded-circle" src="' + chat.photo + '" alt="' + chat.name + '" />' +
                            '</div>' +
                            '<div class="flex-1 chat-contact-body ms-2 chat-contact-body-text">' +
                                '<div class="d-flex justify-content-between">' +
                                    '<h6 class="mb-0 chat-contact-title">' + chat.name + '</h6>' +
                                    '<span class="message-time fs-11">' + chat.lastMessageTime + '</span>' +
                                '</div>' +
                                '<div class="min-w-0">' +
                                    '<div class="chat-contact-content pe-3">' + chat.lastMessageText + '</div>' +
                                '</div>' +
                            '</div>' +
                        '</div>';

                    chatItem.addEventListener("click", function () {
                        // Mark this row as the active conversation. Bootstrap's
                        // tab toggle can't manage this for us because data-bs-target
                        // points to a chat panel that openChatPanel() recreates,
                        // so we own the .active state directly. The CSS at
                        // .msg-contacts .chat-contact.active paints the brand-soft
                        // background + left-edge stripe.
                        document.querySelectorAll('.msg-contacts .chat-contact.active')
                            .forEach(function (n) {
                                n.classList.remove('active');
                                n.setAttribute('aria-selected', 'false');
                            });
                        chatItem.classList.add('active');
                        chatItem.setAttribute('aria-selected', 'true');
                        openChatPanel(chat.id, chat.name, chat.photo, chat.is_group || false);
                    });

                    chatList.appendChild(chatItem);
                });

                var activeId = localStorage.getItem('activeChatId');
                var activeName = localStorage.getItem('activeChatName');
                var activePhoto = localStorage.getItem('activeChatPhoto');
                var isGroup = localStorage.getItem('activeIsGroup') === 'true';

                if (activeId && activeName) {
                    setTimeout(function() {
                        // Mirror the click-handler behaviour for the row that
                        // matches the restored activeChatId, so the brand-soft
                        // highlight + left-edge stripe show on reload too.
                        document.querySelectorAll('.msg-contacts .chat-contact.active')
                            .forEach(function (n) {
                                n.classList.remove('active');
                                n.setAttribute('aria-selected', 'false');
                            });
                        var restoredRow = document.querySelector(
                            '.msg-contacts .chat-contact[data-user-id="' + activeId + '"]' +
                            '[data-is-group="' + (isGroup ? 'true' : 'false') + '"]'
                        );
                        if (restoredRow) {
                            restoredRow.classList.add('active');
                            restoredRow.setAttribute('aria-selected', 'true');
                        }
                        openChatPanel(parseInt(activeId), activeName, activePhoto, isGroup);
                    }, 100);
                }

                setInterval(function() {
                    for (var userId in presenceInfo) {
                        fetch('/social/presence/?user_id=' + userId)
                            .then(function(res) { return res.json(); })
                            .then(function(presence) {
                                presenceInfo[userId] = {
                                    last_seen: presence.last_seen,
                                    is_online: presence.is_online
                                };

                                var headerStatus = document.getElementById('status-text-' + userId);
                                var contactItem = document.querySelector('.chat-contact[data-user-id="' + userId + '"]');
                                var avatar = contactItem ? contactItem.querySelector(".avatar") : null;
                                var presText = "";

                                if (presence.is_online) {
                                    presText = "Active now";
                                    if (headerStatus) {
                                        headerStatus.textContent = presText;
                                        headerStatus.classList.add("text-success");
                                        headerStatus.classList.remove("text-muted");
                                    }
                                    if (avatar) {
                                        avatar.classList.add("status-online");
                                        avatar.classList.remove("status-offline");
                                    }
                                } else {
                                    presText = formatLastSeen(presence.last_seen);
                                    if (headerStatus) {
                                        headerStatus.textContent = presText;
                                        headerStatus.classList.remove("text-success");
                                        headerStatus.classList.add("text-muted");
                                    }
                                    if (avatar) {
                                        avatar.classList.remove("status-online");
                                        avatar.classList.add("status-offline");
                                    }
                                }
                            })
                            .catch(function(err) { console.error("Error updating presence for user " + userId + ":", err); });
                    }
                }, 60000);

            });
        })
        .catch(function(error) {
            console.error("Error loading friends:");
            document.getElementById("chat-list").innerHTML = '<p class="text-center mt-4">Error loading chats.</p>';
        });
}

// ── Open Chat Panel ──

function openChatPanel(userId, userName, userPhoto, isGroup) {
    userPhoto = userPhoto || null;
    isGroup = isGroup || false;

    var chatCard = document.getElementById('chatCard');
    if (chatCard) chatCard.classList.add('chat-active');
    // Mirror the state at <body> so global chrome (mobile tab bar,
    // background scroll) can react via CSS. Removed when the user
    // taps the back button (see the .contacts-list-show listener).
    // SCOPE THIS TO MOBILE ONLY. Setting `body.style.top` as an
    // inline style applies on every viewport, and base_operation.html
    // has `body { position: relative }`, so an inline `top: -Npx`
    // shifts the desktop body content up by N pixels — producing a
    // visible white strip where the html background shows through.
    // The position:fixed scroll-lock CSS already lives behind a
    // ≤640px media query; mirror that gating in the JS too.
    var isMobile = window.matchMedia && window.matchMedia('(max-width: 640px)').matches;
    if (isMobile && !document.body.classList.contains('cl-chat-active')) {
        document.body.dataset.clChatLockY = String(window.scrollY || 0);
        document.body.style.top = (-(window.scrollY || 0)) + 'px';
        document.body.classList.add('cl-chat-active');
    }

    renderedMessageIds.clear();
    localStorage.setItem('activeChatId', userId);
    localStorage.setItem('activeChatName', userName);
    localStorage.setItem('activeChatPhoto', userPhoto || '/static/assets/img/def_user.jpg');
    localStorage.setItem('activeIsGroup', isGroup ? 'true' : 'false');

    var messageWrapperId = isGroup ? 'groupMessages-' + userId : 'chatMessages-' + userId;
    var messageListId = isGroup ? 'groupMessagesList-' + userId : 'chatMessagesList-' + userId;

    var chatPanel = document.getElementById("chat-panel");
    chatPanel.innerHTML =
        '<div class="tab-pane card-chat-pane active d-flex flex-column h-100 position-relative" id="chat-' + userId + '" role="tabpanel" aria-labelledby="chat-link-' + userId + '">' +
            '<div class="chat-content-header">' +
                '<div class="d-flex align-items-center justify-content-between gap-2">' +
                    '<div class="d-flex align-items-center min-w-0">' +
                        '<a class="pe-2 text-700 contacts-list-show flex-shrink-0 chat-back-btn" href="#!">' +
                            '<div class="fas fa-chevron-left"></div>' +
                        '</a>' +
                        '<div class="min-w-0">' +
                            '<h5 class="mb-0 text-truncate fs-9">' + userName + '</h5>' +
                            (!isGroup ? '<div class="fs-11 text-400 text-truncate" id="status-text-' + userId + '">Loading status...</div>' : '') +
                        '</div>' +
                    '</div>' +
                    (isGroup ? '<div class="d-flex align-items-center flex-shrink-0 chat-header-actions"><button class="btn btn-sm btn-falcon-primary btn-chat-info" type="button" data-index="' + userId + '" data-bs-toggle="tooltip" data-bs-placement="top" title="Conversation Information"><span class="fas fa-cog"></span></button></div>' : '') +
                '</div>' +
            '</div>' +
            '<div class="chat-messages flex-grow-1 scrollbar scrollbar-overlay" id="' + messageWrapperId + '">' +
                '<div class="text-center text-muted" id="chat-loading-spinner-' + userId + '" style="display: none;"><small>Loading more messages...</small></div>' +
                '<div id="' + messageListId + '"></div>' +
                '<div id="typing-indicator-' + userId + '" class="cl-typing-indicator py-1 my-2 ms-4 me-4" style="display: none;"><span class="cl-typing-dots"><span></span><span></span><span></span></span><em>' + userName + ' is typing…</em></div>' +
            '</div>' +
            '<button type="button" id="scrollToBottomBtn-' + userId + '" class="scroll-to-bottom-btn" onclick="scrollToLatest(\'' + userId + '\')"><i class="fas fa-arrow-down"></i><span class="unread-badge" id="unreadBadge-' + userId + '"></span></button>' +
            '<div class="reply-preview-bar" id="reply-preview-' + userId + '">' +
                '<i class="fas fa-reply text-primary" style="font-size: 14px; flex-shrink: 0;"></i>' +
                '<div class="reply-preview-content">' +
                    '<div class="reply-preview-sender" id="reply-preview-sender-' + userId + '"></div>' +
                    '<div class="reply-preview-text" id="reply-preview-text-' + userId + '"></div>' +
                '</div>' +
                '<button type="button" class="reply-cancel-btn" onclick="cancelReply()" title="Cancel reply">&times;</button>' +
            '</div>' +
            '<form class="chat-editor-area d-flex align-items-center p-2 gap-2" onsubmit="event.preventDefault(); sendMessage(' + userId + ', \'' + userName.replace(/'/g, "\\'") + '\')">' +
                '<label for="chat-file-upload-' + userId + '" class="chat-file-upload text-muted fs-9 mb-0 cursor-pointer"><span class="fas fa-paperclip"></span></label>' +
                '<input class="d-none" type="file" id="chat-file-upload-' + userId + '" />' +
                '<div class="chat-bubble-wrapper d-flex align-items-center px-3 py-2 gap-2 flex-wrap flex-grow-1">' +
                    '<div id="file-preview-' + userId + '" class="file-preview-box align-items-center gap-2 px-2 py-1 me-2" style="display: none;"></div>' +
                    '<div id="chatInput-' + userId + '" class="chat-input emojiarea-editor" contenteditable="true" data-placeholder="Type your message..."></div>' +
                '</div>' +
                '<button type="button" class="btn btn-link emoji-icon text-muted fs-9 mb-0 p-0" id="emoji-btn-' + userId + '"><span class="far fa-laugh-beam"></span></button>' +
                '<div class="custom-emoji-picker shadow-sm border rounded d-none" id="custom-emoji-picker-' + userId + '" style="position: absolute; bottom: 60px; right: 70px; z-index: 9999;">' +
                    '<span class="emoji cursor-pointer" data-emoji="😀">😀</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="😂">😂</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="😍">😍</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="😢">😢</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="😡">😡</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="👍">👍</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="👎">👎</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="🔥">🔥</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="❤️">❤️</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="🎉">🎉</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="😎">😎</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="🤔">🤔</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="😱">😱</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="🥳">🥳</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="😴">😴</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="🤗">🤗</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="😇">😇</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="🤩">🤩</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="😜">😜</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="👏">👏</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="💪">💪</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="🙏">🙏</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="✨">✨</span>' +
                    '<span class="emoji cursor-pointer" data-emoji="💯">💯</span>' +
                '</div>' +
                '<button class="btn btn-sm btn-falcon-primary px-4 py-2 rounded-pill fw-semibold d-flex align-items-center chat-send-btn" type="submit"><i class="fas fa-paper-plane"></i> <span class="send-label ms-2">Send</span></button>' +
            '</form>' +
        '</div>';

    chatMessageCount[userId] = 0;

    if (isGroup) {
        loadChatMessages(userId, null, false, true);
        setupScrollHandler(userId, true);
    } else {
        fetch('/social/chat/mark_read/?receiver=' + userId, {
            method: "POST",
            headers: { "X-CSRFToken": getCSRFToken() }
        }).then(function() {
            loadChatMessages(userId, null, false, false);
            setupScrollHandler(userId, false);
        });
    }

    // Infinite scroll on top
    function setupScrollHandler(uid, isGrp) {
        var chatMessagesDiv = document.getElementById(isGrp ? 'groupMessages-' + uid : 'chatMessages-' + uid);
        if (!chatMessagesDiv) return;

        if (scrollHandlers[uid]) {
            chatMessagesDiv.removeEventListener("scroll", scrollHandlers[uid]);
        }

        var newScrollHandler = function() {
            var nearTopThreshold = 10;
            var isNearBottom = chatMessagesDiv.scrollTop + chatMessagesDiv.clientHeight >= chatMessagesDiv.scrollHeight - 50;

            if (!scrollDebounce && chatMessagesDiv.scrollTop <= nearTopThreshold && chatPagination[uid] !== null) {
                scrollDebounce = true;
                loadChatMessages(uid, chatPagination[uid], true, isGrp);
                setTimeout(function() { scrollDebounce = false; }, 300);
            }

            requestAnimationFrame(function() {
                var newIsNearBottom = chatMessagesDiv.scrollTop + chatMessagesDiv.clientHeight >= chatMessagesDiv.scrollHeight - 100;
                if (newIsNearBottom) {
                    var scrollBtn = document.getElementById('scrollToBottomBtn-' + uid);
                    if (scrollBtn) scrollBtn.classList.remove('visible');
                    resetUnreadBadge(uid);
                } else {
                    showScrollToBottomButton(uid);
                }
            });
        };

        chatMessagesDiv.addEventListener("scroll", newScrollHandler);
        scrollHandlers[uid] = newScrollHandler;
    }

    var chatInput = document.getElementById('chatInput-' + userId);
    var emojiBtn = document.getElementById('emoji-btn-' + userId);
    var emojiPicker = document.getElementById('custom-emoji-picker-' + userId);

    if (emojiPicker && !document.body.contains(emojiPicker)) {
        document.body.appendChild(emojiPicker);
    }

    emojiBtn.addEventListener("click", function(e) {
        e.stopPropagation();
        emojiPicker.classList.toggle("d-none");
    });

    emojiPicker.addEventListener("click", function(e) {
        if (e.target.classList.contains("emoji")) {
            insertEmojiIntoContentEditable(chatInput, e.target.dataset.emoji);
            emojiPicker.classList.add("d-none");
        }
    });

    document.addEventListener("click", function(e) {
        if (!emojiPicker.contains(e.target) && !emojiBtn.contains(e.target)) {
            emojiPicker.classList.add("d-none");
        }
    });

    window.addEventListener("focus", function() {
        if (activeSockets[userId]) {
            throttleReadReceipt(userId);
        }
    });

    connectWebSocket(userId, function() { throttleReadReceipt(userId); }, isGroup);

    var chatInputDiv = document.getElementById('chatInput-' + userId);
    var fileInput = document.getElementById('chat-file-upload-' + userId);
    var filePreview = document.getElementById('file-preview-' + userId);

    fileInput.addEventListener("change", function () {
        var file = this.files[0];
        var fp = document.getElementById('file-preview-' + userId);

        if (!file) {
            fp.innerHTML = "";
            fp.style.display = "none";
            return;
        }

        var forbiddenExtensions = ['exe', 'bat', 'sh', 'cmd', 'js', 'jar', 'msi'];
        var fileExtension = file.name.split('.').pop().toLowerCase();

        if (forbiddenExtensions.indexOf(fileExtension) !== -1) {
            alert('The file type .' + fileExtension + ' is not allowed.');
            this.value = "";
            fp.innerHTML = "";
            fp.style.display = "none";
            return;
        }

        // The file is base64-encoded and pushed through the chat
        // WebSocket; Daphne's default max frame is ~1 MiB, plus base64
        // adds ~33 % overhead. Reject anything over ~700 KiB before it
        // disappears silently, with an inline message in the preview
        // box so the user knows what happened.
        var MAX_BYTES = 700 * 1024;
        if (file.size > MAX_BYTES) {
            this.value = "";
            fp.style.display = "flex";
            fp.innerHTML = '<div class="file-preview-box d-inline-flex align-items-center gap-2 px-2 py-1" style="background: rgba(255,107,107,0.12); border:1px solid rgba(255,107,107,0.3);">' +
                '<i class="fas fa-triangle-exclamation" style="color:#ff6b6b;"></i>' +
                '<span class="file-name small">File too large (' + (file.size / 1024 / 1024).toFixed(2) + ' MB). Max ~700 KB over chat.</span>' +
                '<span class="cursor-pointer" onclick="clearFilePreview(\'' + userId + '\')"><i class="fas fa-times-circle"></i></span>' +
                '</div>';
            return;
        }

        fp.style.display = "flex";

        if (file) {
            var isImageFile = file.type.startsWith("image/");
            var icon = isImageFile ? "fa-image text-primary" : "fa-paperclip text-secondary";
            fp.innerHTML = '<div class="file-preview-box d-inline-flex align-items-center gap-2 px-2 py-1">' +
                '<span class="fas ' + icon + '"></span>' +
                '<span class="file-name small text-truncate">' + file.name + '</span>' +
                '<span class="text-danger cursor-pointer" onclick="clearFilePreview(\'' + userId + '\')">' +
                '<i class="fas fa-times-circle"></i></span></div>';
        }
    });

    chatInputDiv.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage(userId, userName);
        }

        var typingTimeout = null;
        chatInputDiv.addEventListener("input", function() {
            var isGrp = localStorage.getItem("activeIsGroup") === 'true';
            var socketKey = isGrp ? 'group_' + userId : userId;
            var socket = activeSockets[socketKey];

            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ type: "typing" }));
                if (typingTimeout) clearTimeout(typingTimeout);
                typingTimeout = setTimeout(function() {
                    if (socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: "stop_typing" }));
                    }
                }, 1000);
            }
        });
    });

    // Set initial status from cached presenceInfo + the contact's
    // online dot. If we already have a last_seen for this peer, surface
    // it as a Messenger-style relative time ("Active 5m ago") instead
    // of the bare "Offline" we used to fall through to.
    setTimeout(function() {
        var contactItem = document.querySelector('.chat-contact[data-user-id="' + userId + '"]');
        var headerStatus = document.getElementById('status-text-' + userId);
        if (contactItem && headerStatus) {
            var avatar = contactItem.querySelector(".avatar");
            var cached = presenceInfo[userId] || {};
            var isOnline = (avatar && avatar.classList.contains("status-online")) || cached.is_online === true;
            if (isOnline) {
                headerStatus.textContent = "Active now";
                headerStatus.classList.add("text-success");
                headerStatus.classList.remove("text-muted");
            } else {
                headerStatus.textContent = formatLastSeen(cached.last_seen);
                headerStatus.classList.add("text-muted");
                headerStatus.classList.remove("text-success");
            }
        }
    }, 100);

    // Pull a fresh presence sample so the header doesn't stay stale
    // for up to 60s after a page reload. Skips groups — only DMs
    // have a meaningful last_seen.
    if (!isGroup) {
        fetch('/social/presence/?user_id=' + userId)
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (presence) {
                if (!presence) return;
                presenceInfo[userId] = {
                    last_seen: presence.last_seen,
                    is_online: presence.is_online,
                };
                var headerStatus = document.getElementById('status-text-' + userId);
                var contactItem = document.querySelector('.chat-contact[data-user-id="' + userId + '"]');
                var avatar = contactItem ? contactItem.querySelector('.avatar') : null;
                if (presence.is_online) {
                    if (headerStatus) {
                        headerStatus.textContent = 'Active now';
                        headerStatus.classList.add('text-success');
                        headerStatus.classList.remove('text-muted');
                    }
                    if (avatar) {
                        avatar.classList.add('status-online');
                        avatar.classList.remove('status-offline');
                    }
                } else {
                    if (headerStatus) {
                        headerStatus.textContent = formatLastSeen(presence.last_seen);
                        headerStatus.classList.remove('text-success');
                        headerStatus.classList.add('text-muted');
                    }
                    if (avatar) {
                        avatar.classList.remove('status-online');
                        avatar.classList.add('status-offline');
                    }
                }
            })
            .catch(function () { /* swallow — polling will retry */ });
    }
}

// ── Helper Functions ──

function clearFilePreview(userId) {
    var fileInput = document.getElementById('chat-file-upload-' + userId);
    var filePreview = document.getElementById('file-preview-' + userId);
    fileInput.value = "";
    filePreview.innerHTML = "";
    filePreview.style.display = "none";
}

function searchContacts() {
    var input = document.getElementById("contactSearchInput").value.toLowerCase();
    var chatList = document.getElementById("chat-list");
    var chatItems = document.querySelectorAll(".chat-contact");

    if (input === "") {
        chatList.innerHTML = "";
        loadChatList();
        return;
    }

    var hasResults = false;
    chatItems.forEach(function(item) {
        var contactName = item.querySelector(".chat-contact-title").textContent.toLowerCase();
        if (contactName.indexOf(input) !== -1) {
            item.style.display = "block";
            hasResults = true;
        } else {
            item.style.display = "none";
        }
    });

    if (!hasResults) {
        chatList.innerHTML = '<p class="text-center mt-4 text-muted">No contacts found</p>';
    }
}

function renderChatContact(chat) {
    return '<div class="hover-actions-trigger chat-contact nav-item p-2 border-bottom">' +
        '<div class="d-flex p-3">' +
            '<div class="avatar avatar-xl status-online">' +
                '<img class="rounded-circle" src="' + chat.photo + '" alt="' + chat.name + '" />' +
            '</div>' +
            '<div class="flex-1 chat-contact-body ms-2 chat-contact-body-text">' +
                '<div class="d-flex justify-content-between">' +
                    '<h6 class="mb-0 chat-contact-title">' + chat.name + '</h6>' +
                    '<span class="message-time fs-11">' + chat.lastMessageTime + '</span>' +
                '</div>' +
                '<div class="min-w-0">' +
                    '<div class="chat-contact-content pe-3">' + chat.lastMessageText + '</div>' +
                '</div>' +
            '</div>' +
        '</div></div>';
}

function scrollToRepliedMessage(messageId) {
    var activeChatId = localStorage.getItem('activeChatId');
    var isGroup = localStorage.getItem('activeIsGroup') === 'true';
    var wrapperId = isGroup ? 'groupMessages-' + activeChatId : 'chatMessages-' + activeChatId;
    var chatMessagesDiv = document.getElementById(wrapperId);

    function highlightAndScroll(el) {
        if (!el || !chatMessagesDiv) return;
        var containerRect = chatMessagesDiv.getBoundingClientRect();
        var elRect = el.getBoundingClientRect();
        var offsetTop = elRect.top - containerRect.top + chatMessagesDiv.scrollTop;
        chatMessagesDiv.scrollTo({
            top: offsetTop - (containerRect.height / 2) + (elRect.height / 2),
            behavior: 'smooth'
        });
        el.classList.add('msg-highlight-glow');
        setTimeout(function() {
            el.classList.add('msg-highlight-glow-fade');
            setTimeout(function() {
                el.classList.remove('msg-highlight-glow', 'msg-highlight-glow-fade');
            }, 400);
        }, 2000);
    }

    var el = document.querySelector('.chat-message-content[data-message-id="' + messageId + '"]');
    if (el) {
        highlightAndScroll(el);
    } else {
        fetch('/social/chat/single_message/?message_id=' + messageId)
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (!data || !data.id) return;
                var listId = isGroup ? 'groupMessagesList-' + activeChatId : 'chatMessagesList-' + activeChatId;
                var chatMessagesList = document.getElementById(listId);
                if (!chatMessagesList) return;
                var messageDiv = document.createElement("div");
                var isSent = parseInt(data.sender_id) === CURRENT_USER_ID;
                messageDiv.className = "chat-message-wrapper d-flex align-items-end mb-2 ms-4 me-4 mt-2";
                messageDiv.classList.add(isSent ? "justify-content-end" : "justify-content-start");
                messageDiv.style.position = "relative";
                var uPhoto = data.sender_photo || '/static/assets/img/def_user.jpg';
                var replyFallbackContent = buildMsgContent({
                    msgId: data.id, file: data.file, message: data.message,
                    isDeleted: false, isSent: isSent, isGroup: false, senderName: data.sender_name
                });
                messageDiv.innerHTML =
                    '<div class="d-flex ' + (isSent ? 'flex-row-reverse' : 'flex-row') + ' align-items-end gap-2 mb-2">' +
                        (!isSent ? '<img class="profile-image rounded-circle me-2" src="' + uPhoto + '" alt="Profile" style="width: 32px; height: 32px; object-fit: cover;">' : '') +
                        '<div class="d-flex flex-column ' + (isSent ? 'align-items-end' : 'align-items-start') + '">' +
                            '<div class="msg-row ' + (isSent ? 'sent' : 'received') + '">' +
                                replyFallbackContent +
                                buildMsgActions(data.id, isSent, false, !!data.file, data.message, data.sender_name) +
                            '</div>' +
                        '</div>' +
                    '</div>';
                chatMessagesList.prepend(messageDiv);
                setTimeout(function() {
                    var newEl = document.querySelector('.chat-message-content[data-message-id="' + messageId + '"]');
                    highlightAndScroll(newEl);
                }, 200);
            })
            .catch(function(err) { console.error("Failed to fetch replied message:", err); });
    }
}

// ── Load Chat Messages ──

function loadChatMessages(userId, nextUrl, prepend, isGroup) {
    nextUrl = nextUrl || null;
    prepend = prepend || false;
    isGroup = isGroup || false;

    if (prepend && isLoadingOldMessages) return;
    if (prepend) isLoadingOldMessages = true;

    if (prepend) {
        if (!chatScrollPage[userId]) {
            chatScrollPage[userId] = 2;
        } else {
            chatScrollPage[userId]++;
        }
    } else {
        chatScrollPage[userId] = 1;
    }

    var chatMessagesList = document.getElementById(isGroup ? 'groupMessagesList-' + userId : 'chatMessagesList-' + userId);
    if (!chatMessagesList) return;

    var chatMessagesDiv = document.getElementById(isGroup ? 'groupMessages-' + userId : 'chatMessages-' + userId);
    var spinner = document.getElementById('chat-loading-spinner-' + userId);

    var url = nextUrl || (isGroup
        ? '/social/group_chat/messages/?group_id=' + userId
        : '/social/chat/?receiver=' + userId);

    if (prepend && spinner) spinner.style.display = 'block';

    fetch(url)
        .then(function(response) { return response.json(); })
        .then(function(data) {
            chatPagination[userId] = data.next || null;
            var messages = Array.isArray(data.results) ? data.results : Array.isArray(data) ? data : [];

            if (!prepend) {
                messages = messages.reverse();
            }

            if (!chatMessageCount[userId]) {
                chatMessageCount[userId] = 0;
            }
            chatMessageCount[userId] += messages.length;

            if (!messages.length && prepend) {
                var noMoreMsg = document.createElement("div");
                noMoreMsg.className = "text-center text-muted small mb-2";
                noMoreMsg.innerText = "No more messages";
                chatMessagesList.prepend(noMoreMsg);
                return;
            }

            if (!messages.length) return;

            var oldScrollHeight = chatMessagesDiv.scrollHeight;
            var oldScrollTop = chatMessagesDiv.scrollTop;
            var prevMsgTime = null;

            messages.forEach(function(message, idx) {
                if (renderedMessageIds.has(message.id)) return;
                renderedMessageIds.add(message.id);

                // DRF camel-case renderer converts snake_case keys to camelCase.
                // Mirror the camelCase keys back onto the snake_case names this
                // renderer uses, so message.formatted_time / .created_at / etc.
                // resolve regardless of which casing the server emits.
                if (message.formattedTime !== undefined && message.formatted_time === undefined) message.formatted_time = message.formattedTime;
                if (message.createdAt !== undefined && message.created_at === undefined) message.created_at = message.createdAt;
                if (message.senderId !== undefined && message.sender_id === undefined) message.sender_id = message.senderId;
                if (message.senderName !== undefined && message.sender_name === undefined) message.sender_name = message.senderName;
                if (message.senderPhoto !== undefined && message.sender_photo === undefined) message.sender_photo = message.senderPhoto;
                if (message.isSent !== undefined && message.is_sent === undefined) message.is_sent = message.isSent;
                if (message.isRead !== undefined && message.is_read === undefined) message.is_read = message.isRead;
                if (message.isDeleted !== undefined && message.is_deleted === undefined) message.is_deleted = message.isDeleted;
                if (message.isEdited !== undefined && message.is_edited === undefined) message.is_edited = message.isEdited;
                if (message.replyTo !== undefined && message.reply_to === undefined) message.reply_to = message.replyTo;
                if (message.readBy !== undefined && message.read_by === undefined) message.read_by = message.readBy;

                var currTime = message.created_at || message.timestamp;
                if (currTime) {
                    var dividerEl = (idx === 0 && !prepend)
                        ? createTimeDividerEl(currTime)
                        : (prevMsgTime ? (function() {
                            var html = getTimeDividerHtml(prevMsgTime, currTime, 30);
                            if (!html) return null;
                            var tmp = document.createElement('div');
                            tmp.innerHTML = html;
                            return tmp.firstElementChild;
                        })() : null);
                    if (dividerEl) {
                        if (prepend) chatMessagesList.prepend(dividerEl);
                        else chatMessagesList.appendChild(dividerEl);
                    }
                    prevMsgTime = currTime;
                }

                // Determine bubble side. We've seen the server's
                // `is_sent` field flip on REST loads, so we resolve
                // sent/received from sender_id + CURRENT_USER_ID +
                // the chat-partner id (`userId` in this scope) — any
                // of those three should pin it down even if one is
                // wrong. The chat-partner check is the strongest:
                // if sender == partner, it's received; otherwise sent.
                var senderId = message.sender_id;
                if (senderId === undefined || senderId === null) {
                    if (message.sender && typeof message.sender === 'object') {
                        senderId = message.sender.id;
                    } else if (message.sender !== undefined && message.sender !== null) {
                        senderId = message.sender;
                    }
                }
                var partnerId = parseInt(userId, 10);
                var sId = senderId !== null && senderId !== undefined ? parseInt(senderId, 10) : NaN;
                var meId = parseInt(CURRENT_USER_ID, 10);
                var isSent;
                if (!isNaN(sId) && !isGroup && !isNaN(partnerId)) {
                    // 1:1 chat — strongest signal: sender != partner means it's mine.
                    isSent = sId !== partnerId;
                } else if (!isNaN(sId)) {
                    isSent = sId === meId;
                } else if (typeof message.is_sent !== 'undefined') {
                    isSent = !!message.is_sent;
                } else {
                    isSent = false;
                }
                if (window.__inboxDebug) {
                    console.log('[bubble-side]', { id: message.id, sender_id: message.sender_id, sender: message.sender, resolved_senderId: senderId, partnerId: partnerId, CURRENT_USER_ID: meId, is_sent_server: message.is_sent, isSent_final: isSent });
                }
                var userPhoto = message.sender_photo || '/static/assets/img/def_user.jpg';

                var messageDiv = document.createElement("div");
                messageDiv.className = "chat-message-wrapper d-flex align-items-end mb-2 ms-4 me-4 mt-2";
                messageDiv.classList.add(isSent ? "justify-content-end" : "justify-content-start");
                messageDiv.style.position = "relative";
                if (message.created_at) messageDiv.setAttribute('data-created-at', message.created_at);
                if (senderId !== undefined && senderId !== null) messageDiv.setAttribute('data-sender-id', String(senderId));
                if (Array.isArray(message.read_by)) {
                    try { messageDiv.setAttribute('data-read-by', JSON.stringify(message.read_by)); } catch (_) {}
                }

                var replyBlockHtml = buildReplyBlock(message.reply_to, isSent, message.sender_name);
                var contentHtml = buildMsgContent({
                    msgId: message.id, file: message.file, message: message.message,
                    isDeleted: message.is_deleted, isSent: isSent, isGroup: isGroup, senderName: message.sender_name
                });

                messageDiv.innerHTML =
                    '<div class="d-flex ' + (isSent ? 'flex-row-reverse' : 'flex-row') + ' align-items-end gap-2 mb-2">' +
                        (!isSent ? '<img class="profile-image rounded-circle me-2" src="' + (userPhoto || '/static/assets/img/def_user.jpg') + '" alt="Profile" style="width: 32px; height: 32px; object-fit: cover;">' : '') +
                        '<div class="d-flex flex-column ' + (isSent ? 'align-items-end' : 'align-items-start') + '">' +
                            replyBlockHtml +
                            '<div class="msg-row ' + (isSent ? 'sent' : 'received') + '">' +
                                contentHtml +
                                buildMsgActions(message.id, isSent, message.is_deleted, !!message.file, message.message, message.sender_name) +
                            '</div>' +
                            '<div class="reaction-bubble-container mt-1 d-flex ' + (isSent ? 'justify-content-end' : 'justify-content-start') + ' pe-2" id="reaction-display-' + message.id + '"></div>' +
                            '<small class="chat-timestamp text-500 mt-1 d-flex align-items-center gap-2" style="font-size: 10px;">' +
                                (message.is_edited ? '<span class="msg-edited-label">edited</span>' : '') +
                                message.formatted_time +
                                (isSent
                                    ? (message.is_read
                                        ? '<i class="fas fa-check-double text-primary read-check" data-read="true" data-message-id="' + message.id + '"></i>'
                                        : '<i class="fas fa-check text-muted read-check" data-read="false" data-message-id="' + message.id + '"></i>')
                                    : '') +
                            '</small>' +
                        '</div>' +
                    '</div>';

                var reactionDisplay = messageDiv.querySelector('#reaction-display-' + message.id);
                if (reactionDisplay && message.reactions && message.reactions.length > 0) {
                    var emojiCounts = {};
                    message.reactions.forEach(function(reaction) {
                        if (!emojiCounts[reaction.emoji]) {
                            emojiCounts[reaction.emoji] = { count: 1, users: [reaction.user_id] };
                        } else {
                            emojiCounts[reaction.emoji].count++;
                            emojiCounts[reaction.emoji].users.push(reaction.user_id);
                        }
                    });
                    for (var emoji in emojiCounts) {
                        var isMe = emojiCounts[emoji].users.indexOf(CURRENT_USER_ID) > -1;
                        var badge = buildReactionBadge(emoji, emojiCounts[emoji].count, emojiCounts[emoji].users, isMe);
                        reactionDisplay.appendChild(badge);
                    }
                }

                if (prepend) {
                    chatMessagesList.prepend(messageDiv);
                } else {
                    chatMessagesList.appendChild(messageDiv);
                }
            });

            document.querySelectorAll(".read-check[data-read='false']").forEach(function(icon) {
                var msgId = parseInt(icon.getAttribute("data-message-id"));
                if (pendingReadReceipts.has(msgId)) {
                    icon.classList.remove("fa-check", "text-muted");
                    icon.classList.add("fa-check-double", "text-primary");
                    icon.setAttribute("data-read", "true");
                    pendingReadReceipts.delete(msgId);
                }
            });

            recomputeBurstEnds(chatMessagesList);

            // For group chats, render seen-by avatars and mark visible
            // received messages as read so other senders' UIs can update.
            if (isGroup) {
                renderSeenByForGroup(chatMessagesList);
                var unreadIds = [];
                messages.forEach(function(m) {
                    var sId = m.sender_id !== undefined ? m.sender_id : (m.senderId !== undefined ? m.senderId : null);
                    if (sId !== null && parseInt(sId, 10) !== parseInt(CURRENT_USER_ID, 10)) unreadIds.push(m.id);
                });
                if (unreadIds.length) {
                    fetch('/social/group_chat/' + userId + '/mark_read/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
                        body: JSON.stringify({ message_ids: unreadIds })
                    }).catch(function(){});
                }
            }

            if (prepend) {
                chatMessagesDiv.style.scrollBehavior = 'auto';
                var immediateNewHeight = chatMessagesDiv.scrollHeight;
                chatMessagesDiv.scrollTop = oldScrollTop + (immediateNewHeight - oldScrollHeight);

                var mediaPromises = [];
                chatMessagesList.querySelectorAll('img.chat-img, video').forEach(function(el) {
                    if (el.tagName === 'IMG' && !el.complete) {
                        mediaPromises.push(new Promise(function(resolve) {
                            el.addEventListener('load', resolve, { once: true });
                            el.addEventListener('error', resolve, { once: true });
                        }));
                    } else if (el.tagName === 'VIDEO' && el.readyState < 1) {
                        mediaPromises.push(new Promise(function(resolve) {
                            el.addEventListener('loadeddata', resolve, { once: true });
                            el.addEventListener('error', resolve, { once: true });
                        }));
                    }
                });

                if (mediaPromises.length > 0) {
                    Promise.all(mediaPromises).then(function() {
                        var finalNewHeight = chatMessagesDiv.scrollHeight;
                        chatMessagesDiv.scrollTop = oldScrollTop + (finalNewHeight - oldScrollHeight);
                        setTimeout(function() {
                            chatMessagesDiv.style.scrollBehavior = 'smooth';
                            isLoadingOldMessages = false;
                        }, 50);
                    });
                    setTimeout(function() {
                        isLoadingOldMessages = false;
                        chatMessagesDiv.style.scrollBehavior = 'smooth';
                    }, 3000);
                } else {
                    setTimeout(function() {
                        chatMessagesDiv.style.scrollBehavior = 'smooth';
                        isLoadingOldMessages = false;
                    }, 50);
                }
            } else {
                chatMessagesDiv.style.scrollBehavior = 'auto';
                chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
                setTimeout(function() {
                    chatMessagesDiv.style.scrollBehavior = 'smooth';
                }, 50);
            }
        })
        .catch(function(error) {
            console.error("Error loading messages:");
        })
        .finally(function() {
            if (spinner) spinner.style.display = 'none';
            scrollDebounce = false;
        });
}

// ── Timestamp Toggle ──

function toggleTimestamp(messageElement) {
    document.querySelectorAll(".chat-timestamp").forEach(function(timestamp) {
        timestamp.classList.add("hidden");
    });
    var timestamp = messageElement.querySelector(".chat-timestamp");
    if (timestamp) {
        timestamp.classList.toggle("hidden");
    }
}

// ── Get Cleaned Message ──

function getCleanedMessage(chatInput) {
    if (!chatInput) return '';
    var html = chatInput.innerHTML;
    html = html.replace(/<div><br><\/div>/g, '\n')
               .replace(/<div>/g, '\n')
               .replace(/<\/div>/g, '')
               .replace(/<br>/g, '\n')
               .replace(/&nbsp;/g, ' ')
               .replace(/&#x200B;/g, '');
    var lines = html.split('\n').map(function(line) { return line.trim(); }).filter(Boolean);
    if (lines.length <= 3 && lines.join('').length <= 10) {
        return lines.join(' ');
    }
    return lines.join('\n');
}

// ── Insert Emoji ──

function insertEmojiIntoContentEditable(contentEditableElement, emoji) {
    if (!contentEditableElement) return;
    contentEditableElement.focus();
    var selection = window.getSelection();
    var range = selection.getRangeAt(0);
    var emojiNode = document.createTextNode(emoji);
    range.deleteContents();
    range.insertNode(emojiNode);
    range.setStartAfter(emojiNode);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
}

// ── Send Message ──

function sendMessage(userId, userName) {
    var chatInput = document.getElementById('chatInput-' + userId);
    var messageText = getCleanedMessage(chatInput);
    var fileInput = document.getElementById('chat-file-upload-' + userId);
    var file = fileInput.files[0];
    var isGroup = localStorage.getItem("activeIsGroup") === 'true';

    if (!messageText && !file) return;

    var clearInput = function() {
        chatInput.innerText = "";
        fileInput.value = "";
        var fp = document.getElementById('file-preview-' + userId);
        fp.innerHTML = "";
        fp.style.display = "none";
        editingMessageId = null;
        cancelEdit();
        cancelReply();
        delete chatInput.dataset.replyTo;
    };

    var replyTo = chatInput.dataset.replyTo ? parseInt(chatInput.dataset.replyTo) : null;

    if (file) {
        var reader = new FileReader();
        reader.onload = function (event) {
            var base64File = event.target.result;
            var filePayload = {
                message: messageText || "",
                file: { name: file.name, type: file.type, data: base64File }
            };
            if (editingMessageId) {
                filePayload.type = "edit_message";
                filePayload.message_id = editingMessageId;
            }
            if (replyTo) filePayload.reply_to = replyTo;
            sendViaWebSocket(userId, filePayload, isGroup);
            setTimeout(function() { scrollToBottom(userId); }, 100);
            clearInput();
        };
        reader.readAsDataURL(file);
    } else {
        var payload = editingMessageId ? {
            type: "edit_message",
            message_id: editingMessageId,
            message: messageText
        } : { message: messageText };
        if (replyTo) payload.reply_to = replyTo;
        sendViaWebSocket(userId, payload, isGroup);
        setTimeout(function() { scrollToBottom(userId); }, 100);
        clearInput();
    }
}

// ── Scroll Functions ──

function scrollToBottom(userId) {
    if (isLoadingOldMessages) return;
    var isGroup = localStorage.getItem("activeIsGroup") === 'true';
    var wrapperId = isGroup ? 'groupMessages-' + userId : 'chatMessages-' + userId;
    var chatMessagesDiv = document.getElementById(wrapperId);
    if (chatMessagesDiv) {
        requestAnimationFrame(function() {
            chatMessagesDiv.scrollTo({ top: chatMessagesDiv.scrollHeight, behavior: 'smooth' });
        });
    }
}

document.addEventListener("click", function () {
    hideAllReactionPickers();
});

// ── WebSocket Send ──

function sendViaWebSocket(userId, data, isGroup) {
    if (isGroup === null || isGroup === undefined) {
        isGroup = localStorage.getItem("activeIsGroup") === "true";
    }
    var socketKey = isGroup ? 'group_' + userId : userId;
    var socket = activeSockets[socketKey];
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(data));
    }
}

// ── Delete Conversation ──

function deleteConversation(userId) {
    if (!confirm("Are you sure you want to delete this conversation?")) return;
    var isGroup = localStorage.getItem("activeIsGroup") === "true";
    var endpoint = isGroup ? "/social/group_chat/delete_conversation/" : "/social/chat/delete_conversation/";
    var body = isGroup ? { id: userId } : { receiver: userId };

    fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
        body: JSON.stringify(body)
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        alert("Conversation deleted. It will reappear when a new message is sent.");
        localStorage.removeItem('activeChatId');
        localStorage.removeItem('activeChatName');
        localStorage.removeItem('activeChatPhoto');
        localStorage.removeItem('activeIsGroup');
        loadChatList();
        var chatPanel = document.getElementById("chat-panel");
        if (chatPanel) chatPanel.innerHTML = '<p class="text-center mt-4">Select a conversation</p>';
    })
    .catch(function(err) { console.error("Failed to delete conversation:"); });
}

// ── Connect WebSocket ──

function connectWebSocket(userId, onReady, isGroup) {
    onReady = onReady || null;
    isGroup = isGroup || false;

    var socketKey = isGroup ? 'group_' + userId : userId;
    var ids = [CURRENT_USER_ID, userId].sort(function(a, b) { return a - b; });
    var protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    var socketUrl = isGroup
        ? protocol + '://' + window.location.host + '/ws/group/' + userId + '/'
        : protocol + '://' + window.location.host + '/ws/chat/' + userId + '/';

    if (activeSockets[socketKey]) {
        if (activeSockets[socketKey].readyState === WebSocket.OPEN && onReady) {
            onReady();
        }
        return;
    }

    var socket = new WebSocket(socketUrl);
    activeSockets[socketKey] = socket;

    socket.onopen = function() {
        if (onReady) onReady();
    };

    socket.onmessage = function (e) {
        var data = JSON.parse(e.data);

        // Silent update guard: reactions and unsend are handled by their own blocks below
        // and must never fall through to the DM/group message rendering + unread/notification code.
        if (data.is_reaction) {
            if (data.type === "reaction_added" || data.type === "reaction_removed") {
                // Let it fall through to the reaction handlers below which return early
            } else {
                return;
            }
        }

        // Presence update
        if (data.type === "presence_update") {
            var pUserId = parseInt(data.user_id);
            userPresence[pUserId] = data.is_online;
            var contactItem = document.querySelector('.chat-contact[data-user-id="' + pUserId + '"]');
            var avatar = contactItem ? contactItem.querySelector(".avatar") : null;
            if (avatar) {
                if (data.is_online) {
                    avatar.classList.add("status-online");
                    avatar.classList.remove("status-offline");
                } else {
                    avatar.classList.remove("status-online");
                    avatar.classList.add("status-offline");
                }
            }
            var headerStatus = document.getElementById('status-text-' + pUserId);
            if (headerStatus) {
                if (data.is_online) {
                    headerStatus.textContent = "Active now";
                    headerStatus.classList.add("text-success");
                    headerStatus.classList.remove("text-muted");
                } else {
                    headerStatus.textContent = formatLastSeen(data.last_seen);
                    headerStatus.classList.remove("text-success");
                    headerStatus.classList.add("text-muted");
                }
            }
            return;
        }

        // Reaction added
        if (data.type === "reaction_added") {
            if (data.is_deleted) return;
            var displayDiv = document.getElementById('reaction-display-' + data.message_id);
            if (!displayDiv) return;
            var isMe = parseInt(data.user_id) === CURRENT_USER_ID;
            var serverCount = data.reaction_count;
            // Remove any previous reaction by this user (they switched emoji)
            var existingBadges = displayDiv.querySelectorAll(".reaction-badge");
            existingBadges.forEach(function(badge) {
                var users = badge.getAttribute("data-users") ? badge.getAttribute("data-users").split(',') : [];
                var index = users.indexOf(String(data.user_id));
                if (index > -1) {
                    users.splice(index, 1);
                    badge.setAttribute("data-users", users.join(','));
                    if (isMe) {
                        badge.classList.remove("reaction-mine");
                        badge.removeAttribute("data-user-reacted");
                    }
                    var count = users.length;
                    if (count <= 0) {
                        badge.remove();
                    } else {
                        updateReactionBadgeContent(badge, badge.getAttribute("data-emoji"), count);
                    }
                }
            });
            // Add the new reaction using server-provided count
            var rBadge = displayDiv.querySelector('.reaction-badge[data-emoji="' + data.emoji + '"');
            if (rBadge) {
                var rUsers = rBadge.getAttribute("data-users") ? rBadge.getAttribute("data-users").split(',').filter(Boolean) : [];
                if (rUsers.indexOf(String(data.user_id)) === -1) rUsers.push(String(data.user_id));
                rBadge.setAttribute("data-users", rUsers.join(','));
                updateReactionBadgeContent(rBadge, data.emoji, serverCount);
                if (isMe) { rBadge.classList.add("reaction-mine"); rBadge.setAttribute("data-user-reacted", "true"); }
            } else {
                var newBadge = buildReactionBadge(data.emoji, serverCount, [String(data.user_id)], isMe);
                displayDiv.appendChild(newBadge);
            }
            return;
        }

        // Reaction removed (toggle off)
        if (data.type === "reaction_removed") {
            var rmDisplayDiv = document.getElementById('reaction-display-' + data.message_id);
            if (!rmDisplayDiv) return;
            var serverCount = data.reaction_count;
            var rmBadge = rmDisplayDiv.querySelector('.reaction-badge[data-emoji="' + data.emoji + '"');
            if (rmBadge) {
                var rmUsers = rmBadge.getAttribute("data-users") ? rmBadge.getAttribute("data-users").split(',') : [];
                var rmIndex = rmUsers.indexOf(String(data.user_id));
                if (rmIndex > -1) rmUsers.splice(rmIndex, 1);
                if (parseInt(data.user_id) === CURRENT_USER_ID) {
                    rmBadge.classList.remove("reaction-mine");
                    rmBadge.removeAttribute("data-user-reacted");
                }
                // Use server count: if 0 unique users left, remove badge entirely
                if (serverCount <= 0 || rmUsers.length <= 0) {
                    rmBadge.remove();
                } else {
                    rmBadge.setAttribute("data-users", rmUsers.join(','));
                    updateReactionBadgeContent(rmBadge, data.emoji, serverCount);
                }
            }
            return;
        }

        // Message deleted
        if (data.type === "message_deleted") {
            var messageId = parseInt(data.message_id);
            var delIsGroup = localStorage.getItem("activeIsGroup") === "true";
            var targetId = parseInt(localStorage.getItem("activeChatId"));
            var isCurrentUser = parseInt(data.deleter_id) === CURRENT_USER_ID;
            var previewText = "";
            if (delIsGroup) {
                previewText = isCurrentUser ? "You unsent a message" : (data.deleted_by_name || "Someone") + " unsent a message";
            } else {
                previewText = isCurrentUser ? "You unsent a message" : "This message was unsent";
            }
            var allMessages = document.querySelectorAll('.chat-message-content[data-message-id="' + messageId + '"]');
            allMessages.forEach(function(messageEl) {
                var reactionDiv = messageEl.querySelector('#reaction-display-' + messageId);
                if (reactionDiv) reactionDiv.remove();
                var msgRow = messageEl.closest('.msg-row');
                if (msgRow) {
                    var hoverActions = msgRow.querySelector('.msg-hover-actions');
                    if (hoverActions) hoverActions.remove();
                }
                messageEl.innerHTML = '<div class="chat-message-text">' + previewText + '</div>';
                messageEl.classList.add("unsent-message");
                messageEl.style.color = "#6c757d";
                messageEl.style.fontStyle = "italic";
                messageEl.style.backgroundColor = "#f0f0f0";
            });
            var activeChatId = localStorage.getItem("activeChatId");
            var delChatInput = document.getElementById('chatInput-' + activeChatId);
            if (delChatInput && parseInt(delChatInput.dataset.replyTo) === messageId) {
                cancelReply();
            }
            if (editingMessageId === messageId) {
                cancelEdit();
            }
            var selector = delIsGroup
                ? '.chat-contact[data-user-id="' + targetId + '"][data-is-group="true"]'
                : '.chat-contact[data-user-id="' + targetId + '"]:not([data-is-group="true"])';
            var delContactItem = document.querySelector(selector);
            if (delContactItem) {
                var preview = delContactItem.querySelector(".chat-contact-content");
                var time = delContactItem.querySelector(".message-time");
                if (preview) preview.textContent = previewText;
                if (time) time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                if (delContactItem.parentNode) {
                    delContactItem.parentNode.insertBefore(delContactItem, delContactItem.parentNode.firstChild);
                }
            }
            return;
        }

        // Message edited
        if (data.type === "message_edited") {
            var editMsgEl = document.querySelector('.chat-message-content[data-message-id="' + data.message_id + '"]');
            if (editMsgEl) {
                var isSender = parseInt(data.sender_id) === CURRENT_USER_ID;
                var textDiv = editMsgEl.querySelector('.chat-message-text');
                if (textDiv) {
                    textDiv.innerHTML = escapeHtml(data.new_message).replace(/\n/g, '<br>');
                } else {
                    editMsgEl.innerHTML = '<div class="chat-message-text">' + escapeHtml(data.new_message).replace(/\n/g, '<br>') + '</div>';
                }
                var editMsgRow = editMsgEl.closest('.msg-row');
                if (editMsgRow) {
                    var oldActions = editMsgRow.querySelector('.msg-hover-actions');
                    if (oldActions) oldActions.remove();
                    editMsgRow.insertAdjacentHTML('beforeend', buildMsgActions(data.message_id, isSender, false, !!data.file, data.new_message, data.sender_name));
                }
                var column = editMsgEl.closest('.d-flex.flex-column');
                if (column) {
                    var editTimestamp = column.querySelector('.chat-timestamp');
                    if (editTimestamp && !editTimestamp.querySelector('.msg-edited-label')) {
                        editTimestamp.insertAdjacentHTML('afterbegin', '<span class="msg-edited-label">edited</span>');
                    }
                }
            }
            return;
        }

        // Typing indicator
        if (data.type === "typing") {
            // Typing means they're definitely online RIGHT NOW.
            if (data.is_typing) markPeerOnline(data.user_id);
            var typingIndicator = document.getElementById('typing-indicator-' + data.user_id);
            if (typingIndicator) {
                // Empty string lets the stylesheet's inline-flex layout win;
                // explicit "none" hides it when the peer stops typing.
                typingIndicator.style.display = data.is_typing ? "" : "none";
                if (data.is_typing) {
                    var typingChatDiv = document.getElementById('chatMessages-' + data.user_id);
                    if (!typingChatDiv) return;
                    var typingNearBottom = Math.abs(typingChatDiv.scrollTop + typingChatDiv.clientHeight - typingChatDiv.scrollHeight) < 100;
                    if (typingNearBottom) {
                        requestAnimationFrame(function() { typingChatDiv.scrollTop = typingChatDiv.scrollHeight; });
                    }
                }
            }
            return;
        }

        // Group message
        if (data.type === "group_message") {
            // The sender of this group message is online RIGHT NOW.
            if (parseInt(data.sender_id) !== CURRENT_USER_ID) markPeerOnline(data.sender_id);
            var groupId = data.group_id;
            var activeGroupId = localStorage.getItem("activeChatId");
            var activeIsGroup = localStorage.getItem("activeIsGroup") === 'true';
            var groupItem = document.querySelector('.chat-contact[data-user-id="' + groupId + '"][data-is-group="true"]');
            if (groupItem) {
                var gPreview = groupItem.querySelector(".chat-contact-content");
                var gTime = groupItem.querySelector(".message-time");
                if (gPreview) {
                    var gIsMine = parseInt(data.sender_id) === CURRENT_USER_ID;
                    var gPrefix = (gIsMine ? 'You' : data.sender_name) + ': ';
                    var gHasText = data.message && String(data.message).trim() !== "";
                    if (gHasText) {
                        var gPreviewText = gPrefix + data.message;
                        if (gPreviewText.length > 50) gPreviewText = gPreviewText.slice(0, 47) + '...';
                        gPreview.textContent = gPreviewText;
                    } else if (data.file) {
                        // Groups: "You sent a photo" vs "Jane sent a photo"
                        // (not "sent you a photo" — group, not direct).
                        var gIsImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(data.file);
                        var gIcon = gIsImage
                            ? '<i class="fas fa-image text-primary me-1"></i>'
                            : '<i class="fas fa-paperclip text-info me-1"></i>';
                        var gNoun = gIsImage ? 'photo' : 'file';
                        var gActor = gIsMine ? 'You' : (data.sender_name || 'Someone');
                        gPreview.innerHTML = gIcon + gActor + ' sent a ' + gNoun;
                    } else {
                        gPreview.textContent = gPrefix.replace(/:\s*$/, '');
                    }
                }
                if (gTime) gTime.textContent = data.timestamp;
                if (groupItem.parentNode) {
                    groupItem.parentNode.insertBefore(groupItem, groupItem.parentNode.firstChild);
                }
                if (!(activeIsGroup && parseInt(activeGroupId) === parseInt(groupId))) {
                    groupItem.classList.add("fw-bold", "unread");
                    if (parseInt(data.sender_id) !== CURRENT_USER_ID) {
                        inboxPlayNotification(groupId, true, data.message_id);
                    }
                }
            }
            if (!activeIsGroup || parseInt(activeGroupId) !== parseInt(groupId)) return;

            var gChatMessagesDiv = document.getElementById('groupMessages-' + groupId);
            var gChatMessagesList = document.getElementById('groupMessagesList-' + groupId);

            if (gChatMessagesList && data.created_at) {
                var lastWrapper = gChatMessagesList.querySelector('.chat-message-wrapper:last-child');
                var lastTime = lastWrapper ? lastWrapper.getAttribute('data-created-at') : null;
                var dividerHtml = getTimeDividerHtml(lastTime, data.created_at, 30);
                if (dividerHtml) gChatMessagesList.insertAdjacentHTML('beforeend', dividerHtml);
            }

            var gIsSender = parseInt(data.sender_id) === CURRENT_USER_ID;
            var gMessageDiv = document.createElement("div");
            gMessageDiv.className = "chat-message-wrapper d-flex align-items-end mb-2 ms-4 me-4 mt-2";
            gMessageDiv.classList.add(gIsSender ? "justify-content-end" : "justify-content-start");
            if (data.created_at) gMessageDiv.setAttribute('data-created-at', data.created_at);
            if (data.sender_id !== undefined && data.sender_id !== null) gMessageDiv.setAttribute('data-sender-id', String(data.sender_id));

            var groupReplyBlockHtml = buildReplyBlock(data.reply_to, gIsSender, data.sender_name);
            var groupContentHtml = buildMsgContent({
                msgId: data.message_id, file: data.file, message: data.message,
                isDeleted: data.is_deleted, isSent: gIsSender, isGroup: true, senderName: data.sender_name
            });

            gMessageDiv.innerHTML =
                '<div class="d-flex ' + (gIsSender ? 'flex-row-reverse' : 'flex-row') + ' align-items-end gap-2 mb-2">' +
                    (!gIsSender ? '<img class="profile-image rounded-circle me-2" src="' + (data.sender_photo || '/static/assets/img/def_user.jpg') + '" alt="Profile" style="width: 32px; height: 32px; object-fit: cover;">' : '') +
                    '<div class="d-flex flex-column ' + (gIsSender ? 'align-items-end' : 'align-items-start') + '">' +
                        groupReplyBlockHtml +
                        '<div class="msg-row ' + (gIsSender ? 'sent' : 'received') + '">' +
                            groupContentHtml +
                            buildMsgActions(data.message_id, gIsSender, data.is_deleted, !!data.file, data.message, data.sender_name) +
                        '</div>' +
                        '<div class="reaction-display d-flex align-items-center mt-1 gap-1 pe-1 justify-content-' + (gIsSender ? 'end' : 'start') + '" style="max-width: 70%;" id="reaction-display-' + data.message_id + '"></div>' +
                        '<small class="chat-timestamp text-500 mt-1 d-flex align-items-center gap-2" style="font-size: 10px;">' +
                            (data.is_edited ? '<span class="msg-edited-label">edited</span>' : '') +
                            data.timestamp +
                        '</small>' +
                    '</div>' +
                '</div>';

            if (gChatMessagesList && gChatMessagesDiv) {
                var existing = gChatMessagesList.querySelector('.chat-message-content[data-message-id="' + data.message_id + '"]');
                if (existing) {
                    var wrapper = existing.closest(".chat-message-wrapper");
                    if (wrapper) wrapper.replaceWith(gMessageDiv);
                } else {
                    gChatMessagesList.appendChild(gMessageDiv);
                }
                recomputeBurstEnds(gChatMessagesList);
                var gIsNearBottom = gChatMessagesDiv.scrollTop + gChatMessagesDiv.clientHeight >= gChatMessagesDiv.scrollHeight - 100;
                if (gIsSender || gIsNearBottom) {
                    requestAnimationFrame(function() { gChatMessagesDiv.scrollTop = gChatMessagesDiv.scrollHeight; });
                    var gScrollBtn = document.getElementById('scrollToBottomBtn-' + groupId);
                    if (gScrollBtn) gScrollBtn.classList.remove('visible');
                    resetUnreadBadge(groupId);
                } else {
                    showScrollToBottomButton(groupId);
                    if (!gIsSender) incrementUnreadBadge(groupId);
                }
            }
            return;
        }

        var isSent = parseInt(data.sender_id) === CURRENT_USER_ID;

        if (data.type === "read_receipt_notify") {
            var readIds = data.read_ids;
            readIds.forEach(function(id) {
                var icon = document.querySelector('.read-check[data-message-id="' + id + '"]');
                if (icon && icon.getAttribute("data-read") === "false") {
                    icon.classList.remove("fa-check", "text-muted");
                    icon.classList.add("fa-check-double", "text-primary");
                    icon.setAttribute("data-read", "true");
                } else {
                    pendingReadReceipts.add(id);
                }
            });
            return;
        }

        // Only process actual chat messages beyond this point — never reactions, edits, or unsend
        if (data.type !== "chat_message") return;

        // The peer just sent a message — they're online RIGHT NOW.
        // Flip their presence indicator before re-rendering the row.
        if (!isSent) markPeerOnline(data.sender_id);

        var otherUserId = isSent ? parseInt(data.receiver_id) : parseInt(data.sender_id);
        var dmChatMessagesDiv = document.getElementById('chatMessages-' + otherUserId);
        var dmChatMessagesList = document.getElementById('chatMessagesList-' + otherUserId);
        var isChatOpen = !!dmChatMessagesDiv;

        var dmContactItem = document.querySelector('.chat-contact[data-user-id="' + otherUserId + '"]');
        if (dmContactItem) {
            var dmPreview = dmContactItem.querySelector(".chat-contact-content");
            if (dmPreview) {
                var dmPrefix = isSent ? "You: " : (data.sender_name + ": ");
                var hasText = data.message && String(data.message).trim() !== "";
                if (hasText) {
                    var dmPreviewText = dmPrefix + data.message;
                    if (dmPreviewText.length > 50) dmPreviewText = dmPreviewText.slice(0, 47) + '...';
                    dmPreview.textContent = dmPreviewText;
                } else if (data.file) {
                    // "You sent a photo" / "Jane sent you a photo" — Messenger-style
                    // wording so the actor is unambiguous on both sides.
                    dmPreview.innerHTML = buildFilePreviewLabel(isSent, data.sender_name, data.file);
                } else {
                    dmPreview.textContent = dmPrefix.replace(/:\s*$/, '');
                }
            }
            var dmTime = dmContactItem.querySelector(".message-time");
            if (dmTime) dmTime.textContent = data.formatted_time;
            if (!isChatOpen) {
                dmContactItem.classList.add("unread", "fw-bold");
                if (!isSent) inboxPlayNotification(otherUserId, false, data.message_id);
                if (Notification.permission === "granted") {
                    var title = data.sender_name + ' sent you a message';
                    var body = data.message ? data.message.slice(0, 50) : "New file received";
                    var nIcon = data.sender_photo || "/static/assets/img/def_user.jpg";
                    new Notification(title, { body: body, icon: nIcon });
                }
            }
            if (dmContactItem.parentNode) {
                dmContactItem.parentNode.insertBefore(dmContactItem, dmContactItem.parentNode.firstChild);
            }
        }

        // Insert time divider for DM
        var dmMsgList = document.getElementById('chatMessagesList-' + otherUserId);
        if (dmMsgList && data.created_at) {
            var lastDmWrapper = dmMsgList.querySelector('.chat-message-wrapper:last-child');
            var lastDmTime = lastDmWrapper ? lastDmWrapper.getAttribute('data-created-at') : null;
            var dmDividerHtml = getTimeDividerHtml(lastDmTime, data.created_at, 30);
            if (dmDividerHtml) dmMsgList.insertAdjacentHTML('beforeend', dmDividerHtml);
        }

        var dmMessageDiv = document.createElement("div");
        dmMessageDiv.className = "chat-message-wrapper d-flex align-items-end mb-2 ms-4 me-4 mt-2";
        dmMessageDiv.classList.add(isSent ? "justify-content-end" : "justify-content-start");
        dmMessageDiv.style.position = "relative";
        if (data.created_at) dmMessageDiv.setAttribute('data-created-at', data.created_at);
        if (data.sender_id !== undefined && data.sender_id !== null) dmMessageDiv.setAttribute('data-sender-id', String(data.sender_id));

        var dmUserPhoto = data.sender_photo || '/static/assets/img/def_user.jpg';
        var dmReplyBlockHtml = buildReplyBlock(data.reply_to, isSent, data.sender_name);
        var dmContentHtml = buildMsgContent({
            msgId: data.message_id, file: data.file, message: data.message,
            isDeleted: data.is_deleted, isSent: isSent, isGroup: false, senderName: data.sender_name,
            isImage: data.is_image
        });

        dmMessageDiv.innerHTML =
            '<div class="d-flex ' + (isSent ? 'flex-row-reverse' : 'flex-row') + ' align-items-end gap-2 mb-2">' +
                (!isSent ? '<img class="profile-image rounded-circle me-2" src="' + dmUserPhoto + '" alt="Profile" style="width: 32px; height: 32px; object-fit: cover;">' : '') +
                '<div class="d-flex flex-column ' + (isSent ? 'align-items-end' : 'align-items-start') + '">' +
                    dmReplyBlockHtml +
                    '<div class="msg-row ' + (isSent ? 'sent' : 'received') + '">' +
                        dmContentHtml +
                        buildMsgActions(data.message_id, isSent, data.is_deleted, !!data.file, data.message, data.sender_name) +
                    '</div>' +
                    '<div class="reaction-display d-flex align-items-center mt-1 gap-1 justify-content-' + (isSent ? 'end' : 'start') + '" id="reaction-display-' + data.message_id + '"></div>' +
                    '<small class="chat-timestamp text-500 mt-1 d-flex align-items-center gap-2" style="font-size: 10px;">' +
                        (data.is_edited ? '<span class="msg-edited-label">edited</span>' : '') +
                        data.formatted_time +
                        (isSent ? '<i class="fas fa-check read-check text-muted ms-1" data-read="false" data-message-id="' + data.message_id + '"></i>' : '') +
                    '</small>' +
                '</div>' +
            '</div>';

        if (!dmChatMessagesDiv || !dmChatMessagesList) return;

        if (renderedMessageIds.has(data.message_id)) return;
        renderedMessageIds.add(data.message_id);

        dmChatMessagesList.appendChild(dmMessageDiv);
        recomputeBurstEnds(dmChatMessagesList);

        var dmIsSender = parseInt(data.sender_id) === CURRENT_USER_ID;
        var dmIsReceiver = !dmIsSender;
        var dmIsNearBottom = dmChatMessagesDiv.scrollTop + dmChatMessagesDiv.clientHeight >= dmChatMessagesDiv.scrollHeight - 100;

        if (dmIsSender || dmIsNearBottom) {
            requestAnimationFrame(function() { dmChatMessagesDiv.scrollTop = dmChatMessagesDiv.scrollHeight; });
            resetUnreadBadge(otherUserId);
        } else if (dmIsReceiver && !dmIsNearBottom) {
            showScrollToBottomButton(otherUserId);
            incrementUnreadBadge(otherUserId);
            inboxPlayNotification(otherUserId, false, data.message_id);
        }

        document.querySelectorAll(".read-check[data-read='false']").forEach(function(icon) {
            var mId = parseInt(icon.getAttribute("data-message-id"));
            if (pendingReadReceipts.has(mId)) {
                icon.classList.remove("fa-check", "text-muted");
                icon.classList.add("fa-check-double", "text-primary");
                icon.setAttribute("data-read", "true");
                pendingReadReceipts.delete(mId);
            }
        });

        if (parseInt(data.receiver_id) === CURRENT_USER_ID) {
            var dmIsOpen = !!dmChatMessagesDiv;
            var dmNearBot = dmChatMessagesDiv.scrollTop + dmChatMessagesDiv.clientHeight >= dmChatMessagesDiv.scrollHeight - 50;
            if (dmIsOpen && dmNearBot) {
                throttleReadReceipt(otherUserId);
            }
        }
    };

    var reconnectAttempts = 0;

    socket.onclose = function() {
        delete activeSockets[socketKey];
        reconnectAttempts++;
        var delay = Math.min(30000, 2000 * reconnectAttempts);
        setTimeout(function() { connectWebSocket(userId, null, isGroup); }, delay);
    };

    socket.onerror = function(e) {};
}

// ── Reaction Functions ──

function buildReactionBadge(emoji, count, userIds, isMe) {
    var badge = document.createElement("div");
    badge.className = "reaction-badge";
    if (isMe) { badge.classList.add("reaction-mine"); badge.setAttribute("data-user-reacted", "true"); }
    badge.setAttribute("data-emoji", emoji);
    badge.setAttribute("data-users", userIds.join(','));
    var emojiSpan = document.createElement("span");
    emojiSpan.className = "reaction-emoji";
    emojiSpan.textContent = emoji;
    badge.appendChild(emojiSpan);
    var countSpan = document.createElement("span");
    countSpan.className = "reaction-count";
    countSpan.textContent = count;
    badge.appendChild(countSpan);
    return badge;
}

function updateReactionBadgeContent(badge, emoji, count) {
    badge.innerHTML = '';
    var emojiSpan = document.createElement("span");
    emojiSpan.className = "reaction-emoji";
    emojiSpan.textContent = emoji;
    badge.appendChild(emojiSpan);
    var countSpan = document.createElement("span");
    countSpan.className = "reaction-count";
    countSpan.textContent = count;
    badge.appendChild(countSpan);
}

function sendReaction(messageId, emoji) {
    var activeChatId = localStorage.getItem("activeChatId");
    var isGroup = localStorage.getItem("activeIsGroup") === 'true';
    var socketKey = isGroup ? 'group_' + activeChatId : activeChatId;
    var socket = activeSockets[socketKey];
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "add_reaction", message_id: messageId, emoji: emoji }));
    }
}

function deleteMessage(messageId) {
    var activeChatId = localStorage.getItem("activeChatId");
    var isGroup = localStorage.getItem("activeIsGroup") === 'true';
    var socketKey = isGroup ? 'group_' + activeChatId : activeChatId;
    var socket = activeSockets[socketKey];
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "delete_message", message_id: messageId }));
    }
}

function editMessagePrompt(messageId, oldMessage) {
    cancelReply();
    var activeChatId = localStorage.getItem("activeChatId");
    var chatInput = document.getElementById('chatInput-' + activeChatId);
    if (!chatInput) return;
    editingMessageId = messageId;
    chatInput.innerText = oldMessage;
    var form = chatInput.closest("form");
    var editingNotice = form.querySelector(".editing-indicator");
    if (!editingNotice) {
        editingNotice = document.createElement("div");
        editingNotice.className = "editing-indicator text-muted small d-flex align-items-center gap-2";
        editingNotice.innerHTML = '<span>✏️ Editing message</span><span class="text-danger cursor-pointer" onclick="cancelEdit()">Cancel</span>';
        form.prepend(editingNotice);
    }
}

function cancelEdit() {
    editingMessageId = null;
    var activeChatId = localStorage.getItem("activeChatId");
    var chatInput = document.getElementById('chatInput-' + activeChatId);
    if (chatInput) chatInput.innerText = "";
    var form = chatInput ? chatInput.closest("form") : null;
    if (form) {
        var editingNotice = form.querySelector(".editing-indicator");
        if (editingNotice) editingNotice.remove();
    }
}

function scrollToLatest(userId) {
    if (isLoadingOldMessages) return;
    var isGroup = localStorage.getItem('activeIsGroup') === 'true';
    var chatMessagesDiv = document.getElementById(isGroup ? 'groupMessages-' + userId : 'chatMessages-' + userId);
    if (chatMessagesDiv) {
        requestAnimationFrame(function() {
            chatMessagesDiv.scrollTo({ top: chatMessagesDiv.scrollHeight, behavior: 'smooth' });
        });
    }
    var scrollBtn = document.getElementById('scrollToBottomBtn-' + userId);
    if (scrollBtn) scrollBtn.classList.remove('visible');
    resetUnreadBadge(userId);
}

function showScrollToBottomButton(userId) {
    var scrollBtn = document.getElementById('scrollToBottomBtn-' + userId);
    if (scrollBtn) scrollBtn.classList.add('visible');
}

function incrementUnreadBadge(userId) {
    unreadCounts[userId] = (unreadCounts[userId] || 0) + 1;
    var badge = document.getElementById('unreadBadge-' + userId);
    if (badge) {
        badge.textContent = unreadCounts[userId] > 99 ? '99+' : unreadCounts[userId];
        badge.classList.add('has-count');
    }
}

function resetUnreadBadge(userId) {
    unreadCounts[userId] = 0;
    var badge = document.getElementById('unreadBadge-' + userId);
    if (badge) {
        badge.textContent = '';
        badge.classList.remove('has-count');
    }
}

// Stop typing on window close
window.addEventListener("beforeunload", function() {
    var activeChatId = localStorage.getItem("activeChatId");
    var isGroup = localStorage.getItem("activeIsGroup") === 'true';
    var socketKey = isGroup ? 'group_' + activeChatId : activeChatId;
    var socket = activeSockets[socketKey];
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "stop_typing" }));
    }
});

// ── Reply Functions ──

function prepareReply(messageId, messageText, senderName) {
    if (editingMessageId !== null) cancelEdit();

    // Resolve active chat id with fallbacks: localStorage, then the
    // currently-rendered chat input in the DOM, then the closest
    // .card-chat-pane to the clicked message.
    var activeChatId = localStorage.getItem('activeChatId');
    var chatInput = activeChatId ? document.getElementById('chatInput-' + activeChatId) : null;

    if (!chatInput) {
        // Try to find any rendered chat input in the panel.
        chatInput = document.querySelector('[id^="chatInput-"]');
        if (chatInput) {
            activeChatId = chatInput.id.replace('chatInput-', '');
            try { localStorage.setItem('activeChatId', activeChatId); } catch (_) {}
        }
    }
    if (!chatInput) {
        console.warn('[prepareReply] no chat input found — cannot start reply');
        return;
    }

    var originalMessage = document.querySelector('.chat-message-content[data-message-id="' + messageId + '"]');
    if (originalMessage) {
        originalMessage.classList.add("border", "border-primary", "shadow-sm");
        setTimeout(function() { originalMessage.classList.remove("border", "border-primary", "shadow-sm"); }, 1500);
    }

    var previewBar = document.getElementById('reply-preview-' + activeChatId);
    var senderEl = document.getElementById('reply-preview-sender-' + activeChatId);
    var textEl = document.getElementById('reply-preview-text-' + activeChatId);
    if (previewBar && senderEl && textEl) {
        senderEl.textContent = 'Replying to ' + senderName;
        textEl.textContent = messageText;
        previewBar.classList.add('active');
        // Ensure inline display is not blocking the .active rule.
        previewBar.style.display = '';
    } else {
        console.warn('[prepareReply] preview bar not found for chat ' + activeChatId);
    }

    chatInput.focus();
    chatInput.dataset.replyTo = messageId;
}

// Mobile: tap a bubble to toggle its hover-action bar (reply/react/more).
// On desktop, hover already shows them. We gate by viewport so desktop
// users don't need an extra click. Tapping outside any bubble closes
// every open action bar.
(function () {
    function isNarrow() { return window.matchMedia('(max-width: 880px)').matches; }
    document.addEventListener('click', function (e) {
        if (!isNarrow()) return;
        // If they tapped an action button, leave the bar open and let
        // the inner button handle the click.
        if (e.target.closest('.msg-action-btn')) return;
        var bubble = e.target.closest('.chat-message-content');
        if (bubble) {
            var row = bubble.parentElement;
            if (row && row.classList.contains('msg-row')) {
                var was = row.classList.contains('show-actions');
                document.querySelectorAll('.msg-row.show-actions').forEach(function (r) {
                    r.classList.remove('show-actions');
                });
                if (!was) row.classList.add('show-actions');
            }
        } else {
            document.querySelectorAll('.msg-row.show-actions').forEach(function (r) {
                r.classList.remove('show-actions');
            });
        }
    });
})();

// Event-delegation fallback: even if the inline onclick fails to parse
// (e.g. an unescaped quote in the original message text breaks the
// HTML attribute), this captures clicks on any .reply-button and
// resolves the message id + text + sender from the DOM.
document.addEventListener('click', function (e) {
    var btn = e.target.closest('.reply-button');
    if (!btn) return;
    // If the inline handler already fired and set replyTo, skip.
    var msgRow = btn.closest('.msg-row');
    if (!msgRow) return;
    var bubble = msgRow.querySelector('.chat-message-content');
    if (!bubble) return;
    var messageId = bubble.getAttribute('data-message-id');
    if (!messageId) return;
    // Only fire the fallback if the inline onclick didn't already kick
    // off a reply (chatInput.dataset.replyTo would have been set).
    var anyInput = document.querySelector('[id^="chatInput-"]');
    if (anyInput && parseInt(anyInput.dataset.replyTo) === parseInt(messageId)) return;

    var msgText = (bubble.querySelector('.chat-message-text') || bubble).textContent.trim();
    // Sender name lives in a <strong> for group chats; for 1:1 received
    // messages it's the chat-content-header h5 text.
    var senderEl = msgRow.parentElement && msgRow.parentElement.querySelector('strong.text-info');
    var senderName = senderEl ? senderEl.textContent.trim() : '';
    if (!senderName) {
        var hdr = document.querySelector('#chat-panel .chat-content-header h5');
        senderName = hdr ? hdr.textContent.trim() : 'Message';
    }
    if (msgRow.classList.contains('sent')) senderName = 'yourself';
    prepareReply(parseInt(messageId), msgText, senderName);
});

function cancelReply() {
    var activeChatId = localStorage.getItem('activeChatId');
    var chatInput = document.getElementById('chatInput-' + activeChatId);
    if (chatInput) delete chatInput.dataset.replyTo;
    var previewBar = document.getElementById('reply-preview-' + activeChatId);
    if (previewBar) previewBar.classList.remove('active');
}

// ── Reaction Picker ──

function showReactionPicker(event, messageId) {
    event.preventDefault();
    event.stopPropagation();
    hideAllReactionPickers();
    var picker = document.createElement("div");
    picker.className = "reaction-picker shadow-sm border rounded";
    picker.style.position = "fixed";
    picker.style.zIndex = 9999;
    picker.style.display = "flex";
    picker.style.gap = "4px";

    var myReactedEmoji = null;
    var myBadge = document.querySelector('#reaction-display-' + messageId + ' .reaction-badge[data-user-reacted="true"]');
    if (myBadge) myReactedEmoji = myBadge.getAttribute("data-emoji");

    var emojis = ['👍', '❤️', '😂', '😮', '😢', '😡'];
    emojis.forEach(function(emoji) {
        var span = document.createElement("span");
        span.className = "reaction-emoji" + (emoji === myReactedEmoji ? " reaction-emoji-mine" : "");
        span.innerText = emoji;
        span.addEventListener("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            sendReaction(messageId, emoji);
            if (picker.parentNode) picker.parentNode.removeChild(picker);
        });
        picker.appendChild(span);
    });

    // Append off-screen first so we can measure, then clamp to viewport.
    picker.style.left = "-9999px";
    picker.style.top = "-9999px";
    document.body.appendChild(picker);

    var rect = picker.getBoundingClientRect();
    var pad = 8;
    var vw = window.innerWidth;
    var vh = window.innerHeight;

    var isSenderMsg = event.target.closest(".chat-message-wrapper")
        ? event.target.closest(".chat-message-wrapper").classList.contains("justify-content-end")
        : false;

    var left = isSenderMsg ? (event.clientX - rect.width) : event.clientX;
    var top = event.clientY - rect.height - 8;
    if (top < pad) top = event.clientY + 12;

    if (left < pad) left = pad;
    if (left + rect.width > vw - pad) left = vw - rect.width - pad;
    if (top + rect.height > vh - pad) top = vh - rect.height - pad;

    picker.style.left = left + "px";
    picker.style.top = top + "px";
}

function hideAllReactionPickers() {
    document.querySelectorAll(".reaction-picker").forEach(function(p) { p.remove(); });
}

// ── Group Chat Creation ──

function createGroupChat() {
    var groupName = document.getElementById("groupName").value.trim();
    var photoFile = document.getElementById("groupPhoto").files[0];
    var subjectSel = document.getElementById('groupFromSubject');
    var subjectId = subjectSel ? subjectSel.value : '';

    var formData = new FormData();
    formData.append('name', groupName);
    if (photoFile) formData.append('photo', photoFile);

    var url;
    if (subjectId) {
        // Teacher path: server resolves the roster from the subject.
        if (!groupName) {
            alert("Please enter a group name.");
            return;
        }
        formData.append('subject_id', subjectId);
        url = '/social/group_chat/create_from_subject/';
    } else {
        // Manual path: pick friends from the checklist.
        var selected = Array.from(document.querySelectorAll("#groupMembersList input:checked"))
                        .map(function(checkbox) { return parseInt(checkbox.value); });
        if (!groupName || selected.length === 0) {
            alert("Please enter a group name and select at least one member.");
            return;
        }
        selected.forEach(function(memberId) { formData.append('members', memberId); });
        url = '/social/group_chat/';
    }

    fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRFToken() },
        body: formData
    })
    .then(function(response) {
        if (!response.ok) return response.json().then(function(j) { throw new Error(j.error || "Failed to create group chat."); });
        return response.json();
    })
    .then(function(data) {
        var msg = "Group chat created successfully!";
        var memberCount = data.memberCount !== undefined ? data.memberCount : data.member_count;
        if (subjectId && memberCount) msg = "Group created with " + memberCount + " member" + (memberCount === 1 ? '' : 's') + ".";
        alert(msg);
        document.getElementById("createGroupForm").reset();
        if (subjectSel) subjectSel.value = '';
        var membersSection = document.getElementById('groupMembersSection');
        if (membersSection) membersSection.style.display = '';
        bootstrap.Modal.getInstance(document.getElementById("createGroupModal")).hide();
        loadChatList();
    })
    .catch(function(error) {
        alert("Error: " + (error.message || "Could not create group chat."));
    });
}

// ── Group Chat Info Offcanvas ──

document.addEventListener("DOMContentLoaded", function () {
    document.body.addEventListener("click", async function (e) {
        var button = e.target.closest(".btn-chat-info");
        if (!button) return;
        var groupId = button.getAttribute("data-index");
        var membersList = document.getElementById("groupChatMembersList");
        var addSection = document.getElementById("groupAddMemberSection");
        var offcanvas = new bootstrap.Offcanvas(document.getElementById("groupChatInfoOffcanvas"));
        offcanvas.show();
        membersList.setAttribute('data-group-id', groupId);
        membersList.innerHTML = "<p class='text-muted'>Loading members...</p>";
        try {
            var res = await fetch('/social/group_chat/' + groupId + '/members/');
            var payload = await res.json();
            // Tolerate both old (array) and new ({members, ...}) shapes,
            // and the camelCase renderer's key conversion.
            var members = Array.isArray(payload) ? payload : (payload.members || []);
            var isCreator = !!(payload.currentUserIsCreator ?? payload.current_user_is_creator);
            var creatorId = payload.creatorId ?? payload.creator_id;

            if (addSection) addSection.style.display = isCreator ? '' : 'none';

            if (!members.length) {
                membersList.innerHTML = "<p class='text-muted'>No members found.</p>";
                return;
            }
            var currentUserId = parseInt(document.body.dataset.currentUserId);
            membersList.innerHTML = members.map(function(member) {
                var memberIsCreator = !!(member.isCreator ?? member.is_creator) || member.id === creatorId;
                var actionButton = '';
                if (member.id === currentUserId && !memberIsCreator) {
                    actionButton = '<button class="btn btn-sm btn-outline-danger ms-auto leave-btn" data-id="' + member.id + '" data-group="' + groupId + '">Leave</button>';
                } else if (isCreator && member.id !== currentUserId) {
                    actionButton = '<button class="btn btn-sm btn-outline-danger ms-auto remove-btn" data-id="' + member.id + '" data-group="' + groupId + '">Remove</button>';
                }
                var roleLabel = memberIsCreator ? 'Creator' : (member.role === 'admin' ? 'Admin' : 'Member');
                return '<div class="d-flex align-items-center mb-3" data-member-id="' + member.id + '">' +
                    '<img src="' + (member.photo || '/static/assets/img/def_user.jpg') + '" alt="' + member.name + '" class="rounded-circle me-3" style="width: 40px; height: 40px; object-fit: cover;">' +
                    '<div class="flex-grow-1"><div class="fw-bold">' + (member.name || 'Unnamed User') + '</div><small class="text-muted">' + roleLabel + '</small></div>' +
                    actionButton + '</div>';
            }).join("");
        } catch (err) {
            membersList.innerHTML = "<p class='text-danger'>Failed to load members.</p>";
        }
    });

    // ── Add-member search (creator only) ──
    var addSearchTimer = null;
    document.body.addEventListener("input", function(e) {
        if (e.target.id !== 'groupAddMemberSearch') return;
        var input = e.target;
        var results = document.getElementById('groupAddMemberResults');
        var membersList = document.getElementById('groupChatMembersList');
        var groupId = membersList && membersList.getAttribute('data-group-id');
        if (!groupId) return;
        var q = input.value.trim();
        clearTimeout(addSearchTimer);
        addSearchTimer = setTimeout(async function() {
            try {
                var url = '/social/group_chat/' + groupId + '/eligible_users/' + (q ? ('?q=' + encodeURIComponent(q)) : '');
                var r = await fetch(url);
                if (!r.ok) { results.style.display = 'none'; return; }
                var users = await r.json();
                if (!users.length) {
                    results.innerHTML = '<div class="p-2 text-muted" style="font-size:12px;">No friends to add.</div>';
                    results.style.display = '';
                    return;
                }
                results.innerHTML = users.map(function(u) {
                    return '<div class="d-flex align-items-center p-2 add-member-result" style="cursor:pointer;border-bottom:1px solid rgba(0,0,0,.05);" data-id="' + u.id + '" data-name="' + (u.name || '').replace(/"/g,'&quot;') + '" data-group="' + groupId + '">' +
                        '<img src="' + (u.photo || '/static/assets/img/def_user.jpg') + '" class="rounded-circle me-2" style="width:30px;height:30px;object-fit:cover;">' +
                        '<div class="flex-grow-1" style="font-size:13px;">' + (u.name || u.username || 'Unnamed') + '</div>' +
                        '<button class="btn btn-sm btn-primary add-member-btn" data-id="' + u.id + '" data-group="' + groupId + '">Add</button>' +
                    '</div>';
                }).join('');
                results.style.display = '';
            } catch (_) { results.style.display = 'none'; }
        }, 200);
    });

    document.body.addEventListener("click", async function(e) {
        var btn = e.target.closest('.add-member-btn');
        if (!btn) return;
        e.stopPropagation();
        var uid = btn.dataset.id, gid = btn.dataset.group;
        btn.disabled = true; btn.textContent = 'Adding…';
        try {
            var r = await fetch('/social/group_chat/' + gid + '/add_members/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
                body: JSON.stringify({ user_ids: [parseInt(uid, 10)] })
            });
            if (!r.ok) throw 0;
            // Re-trigger the member list refresh by clicking the info button.
            var infoBtn = document.querySelector('.btn-chat-info[data-index="' + gid + '"]');
            if (infoBtn) infoBtn.click();
            document.getElementById('groupAddMemberSearch').value = '';
            document.getElementById('groupAddMemberResults').style.display = 'none';
        } catch (_) {
            btn.disabled = false; btn.textContent = 'Add';
            alert('Failed to add member.');
        }
    });

    document.addEventListener("click", function(e) {
        // Close add-member results when clicking outside
        var input = document.getElementById('groupAddMemberSearch');
        var results = document.getElementById('groupAddMemberResults');
        if (!input || !results) return;
        if (e.target === input || results.contains(e.target)) return;
        results.style.display = 'none';
    });

    // Handle Leave
    document.body.addEventListener("click", async function (e) {
        if (e.target.classList.contains("leave-btn")) {
            var groupId = e.target.dataset.group;
            var res = await fetch('/social/group_chat/' + groupId + '/leave/', {
                method: "POST",
                headers: { "X-CSRFToken": getCSRFToken() }
            });
            var data = await res.json();
            alert(data.message || "You left the group.");
            location.reload();
        }
    });

    // Handle Remove
    document.body.addEventListener("click", async function (e) {
        if (e.target.classList.contains("remove-btn")) {
            var memberId = e.target.dataset.id;
            var groupId = e.target.dataset.group;
            var res = await fetch('/social/group_chat/' + groupId + '/remove_member/', {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
                body: JSON.stringify({ user_id: memberId })
            });
            var data = await res.json();
            alert(data.message || "Member removed.");
            e.target.closest(".d-flex").remove();
        }
    });
});

// Auto-open a direct conversation when arriving with ?user=<id>
document.addEventListener("DOMContentLoaded", function () {
    var params = new URLSearchParams(window.location.search);
    var targetUser = params.get("user");
    if (!targetUser) return;
    function tryOpen(attempt) {
        var sel = '.chat-contact[data-user-id="' + targetUser + '"]:not([data-is-group="true"])';
        var item = document.querySelector(sel);
        if (item) { item.click(); return; }
        if (attempt < 20) setTimeout(function(){ tryOpen(attempt + 1); }, 250);
    }
    tryOpen(0);
});
