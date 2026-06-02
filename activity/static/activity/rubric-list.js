    ;(function () {
      var search = document.getElementById('rbSearch')
      var body = document.getElementById('rbBody')
      var summary = document.getElementById('rbSummary')
      var noMatch = document.getElementById('rbNoMatch')
      var rows = body ? Array.prototype.slice.call(body.querySelectorAll('.rb-row')) : []

      function update() {
        var qRaw = (search && search.value || '').trim()
        var q = qRaw.toLowerCase()
        var visible = 0
        rows.forEach(function (row) {
          var name = row.getAttribute('data-name') || ''
          var match = !q || name.indexOf(q) !== -1
          row.style.display = match ? '' : 'none'
          if (match) {
            visible++
            var counter = row.querySelector('.counter')
            if (counter) counter.textContent = visible
            if (window.ClHighlight) window.ClHighlight.wrap(row, qRaw)
          } else if (window.ClHighlight) {
            window.ClHighlight.clear(row)
          }
        })
        if (summary) {
          var total = rows.length
          summary.textContent = q
            ? visible + ' of ' + total + ' rubric' + (total === 1 ? '' : 's')
            : total + ' rubric' + (total === 1 ? '' : 's')
        }
        if (noMatch) noMatch.style.display = q && visible === 0 ? '' : 'none'
      }
      if (search) search.addEventListener('input', update)

      // Per-row action menus — teleported to <body> so card overflow can't clip them.
      // The helper is defined in base_operation.html *after* the content block,
      // so wait for the full document to parse before binding.
      function bindRowActions() {
        if (window.clBindMenuTeleport) {
          window.clBindMenuTeleport({
            wrapSelector: '.rb-actions',
            btnSelector: '.rb-actions-btn',
            menuSelector: '.rb-actions-menu'
          });
        }
        document.querySelectorAll('.rb-actions-menu form[data-confirm]').forEach(function (form) {
          if (form.dataset.confirmBound === '1') return;
          form.dataset.confirmBound = '1';
          form.addEventListener('submit', function (e) {
            if (form.dataset.confirmed === '1') return;
            e.preventDefault();
            var message = form.getAttribute('data-confirm') || 'Are you sure?';
            if (typeof Swal === 'undefined') {
              if (window.confirm(message)) {
                form.dataset.confirmed = '1';
                form.submit();
              }
              return;
            }
            Swal.fire({
              title: 'Are you sure?',
              text: message,
              icon: 'warning',
              showCancelButton: true,
              confirmButtonText: 'Yes, delete it',
              cancelButtonText: 'Cancel',
              confirmButtonColor: '#c0392b',
              cancelButtonColor: '#6c7080',
              reverseButtons: true,
              focusCancel: true,
            }).then(function (result) {
              if (result.isConfirmed) {
                form.dataset.confirmed = '1';
                form.submit();
              }
            });
          });
        })
      }
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindRowActions)
      } else {
        bindRowActions()
      }
    })()
  