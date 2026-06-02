    document.addEventListener('DOMContentLoaded', function () {
      document.querySelectorAll('input[type="number"]').forEach((input) => {
        input.addEventListener('input', function () {
          const max = parseFloat(this.getAttribute('max'))
          if (parseFloat(this.value) > max) {
            this.setCustomValidity('Score cannot exceed the maximum score')
          } else {
            this.setCustomValidity('')
          }
        })
      })
    })
  

    // Initialize DataTable for essay table with safeguard
    document.addEventListener('DOMContentLoaded', function() {
      const essayTable = document.querySelector('.essay-table');
      if (essayTable && !$.fn.DataTable.isDataTable(essayTable)) {
        $(essayTable).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
  