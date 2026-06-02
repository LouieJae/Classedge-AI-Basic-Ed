  document.addEventListener('DOMContentLoaded', function () {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (el) { new bootstrap.Tooltip(el); });

    if (window.$ && $.fn.selectpicker) { $('.selectpicker').selectpicker(); }

    const semesterDropdown = document.getElementById("id_source_semester");
    if (semesterDropdown) {
      semesterDropdown.addEventListener("change", function () {
        const semesterId = this.value;
        if (!semesterId) return;
        fetch(`/get-terms/${semesterId}/`)
          .then((response) => response.json())
          .then((data) => {
            const termSelect = document.getElementById("id_term");
            if (termSelect) {
              termSelect.innerHTML = data.terms.map(term => `<option value="${term.id}">${term.term_name}</option>`).join("");
            }
            const subjectSelect = document.getElementById("id_copy_from_subject");
            if (subjectSelect) {
              subjectSelect.innerHTML = data.subjects.map(subject => {
                const subjectType = subject.subject_type ? ` - ${subject.subject_type}` : "";
                return `<option value="${subject.id}">${subject.subject_name}${subjectType}</option>`;
              }).join("");
            }
            if (window.$ && $.fn.selectpicker) {
              $(subjectSelect).selectpicker('refresh');
              $('#id_term').selectpicker('refresh');
            }
          })
          .catch((error) => console.error("Error fetching terms and subjects:", error));
      });
    }
  });