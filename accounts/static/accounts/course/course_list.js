    document.addEventListener('DOMContentLoaded', function () {
      if (typeof ClAsyncTable !== 'undefined') {
        ClAsyncTable.init('#cl-course-wrapper', { prefix: 'cl' });
      }

      ['courseModal','courseModalBackdrop','editCourseModal','editCourseModalBackdrop'].forEach(id => {
        const el = document.getElementById(id);
        if (el) document.body.appendChild(el);
      });

      function show(id, bd) { document.getElementById(id).classList.add('show'); document.getElementById(bd).classList.add('show'); }
      function hide(id, bd) { document.getElementById(id).classList.remove('show'); document.getElementById(bd).classList.remove('show'); }

      const addBtn = document.getElementById('openCourseModalBtn');
      if (addBtn) addBtn.addEventListener('click', () => show('courseModal','courseModalBackdrop'));
      document.getElementById('closeCourseModalBtn').addEventListener('click', () => hide('courseModal','courseModalBackdrop'));
      document.getElementById('courseModalBackdrop').addEventListener('click', () => hide('courseModal','courseModalBackdrop'));

      document.getElementById('closeEditCourseModalBtn').addEventListener('click', () => hide('editCourseModal','editCourseModalBackdrop'));
      document.getElementById('editCourseModalBackdrop').addEventListener('click', () => hide('editCourseModal','editCourseModalBackdrop'));

      document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        ['courseModal','editCourseModal'].forEach(id => {
          const m = document.getElementById(id);
          if (m && m.classList.contains('show')) hide(id, id + 'Backdrop');
        });
      });
    });

    function openCourseEditModal(courseId) {
      fetch(`/program/update/${courseId}/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(r => r.text())
        .then(html => {
          document.getElementById('editCourseModalBody').innerHTML = html;
          document.getElementById('editCourseModal').classList.add('show');
          document.getElementById('editCourseModalBackdrop').classList.add('show');
        });
    }

    // Row-action delete hook used by _list_table.html dropdowns.
    function confirmDeleteCourse(id) {
      if (!window.Swal) {
        if (confirm("Delete this program?")) location.href = `/delete_course/${id}/`;
        return;
      }
      Swal.fire({
        title: 'Delete this program?',
        text: "You won't be able to revert this.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#c08479',
        cancelButtonColor: '#a0a4b8',
        confirmButtonText: 'Yes, delete'
      }).then(result => {
        if (result.isConfirmed) location.href = `/delete_course/${id}/`;
      });
    }
  