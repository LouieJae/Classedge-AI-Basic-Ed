/* cl-material-viewer.js — unified preview modal for learning materials.
 *
 * Single dispatcher that opens the right renderer for the file/URL it's
 * given. One modal, one API, four render paths.
 *
 * PUBLIC API
 * ──────────
 *   ClMaterialViewer.open({
 *     name:        'Lecture 3 slides',
 *     fileUrl:     '/media/foo.pdf',      // local file (optional)
 *     url:         'https://...',         // external URL (optional)
 *     iframeHtml:  '<iframe ...></iframe>', // raw custom embed (optional)
 *     onedriveUrl: '...',                  // OneDrive embed URL (optional)
 *     allowDownload: true,
 *     downloadUrl: '/media/foo.pdf'        // optional override
 *   })
 *
 *   ClMaterialViewer.close()
 *
 * The dispatcher inspects the inputs in this priority order:
 *   1. iframeHtml         → inject raw HTML (Canva, Slides, Sway embeds)
 *   2. onedriveUrl        → OneDrive embed iframe (Office docs uploaded
 *                           with Microsoft account linked)
 *   3. fileUrl extension  → switch on extension:
 *                              .pdf            → native browser PDF iframe
 *                              .mp4/.webm/etc. → Plyr video player
 *                              .mp3/.wav/etc.  → Plyr audio player
 *                              .ppt/.docx/etc. → Office Online viewer
 *                              .png/.jpg/etc.  → native <img>
 *                              other           → native iframe
 *   4. url                → YouTube/Vimeo via Plyr, else native iframe
 *   5. nothing            → empty state
 *
 * DEPENDENCIES (loaded from CDN by the base template)
 *   - Plyr v3+ for unified video/audio/YouTube/Vimeo
 *   - Native iframe for PDFs (browser-built-in PDF viewer)
 *
 * OFFICE DOCS (PPT/DOC/XLS) — inline preview only when an
 * `onedrive_embed_url` is on the material (populated when the uploader
 * has Microsoft account linked). Without it the modal opens a plain
 * iframe of the file URL, which most browsers turn into a download.
 * That matches the existing student-modal behavior and works in dev
 * (localhost) — unlike the public `view.officeapps.live.com` viewer
 * which needs the file to be reachable from Microsoft's servers.
 */
(function () {
  'use strict';

  var EXT_VIDEO = ['mp4', 'webm', 'm4v', 'mov', 'ogv', 'ogg'];
  var EXT_AUDIO = ['mp3', 'wav', 'm4a', 'aac', 'oga', 'opus'];
  var EXT_IMAGE = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'avif'];
  var EXT_OFFICE = ['ppt', 'pptx', 'doc', 'docx', 'xls', 'xlsx'];
  var EXT_PDF = ['pdf'];

  var modal = null;
  var plyr = null; // current Plyr instance, if any

  function extOf(url) {
    if (!url) return '';
    var clean = String(url).split('?')[0].split('#')[0];
    var m = clean.match(/\.([a-z0-9]+)$/i);
    return m ? m[1].toLowerCase() : '';
  }

  function isAbsoluteUrl(u) {
    return /^https?:\/\//i.test(u);
  }

  function absolute(u) {
    if (!u) return u;
    if (isAbsoluteUrl(u)) return u;
    var a = document.createElement('a');
    a.href = u;
    return a.href;
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function youTubeId(u) {
    var m = u.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{6,})/);
    return m ? m[1] : null;
  }
  function vimeoId(u) {
    var m = u.match(/vimeo\.com\/(?:video\/)?(\d{4,})/);
    return m ? m[1] : null;
  }

  /* ── Modal scaffolding ────────────────────────────────────────── */

  function ensureModal() {
    if (modal) return modal;
    modal = document.createElement('div');
    modal.className = 'cmv-backdrop';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-hidden', 'true');
    modal.innerHTML =
      '<div class="cmv-shell">' +
        '<header class="cmv-head">' +
          '<h2 class="cmv-title" id="cmvTitle"></h2>' +
          '<div class="cmv-actions">' +
            '<a class="cmv-action cmv-open" target="_blank" rel="noopener" title="Open in new tab" hidden>' +
              '<i class="fas fa-arrow-up-right-from-square"></i>' +
            '</a>' +
            '<a class="cmv-action cmv-download" download title="Download" hidden>' +
              '<i class="fas fa-download"></i>' +
            '</a>' +
            '<button type="button" class="cmv-action cmv-fullscreen" title="Toggle full-page">' +
              '<i class="fas fa-expand"></i>' +
            '</button>' +
            '<button type="button" class="cmv-action cmv-close" aria-label="Close viewer">' +
              '<i class="fas fa-xmark"></i>' +
            '</button>' +
          '</div>' +
        '</header>' +
        '<div class="cmv-body" id="cmvBody"></div>' +
      '</div>';
    document.body.appendChild(modal);

    modal.addEventListener('click', function (e) {
      if (e.target === modal) close();
    });
    modal.querySelector('.cmv-close').addEventListener('click', close);
    modal.querySelector('.cmv-fullscreen').addEventListener('click', function () {
      modal.classList.toggle('is-full');
      var icon = this.querySelector('i');
      if (icon) icon.className = modal.classList.contains('is-full')
        ? 'fas fa-compress' : 'fas fa-expand';
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('is-open')) close();
    });
    return modal;
  }

  /* ── Render paths ─────────────────────────────────────────────── */

  function renderImage(body, src, name) {
    body.innerHTML = '<div class="cmv-image-wrap">' +
      '<img src="' + escapeHtml(src) + '" alt="' + escapeHtml(name || '') + '" />' +
    '</div>';
  }

  function renderVideo(body, src) {
    body.innerHTML = '<video controls playsinline class="cmv-plyr" preload="metadata">' +
      '<source src="' + escapeHtml(src) + '" />' +
    '</video>';
    initPlyr(body.querySelector('video'));
  }

  function renderAudio(body, src) {
    body.innerHTML = '<div class="cmv-audio-wrap">' +
      '<audio controls class="cmv-plyr" preload="metadata">' +
        '<source src="' + escapeHtml(src) + '" />' +
      '</audio>' +
    '</div>';
    initPlyr(body.querySelector('audio'));
  }

  function renderYouTube(body, id) {
    body.innerHTML = '<div class="cmv-plyr" data-plyr-provider="youtube" data-plyr-embed-id="' + escapeHtml(id) + '"></div>';
    initPlyr(body.firstElementChild);
  }

  function renderVimeo(body, id) {
    body.innerHTML = '<div class="cmv-plyr" data-plyr-provider="vimeo" data-plyr-embed-id="' + escapeHtml(id) + '"></div>';
    initPlyr(body.firstElementChild);
  }

  function renderPdf(body, src) {
    // Native iframe — modern browsers ship a usable PDF viewer.
    body.innerHTML = '<iframe class="cmv-iframe" src="' + escapeHtml(src) + '#view=FitH" allow="fullscreen"></iframe>';
  }

  function renderIframe(body, src) {
    body.innerHTML = '<iframe class="cmv-iframe" src="' + escapeHtml(src) + '" allow="fullscreen; autoplay; clipboard-write; encrypted-media" referrerpolicy="no-referrer-when-downgrade"></iframe>';
  }

  function renderRawEmbed(body, html) {
    body.innerHTML = '<div class="cmv-embed-wrap">' + html + '</div>';
  }

  function renderEmpty(body) {
    body.innerHTML = '<div class="cmv-empty">' +
      '<i class="fas fa-folder-open"></i>' +
      '<p>This material has no previewable content.</p>' +
    '</div>';
  }

  /* ── Plyr lifecycle ──────────────────────────────────────────── */

  function initPlyr(el) {
    if (!el || typeof window.Plyr !== 'function') return;
    destroyPlyr();
    try {
      plyr = new window.Plyr(el, {
        controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'captions', 'settings', 'pip', 'fullscreen'],
        keyboard: { focused: true, global: false },
        tooltips: { controls: true, seek: true },
      });
    } catch (_) { /* swallow — Plyr will still emit native controls */ }
  }
  function destroyPlyr() {
    if (plyr) {
      try { plyr.destroy(); } catch (_) {}
      plyr = null;
    }
  }

  /* ── Dispatcher ──────────────────────────────────────────────── */

  function dispatch(body, opts) {
    if (opts.iframeHtml) return renderRawEmbed(body, opts.iframeHtml);
    if (opts.onedriveUrl) return renderIframe(body, opts.onedriveUrl);

    if (opts.fileUrl) {
      var ext = extOf(opts.fileUrl);
      if (EXT_IMAGE.indexOf(ext) !== -1) return renderImage(body, opts.fileUrl, opts.name);
      if (EXT_VIDEO.indexOf(ext) !== -1) return renderVideo(body, opts.fileUrl);
      if (EXT_AUDIO.indexOf(ext) !== -1) return renderAudio(body, opts.fileUrl);
      if (EXT_PDF.indexOf(ext) !== -1) return renderPdf(body, opts.fileUrl);
      // Office docs without an onedrive_embed_url have no in-browser
      // viewer that works on localhost — fall through to plain iframe,
      // which lets the browser handle/download the file. Inline preview
      // requires onedriveUrl to be set on the material.
      return renderIframe(body, opts.fileUrl);
    }

    if (opts.url) {
      var yt = youTubeId(opts.url);
      if (yt) return renderYouTube(body, yt);
      var vm = vimeoId(opts.url);
      if (vm) return renderVimeo(body, vm);
      return renderIframe(body, opts.url);
    }

    renderEmpty(body);
  }

  /* ── Public API ──────────────────────────────────────────────── */

  function open(opts) {
    opts = opts || {};
    ensureModal();
    var title = modal.querySelector('#cmvTitle');
    var body = modal.querySelector('#cmvBody');
    var openLink = modal.querySelector('.cmv-open');
    var dlLink = modal.querySelector('.cmv-download');

    title.textContent = opts.name || 'Material preview';

    // External-link affordance — points to the underlying file/URL.
    var external = opts.url || opts.fileUrl || opts.onedriveUrl;
    if (external) {
      openLink.href = external;
      openLink.hidden = false;
    } else {
      openLink.hidden = true;
    }

    // Download — only when explicitly allowed and a file is involved.
    if (opts.allowDownload && (opts.downloadUrl || opts.fileUrl)) {
      dlLink.href = opts.downloadUrl || opts.fileUrl;
      dlLink.hidden = false;
    } else {
      dlLink.hidden = true;
    }

    body.innerHTML = '';
    dispatch(body, opts);

    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('cmv-lock-scroll');
  }

  function close() {
    if (!modal) return;
    destroyPlyr();
    modal.classList.remove('is-open', 'is-full');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('cmv-lock-scroll');
    var icon = modal.querySelector('.cmv-fullscreen i');
    if (icon) icon.className = 'fas fa-expand';
    var body = modal.querySelector('#cmvBody');
    if (body) body.innerHTML = '';
  }

  /* ── Data-attribute binding ──────────────────────────────────── */
  /* Any element with [data-cmv-open] becomes a preview trigger. Reads
     opts from data-cmv-* attributes; stops propagation so it doesn't
     fight with an outer card-click handler. */
  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-cmv-open]');
    if (!trigger) return;
    e.preventDefault();
    e.stopPropagation();
    open({
      name: trigger.getAttribute('data-cmv-name') || trigger.getAttribute('title') || '',
      fileUrl: trigger.getAttribute('data-cmv-file') || '',
      url: trigger.getAttribute('data-cmv-url') || '',
      iframeHtml: trigger.getAttribute('data-cmv-embed') || '',
      onedriveUrl: trigger.getAttribute('data-cmv-onedrive') || '',
      allowDownload: trigger.getAttribute('data-cmv-download') === '1',
      downloadUrl: trigger.getAttribute('data-cmv-download-url') || '',
    });
  });

  window.ClMaterialViewer = { open: open, close: close };
})();
