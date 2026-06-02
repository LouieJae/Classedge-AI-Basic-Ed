    document.addEventListener('DOMContentLoaded', function () {
      ClAsyncTable.init('#cl-teacher-wrapper', { prefix: 'cl' });

      // Hoist the import modal to <body> before opening so the modal-backdrop
      // (appended to body by Bootstrap, z-index 1050) never paints over it.
      // Without this, ancestors like .cl-page with their own stacking context
      // can trap the modal underneath the backdrop.
      var importModal = document.getElementById('importTeachersModal');
      if (importModal) {
        importModal.addEventListener('show.bs.modal', function () {
          if (importModal.parentNode !== document.body) {
            document.body.appendChild(importModal);
          }
        });
      }
    });
  