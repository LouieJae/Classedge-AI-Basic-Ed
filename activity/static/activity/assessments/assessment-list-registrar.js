  document.addEventListener('DOMContentLoaded', function() {
    const actTable = document.querySelector('.activity-registrar-table');
    if (actTable && window.$ && $.fn.DataTable && !$.fn.DataTable.isDataTable(actTable)) {
      $(actTable).DataTable({
        responsive: true,
        autoWidth: false,
        paging: true,
        searching: true,
        ordering: true,
        pageLength: 10,
        language: {
          search: "Search:",
          lengthMenu: "Show _MENU_ per page",
          info: "Showing _START_–_END_ of _TOTAL_",
          infoEmpty: "No activities to show",
          paginate: { previous: "‹", next: "›" }
        }
      });
    }
  });