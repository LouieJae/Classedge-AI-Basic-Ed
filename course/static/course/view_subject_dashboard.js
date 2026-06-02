    function confirmDelete(moduleId) {
        if (!moduleId) {
            return;
        }
        
        Swal.fire({
          title: 'Are you sure?',
          text: 'This lesson will be deleted and cannot be recovered!',
          icon: 'warning',
          showCancelButton: true,
          confirmButtonColor: '#3085d6',
          cancelButtonColor: '#d33',
          confirmButtonText: 'Yes, delete it!',
          cancelButtonText: 'Cancel'
      }).then((result) => {
          if (result.isConfirmed) {
              // ✅ Check if deletion is possible before redirecting
              fetch(`/checkModuleDependency/${moduleId}/`)
                  .then(response => response.json())
                  .then(data => {
                      if (data.can_delete) {
                          window.location.href = `/deleteModule/${moduleId}/`;
                      } else {
                          Swal.fire({
                              title: 'Deletion Not Allowed!',
                              text: 'This module cannot be deleted because it is referenced by other records. Please remove the linked activities first.',
                              icon: 'error'
                          });
                      }
                  })
                  .catch(error => {
                      Swal.fire({
                          title: 'Error!',
                          text: 'Something went wrong while checking module dependencies.',
                          icon: 'error'
                      });
                  });
          }
      });
  }  
  

    $(document).ready(function () {
        // Event delegation to handle dynamically loaded content inside the modal
      $(document).on('click', '.selectAll', function () {
        const statusId = $(this).data('status'); // Get the status ID from data attribute
 
            // Find and check all radio buttons with the class for this status
        $(`.status-${statusId}`).prop('checked', true);
      });
    });
  

    document.querySelectorAll('.drop-student-confirm').forEach(link => {
      link.addEventListener('click', event => {
        event.preventDefault();

        const url = link.getAttribute('href');
        const studentName = link.dataset.studentName;

        Swal.fire({
          title: 'Administrative Drop',
          text: `Are you sure you want to administratively drop ${studentName}?`,
          icon: 'warning',
          showCancelButton: true,
          reverseButtons: true,
          confirmButtonColor: '#d33',
          cancelButtonColor: '#3085d6',
          confirmButtonText: 'Yes, drop',
        }).then((result) => {
          if (result.isConfirmed) {
            window.location.href = url;
          }
        });
      });
    });
  