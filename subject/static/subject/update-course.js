  (function () {
    function toggleCoilHaliFields() {
      const coilCheckboxes = document.querySelectorAll('.coil-input input[type="checkbox"], #id_is_coil');
      const haliCheckboxes = document.querySelectorAll('.hali-input input[type="checkbox"], #id_is_hali');
      const shouldShow = Array.from(coilCheckboxes).some(cb => cb.checked) ||
                         Array.from(haliCheckboxes).some(cb => cb.checked);
      document.querySelectorAll('.coil-hali-fields').forEach(field => {
        field.classList.toggle('d-none', !shouldShow);
      });
    }
    // Mutual exclusivity — a subject is one program type at a time (or
    // none). When the user picks COIL, HALI, or CTE we clear the others.
    function enforceSingleProgram(changedCb) {
      if (!changedCb || !changedCb.checked) return;
      const group = changedCb.closest('.program-flag-group');
      if (!group) return;
      group.querySelectorAll('input[type="checkbox"]').forEach((other) => {
        if (other !== changedCb && other.checked) {
          other.checked = false;
          other.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    }
    function attachListeners() {
      document.querySelectorAll('.coil-input input[type="checkbox"], .hali-input input[type="checkbox"], .cte-input input[type="checkbox"]').forEach((cb) => {
        if (cb._bound) return;
        cb._bound = true;
        cb.addEventListener('change', function () {
          enforceSingleProgram(cb);
          toggleCoilHaliFields();
        });
      });
    }
    document.addEventListener('DOMContentLoaded', () => {
      attachListeners();
      toggleCoilHaliFields();
      if (window.$ && $.fn.selectpicker) { $('.selectpicker').selectpicker(); }
    });
  })();