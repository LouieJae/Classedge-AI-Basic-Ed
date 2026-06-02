  document.addEventListener('DOMContentLoaded', function () {
    // ── File preview modal wiring ───────────────────────────────
    // Intercepts clicks on .lesson-link[data-preview-src] (file/onedrive
    // lessons), iframes the preview URL inline instead of navigating away.
    const fpBackdrop = document.getElementById('filePreviewBackdrop');
    const fpModal = document.getElementById('filePreviewModal');
    const fpFrame = document.getElementById('filePreviewFrame');
    const fpTitleText = document.getElementById('filePreviewTitleText');
    const fpOpenNew = document.getElementById('filePreviewOpenNew');
    const fpClose = document.getElementById('filePreviewClose');
    const fpLoader = document.getElementById('filePreviewLoader');
    const fpLoaderHint = document.getElementById('filePreviewLoaderHint');
    const fpInstructions = document.getElementById('filePreviewInstructions');

    // Reparent to <body> so position:fixed anchors to the viewport
    // regardless of any ancestor transform/filter (same trick the other
    // rl-modal pages use).
    if (fpModal) document.body.appendChild(fpModal);
    if (fpBackdrop) document.body.appendChild(fpBackdrop);

    function focusFrame() {
      if (!fpFrame) return;
      try { fpFrame.focus({ preventScroll: true }); } catch (e) {}
      try { fpFrame.contentWindow && fpFrame.contentWindow.focus(); } catch (e) {}
    }

    if (fpFrame) {
      fpFrame.addEventListener('load', function () {
        // about:blank fires load too — only hide once the real src is loaded.
        if (fpFrame.src && fpFrame.src !== 'about:blank') {
          fpLoader && fpLoader.classList.add('is-hidden');
          // Re-focus once the viewer mounts in case OneDrive's bootstrapping
          // pulled focus away while loading.
          requestAnimationFrame(focusFrame);
        }
      });
    }

    // Some parent-page keyboard handlers (or the lesson-link itself
    // retaining :focus) eat arrow-key input. When the modal is open,
    // route ←/→/Space/PageDn/PageUp into the iframe by re-focusing it
    // and letting the event continue inside. We only forward, never
    // preventDefault, so the modal's own Esc handler still wins.
    document.addEventListener('keydown', function (e) {
      if (!fpModal || !fpModal.classList.contains('show')) return;
      const NAV = ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','PageUp','PageDown','Home','End',' ','Spacebar'];
      if (!NAV.includes(e.key)) return;
      const active = document.activeElement;
      // If focus is already inside the iframe (or on it), let it through.
      if (active === fpFrame) return;
      // Otherwise the parent doc is eating the key — hand it to the iframe.
      focusFrame();
    }, true);

    function setInstructionsVisible(visible) {
      if (!fpInstructions) return;
      fpInstructions.hidden = !visible;
    }

    function openPreview(src, title) {
      if (!src || !fpModal) return;
      if (fpTitleText) fpTitleText.textContent = title || 'Preview';
      if (fpOpenNew) fpOpenNew.href = src;
      // Show the loader BEFORE we set the iframe src so the user gets
      // immediate feedback while OneDrive/PDF.js boots.
      if (fpLoader) fpLoader.classList.remove('is-hidden');
      const isOffice = /onedrive\.live|sharepoint|office\.com|1drv/i.test(src);
      if (fpLoaderHint) {
        // PPTX/DOCX go through OneDrive's viewer and are noticeably slower
        // than PDFs — set expectations.
        fpLoaderHint.textContent = isOffice
          ? 'Office files take a few seconds to render in OneDrive.'
          : 'Large files may take a few seconds.';
      }
      // Show the instruction strip only for cross-origin viewers
      // (OneDrive). Same-origin PDF.js takes keyboard input fine via the
      // programmatic focus call below, so no instructions needed there.
      setInstructionsVisible(isOffice);
      fpFrame.src = src;
      fpBackdrop.classList.add('show');
      fpModal.classList.add('show');
      document.body.style.overflow = 'hidden';
      // Focus the iframe synchronously inside the user-gesture stack so
      // browsers permit keystroke delivery into cross-origin viewers.
      // Without this, ← / → / Space stay on the parent page until the
      // user clicks the slide first.
      focusFrame();
    }
    function closePreview() {
      if (!fpModal) return;
      fpBackdrop.classList.remove('show');
      fpModal.classList.remove('show');
      document.body.style.overflow = '';
      setInstructionsVisible(false);
      setTimeout(() => {
        fpFrame.src = 'about:blank';
        if (fpLoader) fpLoader.classList.remove('is-hidden');
      }, 220);
    }

    document.querySelectorAll('.lesson-link[data-preview-src]').forEach(link => {
      link.addEventListener('click', function (e) {
        // Ctrl/Cmd/middle-click should still allow opening in a new tab.
        if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return;
        e.preventDefault();
        openPreview(link.getAttribute('data-preview-src'), link.getAttribute('data-preview-title'));
      });
    });

    if (fpClose) fpClose.addEventListener('click', closePreview);
    if (fpBackdrop) fpBackdrop.addEventListener('click', closePreview);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && fpModal && fpModal.classList.contains('show')) closePreview();
    });

    const list = document.querySelector('.lesson-list');
    if (list) {
      list.addEventListener('click', async function (e) {
        const btn = e.target.closest('.js-delete-module');
        if (!btn) return;
        e.preventDefault();
        const form = btn.closest('form');
        const name = btn.dataset.filename || 'this material';
        try {
          const result = await Swal.fire({
            title: 'Delete this material?',
            html: `Delete "<strong>${name}</strong>"? This cannot be undone.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, delete',
            cancelButtonText: 'Cancel',
            confirmButtonColor: '#c08479',
            cancelButtonColor: '#6c7080',
            reverseButtons: true,
            focusCancel: true,
          });
          if (result.isConfirmed) {
            btn.disabled = true;
            form.submit();
          }
        } catch (err) {
          if (confirm(`Delete "${name}"? This cannot be undone.`)) form.submit();
        }
      });
    }

    const taList = document.getElementById('taList');
    if (taList) {
      taList.addEventListener('click', async function (e) {
        const btn = e.target.closest('.js-delete-assessment');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        const form = btn.closest('form');
        const name = btn.dataset.name || 'this assessment';
        try {
          const result = await Swal.fire({
            title: 'Delete this assessment?',
            html: `Delete "<strong>${name}</strong>"? This cannot be undone.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, delete',
            cancelButtonText: 'Cancel',
            confirmButtonColor: '#c08479',
            cancelButtonColor: '#6c7080',
            reverseButtons: true,
            focusCancel: true,
          });
          if (result.isConfirmed) {
            btn.disabled = true;
            form.submit();
          }
        } catch (err) {
          if (confirm(`Delete "${name}"? This cannot be undone.`)) form.submit();
        }
      });
    }

    // Close import dropdown on outside click or Escape
    const importMenu = document.querySelector('.import-menu');
    if (importMenu) {
      document.addEventListener('click', function (e) {
        if (importMenu.open && !importMenu.contains(e.target)) {
          importMenu.open = false;
        }
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && importMenu.open) importMenu.open = false;
      });
    }

    const taListForDelete = document.getElementById('taList');
    if (taListForDelete) {
      taListForDelete.addEventListener('click', async function (e) {
        const btn = e.target.closest('.js-delete-assessment');
        if (!btn) return;
        e.preventDefault();
        const form = btn.closest('form');
        const name = btn.dataset.name || 'this assessment';
        try {
          const result = await Swal.fire({
            title: 'Delete this assessment?',
            html: `Delete "<strong>${name}</strong>"? Students who have already submitted will block this delete; others will be removed permanently.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, delete',
            cancelButtonText: 'Cancel',
            confirmButtonColor: '#c08479',
            cancelButtonColor: '#6c7080',
            reverseButtons: true,
            focusCancel: true,
          });
          if (result.isConfirmed) {
            btn.disabled = true;
            form.submit();
          }
        } catch (err) {
          if (confirm(`Delete "${name}"? This cannot be undone.`)) form.submit();
        }
      });
    }

    // ── Assessment filter chips (teacher Assessments tab) ──────────
    const taList = document.getElementById('taList');
    if (taList) {
      document.querySelectorAll('.ta-filter').forEach(function (chip) {
        chip.addEventListener('click', function () {
          document.querySelectorAll('.ta-filter').forEach(function (c) { c.classList.remove('is-active'); });
          chip.classList.add('is-active');
          taList.dataset.filter = chip.dataset.taFilter || 'all';
        });
      });
    }

    // ── "New assessment" type dropdown (teacher Assessments tab) ──
    const llAdd = document.getElementById('llAddAssessment');
    const llAddTrigger = document.getElementById('llAddAssessmentTrigger');
    if (llAdd && llAddTrigger) {
      function closeLlAdd() {
        llAdd.classList.remove('is-open');
        llAddTrigger.setAttribute('aria-expanded', 'false');
      }
      llAddTrigger.addEventListener('click', function (e) {
        e.stopPropagation();
        const open = llAdd.classList.toggle('is-open');
        llAddTrigger.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      document.addEventListener('click', function (e) {
        if (!llAdd.contains(e.target)) closeLlAdd();
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeLlAdd();
      });
    }

    // ── "New conference" modal ──
    const confModal = document.getElementById('conferenceModal');
    const confOpen = document.getElementById('openConferenceModal');
    const confClose = document.getElementById('closeConferenceModal');
    if (confModal && confOpen) {
      // Move the modal to <body> so position:fixed truly covers the viewport,
      // not just the content area. Ancestors inside .app can otherwise create
      // a containing block that clips the backdrop.
      if (confModal.parentNode !== document.body) {
        document.body.appendChild(confModal);
      }
      confOpen.addEventListener('click', function () { confModal.classList.add('open'); });
      if (confClose) confClose.addEventListener('click', function () { confModal.classList.remove('open'); });
      confModal.addEventListener('click', function (e) {
        if (e.target === confModal) confModal.classList.remove('open');
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && confModal.classList.contains('open')) confModal.classList.remove('open');
      });
    }
  });

  (function () {
    const overlays = {
      student: document.getElementById('cinvStudent'),
      teacher: document.getElementById('cinvTeacher'),
    };
    const triggers = document.querySelectorAll('[data-coil-invite]');
    const menu = document.getElementById('coilInviteMenu');

    function open(kind) {
      const ov = overlays[kind];
      if (!ov) return;
      ov.classList.add('is-open');
      ov.setAttribute('aria-hidden', 'false');
      const input = ov.querySelector('input[type="email"]');
      if (input) setTimeout(() => input.focus(), 50);
      if (menu) menu.open = false;
    }
    function close(ov) {
      ov.classList.remove('is-open');
      ov.setAttribute('aria-hidden', 'true');
    }

    triggers.forEach(t => t.addEventListener('click', () => open(t.dataset.coilInvite)));

    Object.values(overlays).forEach(ov => {
      if (!ov) return;
      ov.addEventListener('click', (e) => { if (e.target === ov) close(ov); });
      ov.querySelectorAll('[data-cinv-close]').forEach(b => b.addEventListener('click', () => close(ov)));
    });

    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      Object.values(overlays).forEach(ov => ov && ov.classList.contains('is-open') && close(ov));
    });
  })();