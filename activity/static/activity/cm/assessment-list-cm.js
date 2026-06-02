/* Assessment list — Classroom Mode page logic.
 * Extracted from activity/templates/activity/assessments/assessment-list-cm.html.
 *
 * Reads two values from the page via window globals (set by a tiny
 * inline script in the template, since Django URL reversal can't
 * happen in a static file):
 *
 *   window.CM_TOGGLE_SHOW_SCORE_URL_TEMPLATE  // e.g. "/toggleShowScore/0/"
 *   window.CM_CSRF_TOKEN                       // CSRF token for AJAX
 */

// Position the row-action menu using viewport coordinates so it escapes
// the .cm-card's overflow clip. Flips above the trigger if it would
// otherwise spill past the viewport bottom; flips to align-left if it
// would clip past the right edge.
function cmPositionMenu(wrap) {
  var trigger = wrap.querySelector('.trigger');
  var menu = wrap.querySelector('.menu');
  if (!trigger || !menu) return;
  // Temporarily render so we can measure — display:block via .open is
  // already set by the time we're called.
  var tRect = trigger.getBoundingClientRect();
  var mRect = menu.getBoundingClientRect();
  var gap = 6;
  var vh = window.innerHeight || document.documentElement.clientHeight;
  var vw = window.innerWidth || document.documentElement.clientWidth;

  var top = tRect.bottom + gap;
  if (top + mRect.height > vh - 8) {
    top = Math.max(8, tRect.top - mRect.height - gap);
  }
  var left = tRect.right - mRect.width;
  if (left < 8) left = Math.min(vw - mRect.width - 8, tRect.left);

  menu.style.top = top + 'px';
  menu.style.left = left + 'px';
}

function cmCloseAllMenus() {
  document.querySelectorAll('.cm-row-actions.open').forEach(function (w) {
    w.classList.remove('open');
  });
}

function cmToggleActions(btn) {
  var wrap = btn.closest('.cm-row-actions');
  var wasOpen = wrap.classList.contains('open');
  cmCloseAllMenus();
  if (!wasOpen) {
    wrap.classList.add('open');
    cmPositionMenu(wrap);
  }
}

document.addEventListener('click', function (e) {
  if (!e.target.closest('.cm-row-actions')) cmCloseAllMenus();
});

// Re-position (or close) when the user scrolls or resizes — a fixed
// menu otherwise stays glued to its old viewport coordinates.
['scroll', 'resize'].forEach(function (evt) {
  window.addEventListener(evt, function () {
    document.querySelectorAll('.cm-row-actions.open').forEach(cmPositionMenu);
  }, true);
});

$(function () {
  $('.show-score-checkbox').on('change', function () {
    const activityId = $(this).data('activity-id');
    const urlTpl = window.CM_TOGGLE_SHOW_SCORE_URL_TEMPLATE || '';
    if (!urlTpl) return;
    $.ajax({
      type: 'POST',
      url: urlTpl.replace('0', activityId),
      data: { csrfmiddlewaretoken: window.CM_CSRF_TOKEN || '' },
      success: function () {},
      error: function () {}
    });
  });

  $(document).on('click', '.delete-btn', function (event) {
    event.preventDefault();
    const form = $(this).closest('form');
    Swal.fire({
      title: 'Delete this activity?',
      text: "This action can't be undone.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#c08479',
      cancelButtonColor: '#6c7080',
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      reverseButtons: true,
    }).then((result) => {
      if (result.isConfirmed) form.submit();
    });
  });

  const cmTable = document.querySelector('.cm-activity-table');
  if (cmTable && !$.fn.DataTable.isDataTable(cmTable)) {
    $(cmTable).DataTable({
      responsive: true,
      autoWidth: false,
      paging: true,
      searching: true,
      ordering: true,
      pageLength: 10,
      language: {
        search: '',
        searchPlaceholder: 'Search activities…',
        paginate: {
          first:    '<i class="fas fa-angles-left"></i>',
          previous: '<i class="fas fa-angle-left"></i>',
          next:     '<i class="fas fa-angle-right"></i>',
          last:     '<i class="fas fa-angles-right"></i>',
        },
      },
    });
  }
});
