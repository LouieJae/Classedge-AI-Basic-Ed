    document.addEventListener('DOMContentLoaded', function () {
      if (typeof ClAsyncTable !== 'undefined') {
        ClAsyncTable.init('#cl-cert-wrapper', { prefix: 'cl' });
      }

      // Reparent to <body> so position:fixed anchors to the viewport.
      ['certificateModal','certificateModalBackdrop','editCertModal','editCertModalBackdrop'].forEach(id => {
        const el = document.getElementById(id);
        if (el) document.body.appendChild(el);
      });

      function show(id, bd) {
        document.getElementById(id).classList.add('show');
        document.getElementById(bd).classList.add('show');
      }
      function hide(id, bd) {
        document.getElementById(id).classList.remove('show');
        document.getElementById(bd).classList.remove('show');
      }

      const addBtn = document.getElementById('openAddCertBtn');
      if (addBtn) addBtn.addEventListener('click', () => {
        show('certificateModal', 'certificateModalBackdrop');
        initCertSelect2(document.getElementById('certificateModal'));
      });
      document.getElementById('closeCertModalBtn').addEventListener('click', () => hide('certificateModal', 'certificateModalBackdrop'));
      document.getElementById('certificateModalBackdrop').addEventListener('click', () => hide('certificateModal', 'certificateModalBackdrop'));

      document.getElementById('closeEditCertModalBtn').addEventListener('click', () => hide('editCertModal', 'editCertModalBackdrop'));
      document.getElementById('editCertModalBackdrop').addEventListener('click', () => hide('editCertModal', 'editCertModalBackdrop'));

      document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        ['certificateModal','editCertModal'].forEach(id => {
          const m = document.getElementById(id);
          if (m && m.classList.contains('show')) hide(id, id + 'Backdrop');
        });
      });
    });

    function openCertEditModal(certId) {
      fetch(`/certificate/update/${certId}/`)
        .then(r => r.text())
        .then(html => {
          document.getElementById('editCertModalBody').innerHTML = html;
          document.getElementById('editCertModal').classList.add('show');
          document.getElementById('editCertModalBackdrop').classList.add('show');
          initCertSelect2(document.getElementById('editCertModal'));
        });
    }

    // Initialize Select2 on the recipients picker inside the given modal scope.
    // Anchors the dropdown to <body> (not the modal) so it isn't clipped by
    // .rl-modal's overflow:hidden / .rl-form-body's scroll container. The
    // dropdown's own z-index (100000) already stacks it above the modal.
    function initCertSelect2(scope) {
      if (!scope || !window.jQuery || !jQuery.fn || !jQuery.fn.select2) return;
      const $scope = jQuery(scope);
      const $sel = $scope.find('select.cert-recipients-select');
      if (!$sel.length) return;
      if ($sel.hasClass('select2-hidden-accessible')) {
        try { $sel.select2('destroy'); } catch (e) {}
      }
      $sel.select2({
        dropdownParent: jQuery(document.body),
        width: '100%',
        placeholder: $sel.attr('data-placeholder') || 'Select recipients…',
        allowClear: false,
        closeOnSelect: false,
      });

      // Wire Select all / Clear buttons + live count for THIS modal scope.
      const $count = $scope.find('[data-cert-count]');
      const $allBtn = $scope.find('[data-cert-select-all]');
      const $clearBtn = $scope.find('[data-cert-clear]');

      function refreshCount() {
        const total = $sel.find('option').length;
        const picked = ($sel.val() || []).length;
        $count.text(picked + (total ? ' / ' + total : '') + ' selected');
      }
      $sel.off('change.certCount').on('change.certCount', refreshCount);
      refreshCount();

      $allBtn.off('click.certAll').on('click.certAll', function () {
        const all = $sel.find('option').map(function () { return this.value; }).get();
        $sel.val(all).trigger('change');
      });
      $clearBtn.off('click.certClr').on('click.certClr', function () {
        $sel.val(null).trigger('change');
      });
    }
  