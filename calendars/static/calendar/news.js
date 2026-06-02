  (function () {
    var gridEl = document.getElementById('newsGrid');
    var searchEl = document.getElementById('newsSearch');
    var noMatch = document.getElementById('newsNoMatch');
    if (!gridEl) return;

    var rows = Array.prototype.slice.call(gridEl.querySelectorAll('.news-row'));
    var cards = Array.prototype.slice.call(gridEl.querySelectorAll('.news-card'));

    function apply() {
      var q = (searchEl && searchEl.value || '').trim().toLowerCase();
      var anyVisible = 0;

      // Filter rows by search query
      rows.forEach(function (row) {
        var text = row.getAttribute('data-text') || '';
        var show = !q || text.indexOf(q) !== -1;
        row.style.display = show ? '' : 'none';
        if (show) anyVisible++;
      });

      // Hide a whole card if none of its rows match (only when searching).
      cards.forEach(function (card) {
        var visibleRows = card.querySelectorAll('.news-row:not([style*="display: none"])').length;
        var hadRowsOriginally = card.querySelectorAll('.news-row').length > 0;
        if (q && hadRowsOriginally && visibleRows === 0) {
          card.classList.add('is-hidden');
        } else {
          card.classList.remove('is-hidden');
        }
      });

      if (noMatch) {
        var allCardsHidden = cards.every(function (c) { return c.classList.contains('is-hidden'); });
        noMatch.classList.toggle('is-on', !!q && allCardsHidden);
      }
    }

    if (searchEl) searchEl.addEventListener('input', apply);
  })();

  // ─── Campus News carousel ───────────────────────────────
  (function () {
    var stage = document.getElementById('cnStage');
    if (!stage) return;
    var slides = Array.prototype.slice.call(stage.querySelectorAll('.cn-slide'));
    if (slides.length <= 1) return;

    var dots = Array.prototype.slice.call(stage.querySelectorAll('.cn-dot'));
    var prev = document.getElementById('cnPrev');
    var next = document.getElementById('cnNext');
    var autoplayMs = parseInt(stage.getAttribute('data-autoplay'), 10) || 0;
    var idx = 0;
    var timer = null;

    function show(n) {
      idx = (n + slides.length) % slides.length;
      slides.forEach(function (s, i) {
        s.classList.toggle('is-active', i === idx);
      });
      dots.forEach(function (d, i) {
        var active = i === idx;
        d.classList.toggle('is-active', active);
        d.setAttribute('aria-selected', active ? 'true' : 'false');
      });
    }

    function step(delta) { show(idx + delta); restartAutoplay(); }

    function restartAutoplay() {
      if (!autoplayMs) return;
      if (timer) clearInterval(timer);
      timer = setInterval(function () { show(idx + 1); }, autoplayMs);
    }

    if (prev) prev.addEventListener('click', function () { step(-1); });
    if (next) next.addEventListener('click', function () { step(1); });
    dots.forEach(function (d) {
      d.addEventListener('click', function () {
        var n = parseInt(d.getAttribute('data-idx'), 10);
        if (!isNaN(n)) { show(n); restartAutoplay(); }
      });
    });

    // Pause autoplay on hover / focus so a user can read a slide.
    stage.addEventListener('mouseenter', function () { if (timer) { clearInterval(timer); timer = null; } });
    stage.addEventListener('mouseleave', restartAutoplay);
    stage.addEventListener('focusin',  function () { if (timer) { clearInterval(timer); timer = null; } });
    stage.addEventListener('focusout', restartAutoplay);

    // Keyboard arrows when the carousel area has focus.
    stage.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft')  { e.preventDefault(); step(-1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
    });

    restartAutoplay();
  })();
