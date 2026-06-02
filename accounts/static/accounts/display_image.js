// Toast utility function
function showToast(message) {
  $('#toastMessage').text(message);
  const toast = new bootstrap.Toast(document.getElementById('successToast'));
  toast.show();
}

// Get CSRF token
function getCSRFToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Fetch and display images
function fetchImages() {
  $.get('/api/display_image/', function(data) {
    const tableBody = $('#imageTableBody').empty();
    if (!data.results || data.results.length === 0) {
      tableBody.html('<tr><td colspan="5" class="text-center py-4"><i class="fas fa-image fa-3x text-muted mb-3"></i><p>No images found. Click "Add New Image" to get started.</p></td></tr>');
      return;
    }

    data.results.forEach((image, index) => {
      const imageUrl = image.image;
      const displayStatus = image.is_displayed ? 
        '<span class="badge bg-success"><i class="fas fa-check me-1"></i>Displayed</span>' : 
        '<span class="badge bg-secondary"><i class="fas fa-eye-slash me-1"></i>Hidden</span>';
      
      const row = `
        <tr>
          <td>${index + 1}</td>
          <td>${image.name}</td>
          <td>
            <div class="d-flex justify-content-center">
              <img src="${imageUrl}" class="img-thumbnail" style="height: 80px; object-fit: contain;" 
                   onerror="this.src='/static/assets/img/generic/default.png';" alt="${image.name}">
            </div>
          </td>
          <td>${displayStatus}</td>
          <td>
            <div class="btn-group" role="group">
              <button class="btn btn-sm btn-outline-primary edit-btn" 
                      data-id="${image.id}" data-name="${image.name}" 
                      data-display="${image.is_displayed}" data-image="${imageUrl}">
                <i class="fas fa-edit me-1"></i>Edit
              </button>
              <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${image.id}" data-name="${image.name}">
                <i class="fas fa-trash-alt me-1"></i>Delete
              </button>
            </div>
          </td>
        </tr>`;
      tableBody.append(row);
    });
  });
}

$(document).ready(function () {
  fetchImages();

  // CREATE
  $('#addImageForm').on('submit', function (e) {
    e.preventDefault();
    const submitBtn = $('#addImageBtn');
    const spinner = submitBtn.find('.spinner-border');
    
    // Show loading state
    submitBtn.prop('disabled', true);
    spinner.removeClass('d-none');
    
    const formData = new FormData(this);
    $.ajax({
      url: '/api/display_image/',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      headers: { 'X-CSRFToken': getCSRFToken() },
      success: function () {
        $('#addImageModal').modal('hide');
        $('#addImageForm')[0].reset();
        fetchImages();
        showToast('Image added successfully!');
      },
      error: function(xhr) {
        let errorMsg = 'Failed to add image.';
        if (xhr.responseJSON && xhr.responseJSON.detail) {
          errorMsg += ' ' + xhr.responseJSON.detail;
        }
        alert(errorMsg);
      },
      complete: function() {
        // Reset loading state
        submitBtn.prop('disabled', false);
        spinner.addClass('d-none');
      }
    });
  });

  // SHOW EDIT MODAL
  $(document).on('click', '.edit-btn', function () {
    const id = $(this).data('id');
    const name = $(this).data('name');
    const isDisplayed = $(this).data('display') === true;
    const imageUrl = $(this).data('image');
    
    $('#edit_id').val(id);
    $('#edit_name').val(name);
    $('#edit_display').prop('checked', isDisplayed);
    $('#edit_preview').attr('src', imageUrl);
    $('#edit_preview_container').toggle(!!imageUrl);
    
    $('#editImageModal').modal('show');
  });

  // UPDATE
  $('#editImageForm').on('submit', function (e) {
    e.preventDefault();
    const id = $('#edit_id').val();
    const submitBtn = $('#updateImageBtn');
    const spinner = submitBtn.find('.spinner-border');
    
    // Show loading state
    submitBtn.prop('disabled', true);
    spinner.removeClass('d-none');
    
    const formData = new FormData(this);
    
    // Explicitly handle checkbox state
    formData.set('is_displayed', $('#edit_display').is(':checked'));
    
    if (!$('#edit_image')[0].files.length) {
      formData.delete('image');
    }
    
    $.ajax({
      url: `/api/display_image/${id}/`,
      type: 'PATCH',
      data: formData,
      processData: false,
      contentType: false,
      headers: { 'X-CSRFToken': getCSRFToken() },
      success: function () {
        $('#editImageModal').modal('hide');
        fetchImages();
        showToast('Image updated successfully!');
      },
      error: function(xhr) {
        let errorMsg = 'Failed to update image.';
        if (xhr.responseJSON && xhr.responseJSON.detail) {
          errorMsg += ' ' + xhr.responseJSON.detail;
        }
        alert(errorMsg);
      },
      complete: function() {
        // Reset loading state
        submitBtn.prop('disabled', false);
        spinner.addClass('d-none');
      }
    });
  });

  // SHOW DELETE CONFIRMATION
  $(document).on('click', '.delete-btn', function () {
    const id = $(this).data('id');
    const name = $(this).data('name');
    
    $('#delete_image_id').val(id);
    $('#deleteConfirmModal .modal-body p').text(`Are you sure you want to delete "${name}"? This action cannot be undone.`);
    $('#deleteConfirmModal').modal('show');
  });

  // CONFIRM DELETE
  $('#confirmDeleteBtn').on('click', function() {
    const id = $('#delete_image_id').val();
    const submitBtn = $(this);
    const spinner = submitBtn.find('.spinner-border');
    
    // Show loading state
    submitBtn.prop('disabled', true);
    spinner.removeClass('d-none');
    
    $.ajax({
      url: `/api/display_image/${id}/`,
      type: 'DELETE',
      headers: { 'X-CSRFToken': getCSRFToken() },
      success: function() {
        $('#deleteConfirmModal').modal('hide');
        fetchImages();
        showToast('Image deleted successfully!');
      },
      error: function() {
        alert('Failed to delete image. Please try again.');
      },
      complete: function() {
        // Reset loading state
        submitBtn.prop('disabled', false);
        spinner.addClass('d-none');
      }
    });
  });
});