    $(document).ready(function () {
      function renderEmpty(message) {
        $('#progressTableBody').html(`
          <tr><td colspan="4">
            <div class="cl-empty">
              <i class="fas fa-chart-line"></i>
              <h6>No matches</h6>
              <small>${message}</small>
            </div>
          </td></tr>`);
      }

      $.getJSON('/get_teacher_progress_report/', function (data) {
        const subjects = data.progress_by_subject || {};
        const teachers = new Set();
        Object.values(subjects).forEach(d => teachers.add(d.teacher_name));
        teachers.forEach(t => $('#teacherFilter').append(`<option value="${t}">${t}</option>`));

        function update() {
          const teacher = $('#teacherFilter').val();
          const q = ($('#tpr-search').val() || '').toLowerCase().trim();
          const body = $('#progressTableBody').empty();
          let i = 1, count = 0;
          Object.entries(subjects).forEach(([subjectKey, d]) => {
            const subjectName = subjectKey.split(' (ID:')[0];
            if (teacher && d.teacher_name !== teacher) return;
            if (q && !subjectName.toLowerCase().includes(q) && !d.teacher_name.toLowerCase().includes(q)) return;
            const pct = parseFloat(d.total_progress) || 0;
            body.append(`
              <tr>
                <td>${i}</td>
                <td><span class="cl-name">${subjectName}</span></td>
                <td><span class="cl-row-meta">${d.teacher_name}</span></td>
                <td>
                  <div class="cl-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}">
                    <div class="cl-progress-bar" style="width:${pct}%"></div>
                    <span class="cl-progress-label">${pct.toFixed(1)}%</span>
                  </div>
                </td>
              </tr>`);
            i++; count++;
          });
          $('#tpr-count').text(`${count} subject${count === 1 ? '' : 's'}`);
          if (count === 0) renderEmpty(q || teacher ? 'Adjust the filters or search to see results.' : 'No subjects yet.');
        }

        let t;
        $('#tpr-search').on('input', () => { clearTimeout(t); t = setTimeout(update, 200); });
        $('#teacherFilter').on('change', update);
        update();
      }).fail(() => renderEmpty('Could not load progress data.'));
    });
  