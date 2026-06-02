    // Reparent role-list modals + backdrops to <body> so position:fixed
    // anchors to the viewport (ancestor transform/filter would otherwise create a containing block).
    ['editRoleModal','editRoleModalBackdrop','viewRoleModal','viewRoleModalBackdrop','customRoleModal','customRoleModalBackdrop'].forEach(id => {
      const el = document.getElementById(id);
      if (el) document.body.appendChild(el);
    });

    function show(id, backdropId) {
      document.getElementById(id).classList.add('show');
      document.getElementById(backdropId).classList.add('show');
    }
    function hide(id, backdropId) {
      document.getElementById(id).classList.remove('show');
      document.getElementById(backdropId).classList.remove('show');
    }

    document.getElementById('openRoleModal').addEventListener('click', () => show('customRoleModal', 'customRoleModalBackdrop'));
    document.getElementById('customRoleModalBackdrop').addEventListener('click', () => hide('customRoleModal', 'customRoleModalBackdrop'));
    const closeAddBtn = document.getElementById('closeRoleModal');
    if (closeAddBtn) closeAddBtn.addEventListener('click', () => hide('customRoleModal', 'customRoleModalBackdrop'));

    function attachPickerHandlers(scope) {
      const checkAll = scope.querySelector('#checkAll');
      if (checkAll) {
        checkAll.addEventListener('change', function () {
          scope.querySelectorAll('.permission-checkbox').forEach(cb => cb.checked = this.checked);
          scope.querySelectorAll('.select-all-category, .select-all-model').forEach(cb => cb.checked = this.checked);
        });
      }
      scope.querySelectorAll('.select-all-category').forEach(master => {
        master.addEventListener('change', function (ev) {
          ev.stopPropagation();
          const cat = this.dataset.catIndex;
          scope.querySelectorAll('.cat-' + cat).forEach(cb => cb.checked = this.checked);
          scope.querySelectorAll('.select-all-model[data-cat-index="' + cat + '"]').forEach(cb => cb.checked = this.checked);
        });
      });
      scope.querySelectorAll('.select-all-model').forEach(master => {
        master.addEventListener('change', function (ev) {
          ev.stopPropagation();
          const key = this.dataset.modelKey;
          scope.querySelectorAll('[data-model-key="' + key + '"].permission-checkbox').forEach(cb => cb.checked = this.checked);
        });
      });
      scope.querySelectorAll('.cat-select-label, .model-select-label').forEach(label => {
        label.addEventListener('click', ev => ev.stopPropagation());
      });
    }

    function openEditRoleModal(roleId) {
      fetch(`/role/update/${roleId}/`)
        .then(r => r.text())
        .then(html => {
          document.getElementById('editRoleModalBody').innerHTML = html;
          show('editRoleModal', 'editRoleModalBackdrop');
          attachPickerHandlers(document.getElementById('editRoleModalBody'));
        });
    }
    document.getElementById('closeEditRoleModalBtn').addEventListener('click', () => hide('editRoleModal', 'editRoleModalBackdrop'));
    document.getElementById('editRoleModalBackdrop').addEventListener('click', () => hide('editRoleModal', 'editRoleModalBackdrop'));

    function openViewRoleModal(roleId) {
      fetch(`/role/view/${roleId}/`)
        .then(r => r.text())
        .then(html => {
          document.getElementById('viewRoleModalBody').innerHTML = html;
          show('viewRoleModal', 'viewRoleModalBackdrop');
        });
    }
    document.getElementById('closeViewRoleModalBtn').addEventListener('click', () => hide('viewRoleModal', 'viewRoleModalBackdrop'));
    document.getElementById('viewRoleModalBackdrop').addEventListener('click', () => hide('viewRoleModal', 'viewRoleModalBackdrop'));

    document.addEventListener('keydown', e => {
      if (e.key !== 'Escape') return;
      ['editRoleModal','viewRoleModal','customRoleModal'].forEach(id => {
        const m = document.getElementById(id);
        if (m && m.classList.contains('show')) hide(id, id + 'Backdrop');
      });
    });
  

    document.addEventListener('DOMContentLoaded', function () {
      ClAsyncTable.init('#cl-role-wrapper', { prefix: 'cl' });
    });
  