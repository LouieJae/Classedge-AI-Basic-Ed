(function () {
  'use strict';
  if (window.ClSkeleton && window.ClSkeleton.__loaded) return;

  function cardList(count, label) {
    var n = Math.max(1, count | 0 || 4);
    var widths = [62, 88, 74];
    var html = '<div class="cl-skel-list" aria-busy="true" aria-label="' + (label || 'Loading') + '">';
    for (var i = 0; i < n; i++) {
      html += '<div class="cl-skel-card">' +
        '<div class="cl-skel cl-skel-circle"></div>' +
        '<div class="cl-skel-card-body">' +
          '<div class="cl-skel cl-skel-line lg" style="width:' + widths[0] + '%"></div>' +
          '<div class="cl-skel cl-skel-line" style="width:' + widths[1] + '%"></div>' +
          '<div class="cl-skel cl-skel-line" style="width:' + widths[2] + '%"></div>' +
        '</div>' +
      '</div>';
    }
    html += '</div>';
    return html;
  }

  function tileGrid(count, label) {
    var n = Math.max(1, count | 0 || 6);
    var html = '<div class="cl-skel-grid" aria-busy="true" aria-label="' + (label || 'Loading') + '">';
    for (var i = 0; i < n; i++) {
      html += '<div class="cl-skel-tile">' +
        '<div class="cl-skel cl-skel-block"></div>' +
        '<div class="cl-skel cl-skel-line lg" style="width:78%"></div>' +
        '<div class="cl-skel cl-skel-line" style="width:60%"></div>' +
      '</div>';
    }
    html += '</div>';
    return html;
  }

  function blockSkel(label) {
    return '<div class="cl-skel cl-skel-block" style="height:240px;border-radius:14px" aria-busy="true" aria-label="' + (label || 'Loading') + '"></div>';
  }

  function renderFor(shape, count, label) {
    if (shape === 'grid' || shape === 'tile') return tileGrid(count, label);
    if (shape === 'block') return blockSkel(label);
    return cardList(count, label);
  }

  function injectInto(target) {
    if (!target || target.dataset.clSkelActive === '1') return;
    var shape  = target.dataset.clSkel || 'list';
    var count  = parseInt(target.dataset.clSkelCount || '4', 10);
    var label  = target.dataset.clSkelLabel || 'Loading';
    target.dataset.clSkelActive = '1';
    target.innerHTML = renderFor(shape, count, label);
  }

  function clearFlag(target) {
    if (target && target.dataset) delete target.dataset.clSkelActive;
  }

  function bindHtmx() {
    if (!document.body) return;
    document.body.addEventListener('htmx:beforeRequest', function (e) {
      var detail = e.detail || {};
      var trigger = detail.elt || e.target;
      if (!trigger) return;
      var targetAttr = trigger.getAttribute && trigger.getAttribute('hx-target');
      var target = null;
      if (targetAttr) {
        try { target = document.querySelector(targetAttr); } catch (_) {}
      }
      if (!target) target = trigger.closest('[data-cl-skel]') || trigger;
      if (target && target.hasAttribute && target.hasAttribute('data-cl-skel')) injectInto(target);
    });
    document.body.addEventListener('htmx:afterSwap', function (e) {
      var detail = e.detail || {};
      clearFlag(detail.target || e.target);
    });
    document.body.addEventListener('htmx:responseError', function (e) {
      var detail = e.detail || {};
      clearFlag(detail.target || e.target);
    });
  }

  window.ClSkeleton = {
    __loaded: true,
    cardList: cardList,
    tileGrid: tileGrid,
    block: blockSkel,
    renderFor: renderFor,
    injectInto: injectInto,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindHtmx);
  } else {
    bindHtmx();
  }
})();
