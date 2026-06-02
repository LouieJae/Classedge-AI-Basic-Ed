  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.teacher-link').forEach(link => {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        const teacherId = this.getAttribute('data-teacher-id');
        const subjectId = this.getAttribute('data-subject-id');
        const startDate = document.getElementById('start_date').value;
        const endDate = document.getElementById('end_date').value;

        fetch(`/find_teacher_attendance/?teacher_id=${teacherId}&subject_id=${subjectId}&start_date=${startDate}&end_date=${endDate}`)
          .then(r => r.json())
          .then(data => {
            if (data.attendance_id) {
              window.location.href = `/screenshots/${data.attendance_id}/`;
            } else if (window.Swal) {
              Swal.fire({ icon: 'info', title: 'No attendance records', text: 'No attendance records found for this teacher and subject in the selected date range.' });
            } else {
              alert('No attendance records found.');
            }
          })
          .catch(() => {
            if (window.Swal) Swal.fire({ icon: 'error', title: 'Error', text: 'Error finding attendance record. Please try again.' });
            else alert('Error finding attendance record.');
          });
      });
    });
  });

  $(document).ready(function () {
    $('#teacher_filter').select2({ width: '100%' });
    $('#teacher_filter').on('change', applyFilters);
    $('#semester_filter').select2({ width: '100%' });
    $('#semester_filter').on('change', applyFilters);
  });