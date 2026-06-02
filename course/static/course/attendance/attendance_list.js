    // Script to open the Add Semester modal (loaded from external file)
    document.getElementById('openAddModalBtn').addEventListener('click', function () {
      document.getElementById('customModal').classList.add('show')
      document.getElementById('customModalBackdrop').classList.add('show')
    })

      // Script to close the Add Semester modal
    document.getElementById('closeModalBtn').addEventListener('click', function () {
      document.getElementById('customModal').classList.remove('show')
      document.getElementById('customModalBackdrop').classList.remove('show')
    })

    // Function to open the Edit Semester modal and load the content dynamically
    function openEditModal(recordId) {
      fetch(`/update_attendace/${recordId}/`)
        .then((response) => response.text())
        .then((html) => {
          document.getElementById('editModalBody').innerHTML = html;
          document.getElementById('editModal').classList.add('show');
          document.getElementById('editModalBackdrop').classList.add('show');

          // Add event listener to the close button after loading the content
          document.getElementById('closeEditModalBtn').addEventListener('click', function () {
            document.getElementById('editModal').classList.remove('show');
            document.getElementById('editModalBackdrop').classList.remove('show');
          });
        })
        .catch((error) => console.error('Error loading modal content:', error));
    }

  

    // Initialize DataTable for attendance list table with safeguard
    document.addEventListener('DOMContentLoaded', function() {
      const attendanceTable = document.querySelector('.attendance-list-table');
      if (attendanceTable && !$.fn.DataTable.isDataTable(attendanceTable)) {
        $(attendanceTable).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
  