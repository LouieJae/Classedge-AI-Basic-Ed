(function () {
  'use strict';

  function getActionItems(menu) {
    if (!menu) return [];
    return Array.from(menu.querySelectorAll('.dropdown-item'))
      .filter(function (it) { return !it.classList.contains('dropdown-divider'); });
  }

  function makeInlineButton(item) {
    var tag = item.tagName.toLowerCase();
    var label = (item.textContent || '').trim();
    var icon = item.querySelector('i');
    var hostForm = item.closest('form');

    var btn;
    if (tag === 'button') {
      btn = item.cloneNode(true);
      btn.className = 'cl-inline-action-btn';
      btn.innerHTML = '';
      if (icon) btn.appendChild(icon.cloneNode(true));
    } else {
      btn = document.createElement('a');
      if (item.href) btn.href = item.href;
      if (item.target) btn.target = item.target;
      btn.className = 'cl-inline-action-btn';
      Array.from(item.attributes).forEach(function (attr) {
        if (attr.name.indexOf('data-') === 0 || attr.name === 'onclick') {
          btn.setAttribute(attr.name, attr.value);
        }
      });
      if (icon) btn.appendChild(icon.cloneNode(true));
      else btn.textContent = label;
    }

    if (label) {
      btn.title = label;
      btn.setAttribute('aria-label', label);
    }
    return { node: btn, form: hostForm };
  }

  function processDropdown(dropdownEl) {
    if (!dropdownEl || dropdownEl.dataset.clCollapsedActions === '1') return;
    dropdownEl.dataset.clCollapsedActions = '1';

    var menu = dropdownEl.querySelector('.dropdown-menu');
    if (!menu) return;
    var actions = getActionItems(menu);
    if (actions.length === 0 || actions.length > 2) return;

    var inline = document.createElement('div');
    inline.className = 'cl-inline-actions';

    actions.forEach(function (item) {
      var built = makeInlineButton(item);
      if (built.form) {
        var formClone = built.form.cloneNode(false);
        Array.from(built.form.children).forEach(function (child) {
          if (child !== item) formClone.appendChild(child.cloneNode(true));
        });
        formClone.appendChild(built.node);
        formClone.classList.add('d-inline');
        inline.appendChild(formClone);
      } else {
        inline.appendChild(built.node);
      }
    });

    dropdownEl.replaceWith(inline);
  }

  function processRow(row) {
    if (!row) return;
    row.querySelectorAll('.dropdown').forEach(processDropdown);
  }

  function processAllChildRows(root) {
    (root || document).querySelectorAll('tr.child, tr.parent + tr.child, .dtr-details').forEach(function (el) {
      var row = el.tagName === 'TR' ? el : el.closest('tr');
      processRow(row);
    });
  }

  function init() {
    if (window.jQuery && jQuery.fn.dataTable) {
      jQuery(document).on('responsive-display.dt', function (e, datatable, rowApi, showHide) {
        if (!showHide) return;
        setTimeout(function () {
          var rowNode = rowApi && rowApi.node && rowApi.node();
          var childRow = rowNode && rowNode.nextElementSibling;
          if (childRow && childRow.classList.contains('child')) {
            processRow(childRow);
          }
        }, 0);
      });

      jQuery(document).on('draw.dt', function () {
        processAllChildRows();
      });
    }

    processAllChildRows();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  window.addEventListener('cm:navigated', function () { processAllChildRows(); });
})();
