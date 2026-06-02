    document.addEventListener('DOMContentLoaded', function() {
      const importForm = document.getElementById('importLessonForm');
      const importSubmitBtn = document.getElementById('importSubmitBtn');
      const importAlert = document.getElementById('importAlert');
      const importAlertText = document.getElementById('importAlertText');
      const importProgress = document.getElementById('importProgress');
      const importProgressBar = document.getElementById('importProgressBar');
      const importResults = document.getElementById('importResults');
      const fileInput = document.getElementById('import_file');

      // File validation
      fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
          if (!file.name.endsWith('.csv')) {
            showAlert('Please select a valid CSV file', 'danger');
            e.target.value = '';
          } else if (file.size > 5 * 1024 * 1024) { // 5MB limit
            showAlert('File size must be less than 5MB', 'danger');
            e.target.value = '';
          } else {
            hideAlert();
          }
        }
      });

      // Form submission
      importSubmitBtn.addEventListener('click', function() {
        if (!fileInput.files[0]) {
          showAlert('Please select a CSV file to import', 'warning');
          return;
        }

        // Show progress
        importProgress.classList.remove('d-none');
        importSubmitBtn.disabled = true;
        importSubmitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Importing...';

        // Submit form via AJAX
        const formData = new FormData(importForm);
        
        fetch(importForm.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            showResults(data);
            setTimeout(() => {
              location.reload();
            }, 2000);
          } else {
            showAlert(data.message || 'Import failed. Please try again.', 'danger');
          }
        })
        .catch(error => {
          showAlert('An error occurred during import. Please try again.', 'danger');
        })
        .finally(() => {
          importProgress.classList.add('d-none');
          importSubmitBtn.disabled = false;
          importSubmitBtn.innerHTML = '<i class="fas fa-upload me-2"></i>Import Materials';
        });
      });

      function showAlert(message, type) {
        importAlertText.textContent = message;
        importAlert.className = `alert alert-${type}`;
        importAlert.classList.remove('d-none');
      }

      function hideAlert() {
        importAlert.classList.add('d-none');
      }

      function showResults(data) {
        document.getElementById('createdCount').textContent = data.created || 0;
        document.getElementById('updatedCount').textContent = data.updated || 0;
        document.getElementById('skippedCount').textContent = data.skipped || 0;
        importResults.classList.remove('d-none');
      }

      // Reset modal when closed
      const importModal = document.getElementById('importLessonModal');
      importModal.addEventListener('hidden.bs.modal', function() {
        importForm.reset();
        importResults.classList.add('d-none');
        hideAlert();
        importProgress.classList.add('d-none');
      });
    });
  