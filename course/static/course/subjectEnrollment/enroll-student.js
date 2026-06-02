  document.addEventListener('DOMContentLoaded', function () {
    const studentSelect = document.getElementById('student_profile');
    const courseSelect = document.getElementById('course_select');
    const yearLevelSelect = document.getElementById('year_level_select');
    const studentsByCourse = JSON.parse(document.getElementById('students_by_course_json').textContent);

    // Initialize Select2 via the reusable cl-select2 engine. The engine
    // applies the bootstrap-5 theme, brand-tracked colors, and rewrites
    // the chip-× / clear-all buttons into our own .cl-chip-x markup.
    // Each select is inited individually so its data-placeholder wins.
    if (window.clSelect2) {
      jQuery('.es-page .es-select2-multi').each(function () {
        window.clSelect2.init(this, {
          placeholder: jQuery(this).data('placeholder') || 'Select…',
          allowClear: false,
          closeOnSelect: false,
        });
      });
      jQuery('.es-page .es-select2-single').each(function () {
        window.clSelect2.init(this, {
          placeholder: jQuery(this).data('placeholder') || 'Select…',
          allowClear: true,
        });
      });
    }

    // Count refreshers for the two multi-selects.
    function refreshCount(selectId) {
      const sel = document.querySelector(selectId);
      const pill = document.querySelector('[data-count-for="' + selectId + '"]');
      if (!sel || !pill) return;
      const total = sel.querySelectorAll('option').length;
      const picked = Array.from(sel.selectedOptions).length;
      pill.textContent = picked + (total ? ' / ' + total : '') + ' selected';
    }
    ['#student_profile', '#subject_ids'].forEach(id => {
      refreshCount(id);
      jQuery(id).on('change.esCount', () => refreshCount(id));
    });

    // Select all / Clear all bulk controls.
    document.querySelectorAll('[data-select-all]').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetSel = btn.getAttribute('data-select-all');
        const $sel = jQuery(targetSel);
        const all = $sel.find('option').map(function () { return this.value; }).get().filter(v => v !== '');
        $sel.val(all).trigger('change');
      });
    });
    document.querySelectorAll('[data-clear-all]').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetSel = btn.getAttribute('data-clear-all');
        jQuery(targetSel).val(null).trigger('change');
      });
    });

    // Single-select status pill + clear button. Mirrors the multi-select toolbar
    // shape so Program / Year level / Semester align with Courses visually.
    function refreshStatusPill(selectId, emptyLabel) {
      const sel = document.querySelector(selectId);
      const pill = document.querySelector('[data-status-for="' + selectId + '"]');
      if (!sel || !pill) return;
      const opt = sel.options[sel.selectedIndex];
      if (!sel.value || !opt) {
        pill.textContent = emptyLabel;
        pill.classList.remove('is-active');
      } else {
        pill.textContent = opt.textContent.trim();
        pill.classList.add('is-active');
      }
    }
    document.querySelectorAll('[data-status-for]').forEach(pill => {
      const sel = pill.getAttribute('data-status-for');
      const empty = pill.textContent.trim() || 'None selected';
      pill.dataset.emptyLabel = empty;
      refreshStatusPill(sel, empty);
      jQuery(sel).on('change.esStatus', () => refreshStatusPill(sel, empty));
    });
    document.querySelectorAll('[data-clear-single]').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetSel = btn.getAttribute('data-clear-single');
        jQuery(targetSel).val('').trigger('change');
      });
    });

    function filterStudents() {
      const selectedCourse = courseSelect.value;
      const selectedYearLevel = yearLevelSelect.value;
      jQuery(studentSelect).val([]).trigger('change');

      if (studentsByCourse[selectedCourse]) {
        const filtered = studentsByCourse[selectedCourse].filter(s =>
          selectedYearLevel === '' || s.grade_year_level === selectedYearLevel || s.grade_year_level === null
        );
        const ids = filtered.map(s => String(s.id));
        jQuery(studentSelect).val(ids).trigger('change');
      }
    }

    jQuery(courseSelect).on('change', filterStudents);
    jQuery(yearLevelSelect).on('change', filterStudents);

    // Modal
    const importModal = document.getElementById('importModal');
    const importBackdrop = document.getElementById('importModalBackdrop');
    const closeBtn = document.getElementById('closeImportModalBtn');
    // Reparent to <body> so position:fixed anchors to the viewport regardless
    // of ancestor transform/filter creating a containing block.
    if (importBackdrop) document.body.appendChild(importBackdrop);
    if (importModal) document.body.appendChild(importModal);
    function openModal() { importModal.classList.add('show'); importBackdrop.classList.add('show'); }
    function closeModal() { importModal.classList.remove('show'); importBackdrop.classList.remove('show'); }
    closeBtn?.addEventListener('click', closeModal);
    importBackdrop?.addEventListener('click', closeModal);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

    // Show selected file name in dropzone
    const fileInput = document.getElementById('importFile');
    const fileName = document.getElementById('importFileName');
    fileInput?.addEventListener('change', function() {
      fileName.textContent = this.files[0]?.name || '';
    });

    // Expose openModal for any external trigger (e.g. an "Import" button elsewhere)
    window.openImportStudentsModal = openModal;
  });