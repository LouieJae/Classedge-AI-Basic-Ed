function selectActivityTypeAndRedirect(activityTypeName, subjectId, activityTypeId, isCM = false) {
  if (activityTypeId) {
    const baseUrl = isCM ? `/subject/${subjectId}/add-assessment-cm/` : `/subject/${subjectId}/add-assessment/`;
    const url = `${baseUrl}?activity_type_id=${activityTypeId}`;
    window.location.href = url;
  } else {
    alert('Activity Type is not defined for ' + activityTypeName);
  }
}

// Open Module Modal for Standard Mode
function openModuleModalStandard(subjectId, type) {
  // Hide the Standard Mode modal properly
  $('#addActivityLessonModalStandard').modal('hide');

  // Wait for the modal transition to complete before proceeding
  setTimeout(() => {
    fetch(`/createModule/${subjectId}/`)
      .then((response) => response.text())
      .then((html) => {
        // Update modal content
        document.getElementById('moduleModalBody').innerHTML = html;
        document.getElementById('moduleModal').classList.add('show');
        document.getElementById('moduleModalBackdrop').classList.add('show');

        // Hide all input fields initially
        document.getElementById('fileInputDiv').style.display = 'none';
        document.getElementById('urlInputDiv').style.display = 'none';
        document.getElementById('embedInputDiv').style.display = 'none';
        document.querySelector('.form-check').style.display = 'none';

        // Conditionally show the correct input based on `type`
        if (type === 'lesson') {
          document.getElementById('fileInputDiv').style.display = 'block';
        } else if (type === 'url') {
          document.getElementById('urlInputDiv').style.display = 'block';
        } else if (type === 'embed') {
          document.getElementById('embedInputDiv').style.display = 'block';
        }

        // Set up input fields visibility
        handleModuleInputDisplay(type);

        // Refresh Bootstrap Selectpicker
        $('.selectpicker').selectpicker('refresh');

      })
      .catch((error) => console.error('Error fetching module content:', error));
  }, 300);
}

// Open Module Modal for Classroom Mode
function openModuleModalClassroom(subjectId, type) {
  // Hide the Classroom Mode modal properly
  $('#addActivityLessonModalCM').modal('hide');

  // Wait for the modal transition to complete before proceeding
  setTimeout(() => {
    fetch(`/createModuleCM/${subjectId}/`)
      .then((response) => response.text())
      .then((html) => {
        // Update modal content
        document.getElementById('moduleModalBody').innerHTML = html;
        document.getElementById('moduleModal').classList.add('show');
        document.getElementById('moduleModalBackdrop').classList.add('show');

        // Hide all input fields initially
        document.getElementById('fileInputDiv').style.display = 'none';
        document.getElementById('urlInputDiv').style.display = 'none';
        document.getElementById('embedInputDiv').style.display = 'none';
        document.querySelector('.form-check').style.display = 'none';

        // Conditionally show the correct input based on `type`
        if (type === 'lesson') {
          document.getElementById('fileInputDiv').style.display = 'block';
        } else if (type === 'url') {
          document.getElementById('urlInputDiv').style.display = 'block';
        } else if (type === 'embed') {
          document.getElementById('embedInputDiv').style.display = 'block';
        }

        // Set up input fields visibility
        handleModuleInputDisplay(type);

        // Refresh Bootstrap Selectpicker
        $('.selectpicker').selectpicker('refresh');

      })
      .catch((error) => console.error('Error fetching module content:', error));
  }, 300);
}


// Utility function to manage input display
function handleModuleInputDisplay(type) {
  if (type === 'lesson') {
    document.getElementById('fileInputDiv').style.display = 'block'; // Show file input
    document.getElementById('urlInputDiv').style.display = 'none'; // Hide URL input
    document.querySelector('.form-check').style.display = 'none';
  } else if (type === 'url') {
    document.getElementById('fileInputDiv').style.display = 'none'; // Hide file input
    document.getElementById('urlInputDiv').style.display = 'block'; // Show URL input
    document.querySelector('.form-check').style.display = 'none';
  }
}


function initializeCustomFileUpload() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const filePreview = document.getElementById('filePreview');
  const dropzoneText = document.getElementById('dropzone-text');

  // Check if all required elements exist on this page
  if (!dropzone || !fileInput || !filePreview || !dropzoneText) {
    return;
  }

  // Trigger file explorer when clicking the dropzone
  dropzone.addEventListener('click', () => fileInput.click());

  // Drag over event
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  // Drag leave event
  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  // Drop event
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const files = e.dataTransfer.files;

    if (files.length > 0) {
      fileInput.files = files; // Assign files to the hidden input
      displayUploadedFile(files[0]); // Display the file details
    }
  });

  // File input change event
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      displayUploadedFile(fileInput.files[0]);
    }
  });

  // Function to display uploaded file details
  function displayUploadedFile(file) {
    // Clear existing preview
    filePreview.innerHTML = '';

    // Determine file icon based on file type
    let fileIcon = '<i class="far fa-file file-icon text-secondary"></i>'; // Default file icon
    const fileType = file.type;

    if (fileType.startsWith('image/')) {
      fileIcon = '<i class="far fa-file-image file-icon text-success"></i>';
    } else if (fileType === 'application/pdf') {
      fileIcon = '<i class="far fa-file-pdf file-icon text-danger"></i>';
    } else if (fileType.startsWith('video/')) {
      fileIcon = '<i class="far fa-file-video file-icon text-primary"></i>';
    } else if (fileType.startsWith('audio/')) {
      fileIcon = '<i class="far fa-file-audio file-icon text-warning"></i>';
    } else if (fileType.startsWith('text/')) {
      fileIcon = '<i class="far fa-file-alt file-icon text-info"></i>';
    }

    // Create the file preview element
    const previewItem = document.createElement('div');
        previewItem.className = 'file-preview-item';

    // Add the file icon and details
    previewItem.innerHTML = `
      ${fileIcon}
      <div class="file-details">
        <span class="file-name" title="${file.name}">${file.name}</span>
        <span class="file-type">${fileType || 'Unknown type'}</span>
      </div>
    `;

    // Append the file preview element to the preview container
    filePreview.appendChild(previewItem);

    // Hide the default dropzone text
    dropzoneText.style.display = 'none';
  }
}

// Initialize the custom file upload functionality
document.addEventListener('DOMContentLoaded', initializeCustomFileUpload);

   

// Bindings below run inside DOMContentLoaded so they re-attach after a
// CM-SPA body swap (the SPA dispatches a fresh DOMContentLoaded event).
// Without that wrapper, top-level getElementById(...).addEventListener calls
// run once on initial script load and leave subsequent-page buttons
// unhandled — closing the modal would silently do nothing after navigation.
function bindCloseToBackdrop(btnId, modalId, backdropId) {
  var btn = document.getElementById(btnId);
  if (!btn) return;
  btn.addEventListener('click', function () {
    var m = document.getElementById(modalId);
    var b = document.getElementById(backdropId);
    if (m) m.classList.remove('show');
    if (b) b.classList.remove('show');
  });
}
document.addEventListener('DOMContentLoaded', function () {
  bindCloseToBackdrop('closeParticipationModalBtn', 'participationModal', 'participationModalBackdrop');
  bindCloseToBackdrop('closeModuleModalBtn', 'moduleModal', 'moduleModalBackdrop');
});

// Old copy activity modal functions removed - now using dedicated import pages
// --- Copy Activity Modal (Classroom Mode) ---
function openCopyActivityModal(subjectId) {
  fetch(`/subject/${subjectId}/copy_activities/`)
    .then((response) => response.text())
    .then((html) => {
      const modalBody = document.getElementById('copyActivityModalBody')
      const modal = document.getElementById('copyActivityModal')
      const backdrop = document.getElementById('copyActivityModalBackdrop')

      if (!modalBody || !modal || !backdrop) {
        return
      }

      modalBody.innerHTML = html
      modal.classList.add('show')
      backdrop.classList.add('show')

      initializeActivityCheckboxScript(subjectId)
    })
    .catch((error) => console.error('Error loading copy activities modal:', error))
}

function initializeActivityCheckboxScript(subjectId) {
  $('#from_semester').off('change').on('change', function () {
    const semesterId = $(this).val()

    if (!semesterId) {
      $('#assessment_list').html('')
      return
    }

    $.ajax({
      url: `/get-activities/${subjectId}/${semesterId}/`,
      type: 'GET',
      success: function (response) {
        const groupedActivities = response.grouped_activities || []
        let assessment_list = ''

        if (groupedActivities.length > 0) {
          groupedActivities.forEach((group) => {
            assessment_list += `<h5>${group.term}</h5><ul>`
            group.activities.forEach((activity) => {
              assessment_list += `<li><label><input type="checkbox" name="activities" value="${activity.id}"> ${activity.activity_name} (${activity.activity_type})</label></li>`
            })
            assessment_list += '</ul>'
          })
        } else {
          assessment_list = '<p>No activities found for the selected semester.</p>'
        }

        $('#assessment_list').html(assessment_list)
      },
      error: function () {
        $('#assessment_list').html('<p>There was an error fetching activities.</p>')
      }
    })
  })
}

document.addEventListener('DOMContentLoaded', function () {
  bindCloseToBackdrop('closeCopyActivityModalBtn', 'copyActivityModal', 'copyActivityModalBackdrop');
});

// Open Copy Lesson Modal
function openCopyLessonModal(subjectId) {
  fetch(`/subject/${subjectId}/copy_lessons_CM/`)
    .then((response) => response.text())
    .then((html) => {
      document.getElementById('copyLessonModalBody').innerHTML = html
      document.getElementById('copyLessonModal').classList.add('show')
      document.getElementById('copyLessonModalBackdrop').classList.add('show')

      initializeLessonCheckboxes(subjectId)
    })
}

document.addEventListener('DOMContentLoaded', function () {
  bindCloseToBackdrop('closeCopyLessonModalBtn', 'copyLessonModal', 'copyLessonModalBackdrop');
});

document.addEventListener('DOMContentLoaded', function () {
  function checkAll(statusId) {
    document.querySelectorAll(`.status-${statusId}`).forEach((radio) => {
      radio.checked = true
    })
  }

  // Attach event listeners to each "Select All" radio button
  document.querySelectorAll('.selectAll').forEach((selectAllButton) => {
    selectAllButton.addEventListener('click', function () {
      const statusId = this.getAttribute('data-status')
      checkAll(statusId)
    })
  })
})

// Open Attendance Modal for Standard Mode (Bootstrap 5 Fix Applied)
function openAttendanceModalCM(subjectId) {
  // Close Bootstrap 5 modal properly
  let bootstrapModal = document.getElementById('addActivityLessonModalCM');
  if (bootstrapModal) {
    let modalInstance = bootstrap.Modal.getInstance(bootstrapModal);
    if (modalInstance) {
      modalInstance.hide(); // Close the modal safely
    }
  }

  // Fetch the attendance modal content
  fetch(`/attendance/record_attendanceCM/${subjectId}/`)
    .then(response => response.text())
    .then(html => {
      let attendanceModalBody = document.getElementById('attendanceModalBody');
      let attendanceModal = document.getElementById('attendanceModal');
      let attendanceModalBackdrop = document.getElementById('attendanceModalBackdrop');

      if (attendanceModalBody && attendanceModal) {
        attendanceModalBody.innerHTML = html;

        // Ensure modal appears on top of the backdrop
        attendanceModal.style.zIndex = '1050';
        attendanceModalBackdrop.style.zIndex = '1040';

        // Show modal and backdrop
        attendanceModal.classList.add('show');
        attendanceModalBackdrop.classList.add('show');
      } else {
      }
    })
    .catch(error => console.error('Error loading attendance modal:', error));
}

document.addEventListener('DOMContentLoaded', function () {
  bindCloseToBackdrop('closeAttendanceModalBtn', 'attendanceModal', 'attendanceModalBackdrop');
});


// Open Attendance Modal for Standard Mode (Bootstrap 5 Fix Applied)
function openAttendanceModal(subjectId) {
  // Close Bootstrap 5 modal properly
  let bootstrapModal = document.getElementById('addActivityLessonModalStandard');
  if (bootstrapModal) {
    let modalInstance = bootstrap.Modal.getInstance(bootstrapModal);
    if (modalInstance) {
      modalInstance.hide(); // Close the modal safely
    }
  }

  // Fetch the attendance modal content
  fetch(`/attendance/record/${subjectId}/`)
    .then(response => response.text())
    .then(html => {
      let attendanceModalBody = document.getElementById('attendanceModalBody');
      let attendanceModal = document.getElementById('attendanceModal');
      let attendanceModalBackdrop = document.getElementById('attendanceModalBackdrop');

      if (attendanceModalBody && attendanceModal) {
        attendanceModalBody.innerHTML = html;

        // Ensure modal appears on top of the backdrop
        attendanceModal.style.zIndex = '1050';
        attendanceModalBackdrop.style.zIndex = '1040';

        // Show modal and backdrop
        attendanceModal.classList.add('show');
        attendanceModalBackdrop.classList.add('show');
      } else {
      }
    })
    .catch(error => console.error('Error loading attendance modal:', error));
}

// (Duplicate closeAttendanceModalBtn binding removed — already wired up above
// inside the DOMContentLoaded block that survives SPA navigation.)




// Function to initialize lesson checkboxes
function initializeLessonCheckboxes(subjectId) {
  document.querySelectorAll('.lesson-checkbox').forEach((checkbox) => {
    checkbox.addEventListener('change', function () {
      let lessonId = this.value

      // Make AJAX request to check if the lesson exists in the current semester
      fetch(`/subject/${subjectId}/check_lesson_exists/?lesson_id=${lessonId}`, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
        .then((response) => response.json())
        .then((data) => {
          let warningElement = document.getElementById(`duplicate-warning-${lessonId}`)
          let listItemElement = document.getElementById(`lesson-item-${lessonId}`)

          if (data.exists) {
            // If the lesson already exists, show the warning message and disable the checkbox
            warningElement.style.display = 'inline'
            checkbox.disabled = true

            // Add a gray-out class to the lesson item
            listItemElement.style.backgroundColor = '#e0e0e0' // Light gray background
            listItemElement.style.cursor = 'not-allowed' // Show not-allowed cursor
            listItemElement.style.opacity = '0.6' // Make the text a bit faded
          } else {
            warningElement.style.display = 'none'
            checkbox.disabled = false

            listItemElement.style.backgroundColor = ''
            listItemElement.style.cursor = 'pointer' // Normal cursor
            listItemElement.style.opacity = '1' // Reset opacity
          }
        })
        .catch((error) => console.error('Error:', error))
    })
  })
}