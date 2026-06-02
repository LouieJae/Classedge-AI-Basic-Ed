    document.addEventListener('DOMContentLoaded', function () {
      if (typeof ClAsyncTable !== 'undefined') {
        ClAsyncTable.init('#cl-dept-wrapper', { prefix: 'cl' });
      }

      ['addDepartmentModal','addDepartmentBackdrop','editDepartmentModal','editDepartmentBackdrop'].forEach(id => {
        const el = document.getElementById(id);
        if (el) document.body.appendChild(el);
      });

      function show(id, bd) { document.getElementById(id).classList.add('show'); document.getElementById(bd).classList.add('show'); }
      function hide(id, bd) { document.getElementById(id).classList.remove('show'); document.getElementById(bd).classList.remove('show'); }

      document.getElementById('openAddDepartmentBtn').addEventListener('click', () => {
        show('addDepartmentModal', 'addDepartmentBackdrop');
        const input = document.getElementById('dept-name-input');
        if (input) setTimeout(() => input.focus(), 280);
      });
      document.getElementById('closeAddDepartmentBtn').addEventListener('click', () => hide('addDepartmentModal','addDepartmentBackdrop'));
      document.getElementById('addDepartmentBackdrop').addEventListener('click', () => hide('addDepartmentModal','addDepartmentBackdrop'));

      document.getElementById('closeEditDepartmentBtn').addEventListener('click', () => hide('editDepartmentModal','editDepartmentBackdrop'));
      document.getElementById('editDepartmentBackdrop').addEventListener('click', () => hide('editDepartmentModal','editDepartmentBackdrop'));

      document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        ['addDepartmentModal','editDepartmentModal'].forEach(id => {
          const m = document.getElementById(id);
          if (m && m.classList.contains('show')) hide(id, id.replace('Modal','Backdrop'));
        });
      });
    });

    // Hook called by row "Edit" action (see column config in views).
    function openDepartmentEditModal(deptId) {
      fetch(`/departments/${deptId}/update/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(r => r.text())
        .then(html => {
          document.getElementById('editDepartmentBody').innerHTML = html;
          document.getElementById('editDepartmentModal').classList.add('show');
          document.getElementById('editDepartmentBackdrop').classList.add('show');
          const input = document.getElementById('dept-name-input');
          if (input) setTimeout(() => { input.focus(); input.select(); }, 280);
        });
    }
  