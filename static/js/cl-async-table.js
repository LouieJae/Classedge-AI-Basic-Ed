/**
 * [Classedge LMS] Reusable async table controller.
 *
 * Wires up a wrapper element so search input (debounced), per-page selector,
 * and pagination links all fetch ?partial=1 from the same URL and swap the
 * wrapper's innerHTML — no full page reload.
 *
 * Usage:
 *   <div id="rl-table-wrapper" data-cl-async-table data-base-url="/role_list/">
 *     {% include "role/_role_list_table.html" %}
 *   </div>
 *   <script src="{% static 'js/cl-async-table.js' %}"></script>
 *   <script>ClAsyncTable.init('#rl-table-wrapper');</script>
 *
 * The fragment template should include (with stable IDs):
 *   - input#<prefix>-search-input  (optional — search box)
 *   - element#<prefix>-search-clear (optional — clear button)
 *   - select#<prefix>-per-page     (optional — per-page selector)
 *   - <a class="cl-page-btn" href="?page=N">  (pagination links from _pagination.html)
 *
 * Defaults to prefix "rl"; pass {prefix: "..."} to override.
 */
(function (global) {
  'use strict';

  function debounce(fn, wait) {
    let t;
    return function () {
      const ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(() => fn.apply(ctx, args), wait);
    };
  }

  function buildQS(params) {
    const usp = new URLSearchParams();
    Object.keys(params).forEach(k => {
      const v = params[k];
      if (v !== undefined && v !== null && v !== '') usp.set(k, v);
    });
    usp.set('partial', '1');
    return usp.toString();
  }

  function ClAsyncTable(wrapperSel, opts) {
    const wrapper = typeof wrapperSel === 'string'
      ? document.querySelector(wrapperSel)
      : wrapperSel;
    if (!wrapper) return;

    const options = Object.assign({
      prefix: 'rl',
      baseUrl: wrapper.dataset.baseUrl || window.location.pathname,
      onAfterSwap: null,
    }, opts || {});

    const state = { search: '', per_page: '', page: 1 };

    function fetchAndSwap(extraParams) {
      const params = Object.assign({}, state, extraParams || {});
      const url = options.baseUrl + '?' + buildQS(params);
      // Update browser URL (without partial=1 so refreshes still work).
      const visibleParams = Object.assign({}, params);
      delete visibleParams.partial;
      const visibleQs = buildQSVisible(visibleParams);
      history.replaceState(null, '', options.baseUrl + (visibleQs ? '?' + visibleQs : ''));
      wrapper.classList.add('cl-loading');
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
        .then(r => r.text())
        .then(html => {
          wrapper.innerHTML = html;
          wrapper.classList.remove('cl-loading');
          rebind();
          if (typeof options.onAfterSwap === 'function') options.onAfterSwap(wrapper);
        })
        .catch(() => { wrapper.classList.remove('cl-loading'); });
    }

    function buildQSVisible(params) {
      const usp = new URLSearchParams();
      Object.keys(params).forEach(k => {
        const v = params[k];
        if (v !== undefined && v !== null && v !== '' && k !== 'partial') usp.set(k, v);
      });
      return usp.toString();
    }

    function rebind() {
      const p = options.prefix;

      // Capture initial state from rendered controls so a "soft" first
      // bind (e.g. server already populated values) stays in sync.
      const searchEl = wrapper.querySelector('#' + p + '-search-input');
      const perPageEl = wrapper.querySelector('#' + p + '-per-page');
      const clearEl = wrapper.querySelector('#' + p + '-search-clear');

      if (searchEl) {
        state.search = searchEl.value;
        const handler = debounce(function () {
          state.search = searchEl.value;
          state.page = 1;
          fetchAndSwap();
        }, 300);
        searchEl.addEventListener('input', handler);
        // Re-focus & restore caret if same input was active.
        if (document.activeElement && document.activeElement.id === searchEl.id) {
          // already focused — nothing to do.
        } else if (wrapper.dataset.focusSearch === '1') {
          searchEl.focus();
          const len = searchEl.value.length;
          searchEl.setSelectionRange(len, len);
        }
        searchEl.addEventListener('focus', () => { wrapper.dataset.focusSearch = '1'; });
        searchEl.addEventListener('blur', () => { wrapper.dataset.focusSearch = '0'; });
      }

      if (perPageEl) {
        state.per_page = perPageEl.value;
        perPageEl.addEventListener('change', function () {
          state.per_page = perPageEl.value;
          state.page = 1;
          fetchAndSwap();
        });
      }

      if (clearEl) {
        clearEl.addEventListener('click', function (ev) {
          ev.preventDefault();
          state.search = '';
          state.page = 1;
          fetchAndSwap();
        });
      }

      // Arbitrary filter inputs/selects: any element with [data-cl-filter]
      // and a "name" attribute will be sent on every fetch.
      wrapper.querySelectorAll('[data-cl-filter][name]').forEach(el => {
        const key = el.getAttribute('name');
        state[key] = el.value;
        const evName = (el.tagName === 'SELECT') ? 'change' : 'input';
        const handler = evName === 'input' ? debounce(() => {
          state[key] = el.value;
          state.page = 1;
          fetchAndSwap();
        }, 300) : () => {
          state[key] = el.value;
          state.page = 1;
          fetchAndSwap();
        };
        el.addEventListener(evName, handler);
      });

      // Forms with [data-cl-confirm] — replace the native confirm() dialog
      // with a SweetAlert2 modal (loaded globally in base_operation.html).
      wrapper.querySelectorAll('form[data-cl-confirm]').forEach(form => {
        if (form.dataset.clConfirmBound === '1') return;
        form.dataset.clConfirmBound = '1';
        form.addEventListener('submit', function (ev) {
          if (form.dataset.clConfirmed === '1') return;
          ev.preventDefault();
          const message = form.getAttribute('data-cl-confirm') || 'Are you sure?';
          const isDanger = form.getAttribute('data-cl-confirm-danger') === '1';
          if (typeof Swal === 'undefined') {
            if (window.confirm(message)) {
              form.dataset.clConfirmed = '1';
              form.submit();
            }
            return;
          }
          // Read tenant brand from CSS variable at runtime so the Swal
          // confirm button tracks --brand-primary instead of a hardcoded
          // forest hex. The danger variant (delete actions) stays red
          // semantically — destructive actions are categorical, not brand.
          const brandConfirm = (getComputedStyle(document.documentElement)
            .getPropertyValue('--brand-primary') || '').trim() || '#1b4332';
          Swal.fire({
            title: 'Are you sure?',
            text: message,
            icon: isDanger ? 'warning' : 'question',
            showCancelButton: true,
            confirmButtonText: isDanger ? 'Yes, delete it' : 'Confirm',
            cancelButtonText: 'Cancel',
            confirmButtonColor: isDanger ? '#c0392b' : brandConfirm,
            cancelButtonColor: '#6c7080',
            reverseButtons: true,
          }).then(result => {
            if (result.isConfirmed) {
              form.dataset.clConfirmed = '1';
              form.submit();
            }
          });
        });
      });

      // Pagination links rendered by _pagination.html — intercept clicks.
      wrapper.querySelectorAll('a.cl-page-btn[href]').forEach(a => {
        a.addEventListener('click', function (ev) {
          ev.preventDefault();
          const u = new URL(a.getAttribute('href'), window.location.origin);
          const page = u.searchParams.get('page') || 1;
          state.page = page;
          fetchAndSwap();
        });
      });
    }

    rebind();
    return { reload: () => fetchAndSwap(), wrapper: wrapper };
  }

  global.ClAsyncTable = {
    init: ClAsyncTable,
  };
})(window);
