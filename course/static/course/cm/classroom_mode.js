/* Classroom Mode — page logic.
 * Extracted from course/templates/course/classroom_mode.html so the
 * page logic is cacheable / auditable. The template still injects a
 * small synchronous bridge for the elapsed-class-session timer
 * (needs {{ subject.id }}) and for the Django messages → toast
 * pipeline (needs the messages framework rendered server-side).
 */

(function () {
  if (window.__cmExitPromptBound) return;
  window.__cmExitPromptBound = true;

  function isExitLink(el) {
    if (!el || el.tagName !== 'A') return false;
    if (el.hasAttribute('data-no-cm-exit-prompt')) return false;
    if (el.hasAttribute('data-cm-exit')) return true;
    var href = el.getAttribute('href') || '';
    return href.indexOf('/course/list') !== -1;
  }

  function tagExitLinks() {
    document.querySelectorAll('a[href]').forEach(function (a) {
      if (isExitLink(a)) a.setAttribute('data-cm-no-spa', 'true');
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tagExitLinks);
  } else {
    tagExitLinks();
  }

  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a') : null;
    if (!isExitLink(a)) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;

    e.preventDefault();
    e.stopImmediatePropagation();

    var href = a.getAttribute('href');
    if (typeof Swal === 'undefined') { window.location.href = href; return; }

    Swal.fire({
      title: 'Exit Classroom Mode?',
      text: 'You are about to leave Classroom Mode. Any unsaved changes will be lost.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Yes, exit',
      cancelButtonText: 'Stay',
      confirmButtonColor: '#c0392b',
      cancelButtonColor: '#6b7280',
      reverseButtons: true,
      focusCancel: true,
      allowOutsideClick: false
    }).then(function (result) {
      if (result.isConfirmed) window.location.href = href;
    });
  }, true);
})();

function confirmDeleteLesson(moduleId) {
  Swal.fire({
    title: 'Are you sure?',
    text: 'This lesson will be deleted and cannot be recovered!',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#3085d6',
    cancelButtonColor: '#d33',
    confirmButtonText: 'Yes, delete it!',
    cancelButtonText: 'Cancel'
  }).then((result) => {
    if (result.isConfirmed) {
      window.location.href = `/deleteModule/${moduleId}/`;
    }
  });
}

window.displayToast = function (message, icon) {
  Swal.fire({
    toast: true,
    position: 'top-end',
    icon: icon,
    title: message,
    showConfirmButton: false,
    timer: 5000,
    timerProgressBar: true,
  });
};

$(document).ready(function () {
  $(document).on('click', '.selectAll', function () {
    const statusId = $(this).data('status');
    $(`.status-${statusId}`).prop('checked', true);
  });

  // Defensive guard: any stray .modal that managed to acquire the
  // .show class on initial render gets cleared so the page never
  // boots with a modal already open.
  $('.modal.show').removeClass('show').css('display', '');
  $('.modal-backdrop').remove();
  $('body').removeClass('modal-open').css('overflow', '').css('padding-right', '');
});

document.addEventListener('DOMContentLoaded', function () {
  const dateInput = document.getElementById('attendanceDate');
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.setAttribute('min', today);
  }

  var clockTime = document.getElementById('cmClockTime');
  var clockAmpm = document.getElementById('cmClockAmpm');
  var clockDate = document.getElementById('cmClockDate');
  var DAYS = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];

  function tickClock() {
    var d = new Date();
    var h = d.getHours();
    var m = d.getMinutes();
    var ampm = h >= 12 ? 'PM' : 'AM';
    var h12 = h % 12 || 12;
    if (clockTime) clockTime.textContent = (h12 < 10 ? ' ' + h12 : h12) + ':' + (m < 10 ? '0' + m : m);
    if (clockAmpm) clockAmpm.textContent = ampm;
    if (clockDate) {
      var longDate = d.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
      clockDate.textContent = DAYS[d.getDay()] + ' · ' + longDate;
    }
  }
  tickClock();
  setInterval(tickClock, 1000);

  var nowDow = DAYS[new Date().getDay()];
  var dayOrder = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var todayIdx = dayOrder.indexOf(nowDow);
  var todayLessons = 0;
  var todayCard = null;
  var totalLessons = 0;
  var totalActivities = 0;
  document.querySelectorAll('.cm-day').forEach(function (el) {
    var name = (el.getAttribute('data-day') || '').trim();
    var idx = dayOrder.indexOf(name);
    var lessonsInDay = el.querySelectorAll('.cm-lesson');
    totalLessons += lessonsInDay.length;
    lessonsInDay.forEach(function (lesson) {
      var meta = lesson.querySelector('.meta');
      if (!meta) return;
      var match = (meta.textContent || '').match(/(\d+)\s*activit/);
      if (match) totalActivities += parseInt(match[1], 10) || 0;
    });
    if (name === nowDow) {
      el.classList.add('is-today');
      todayCard = el;
      todayLessons = lessonsInDay.length;
    } else if (todayIdx > -1 && idx > -1 && idx < todayIdx) {
      el.classList.add('is-past');
    }
  });
  var statLessons = document.getElementById('cmStatLessons');
  if (statLessons) statLessons.textContent = totalLessons;

  var weekRange = document.getElementById('cmWeekRange');
  if (weekRange) {
    var today = new Date();
    var start = new Date(today); start.setDate(today.getDate() - today.getDay());
    var end = new Date(start); end.setDate(start.getDate() + 6);
    var fmt = function (d) { return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }); };
    weekRange.textContent = fmt(start) + ' – ' + fmt(end);
  }
  var statTodayLessons = document.getElementById('cmStatTodayLessons');
  var statTodayHint = document.getElementById('cmStatTodayHint');
  if (statTodayLessons) statTodayLessons.textContent = todayLessons;
  if (statTodayHint) {
    statTodayHint.textContent = todayLessons === 0
      ? 'Nothing scheduled for today.'
      : (todayLessons === 1 ? '1 lesson queued for today.' : todayLessons + ' lessons queued for today.');
  }

  var fsBtn = document.getElementById('cmFullscreenBtn');
  var fsIcon = document.getElementById('cmFullscreenIcon');
  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      (document.documentElement.requestFullscreen ||
       document.documentElement.webkitRequestFullscreen ||
       document.documentElement.msRequestFullscreen).call(document.documentElement);
    } else {
      (document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen).call(document);
    }
  }
  function syncFsState() {
    var fs = !!document.fullscreenElement;
    document.body.classList.toggle('cm-fullscreen', fs);
    if (fsIcon) fsIcon.className = fs ? 'fas fa-compress' : 'fas fa-expand';
  }
  if (fsBtn) fsBtn.addEventListener('click', toggleFullscreen);
  document.addEventListener('fullscreenchange', syncFsState);
  document.addEventListener('webkitfullscreenchange', syncFsState);

  document.addEventListener('keydown', function (e) {
    var t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
    if (e.key === 'f' || e.key === 'F') { e.preventDefault(); toggleFullscreen(); }
    if (e.key === 't' || e.key === 'T') {
      if (todayCard) { e.preventDefault(); todayCard.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
    }
  });
});

// Synchronous timer hydration. Reads subject id from the timer
// element's data attribute (set in the template), so this script can
// live in /static. Runs immediately on parse — the template loads
// this with defer:false on purpose so the elapsed-class-time pill is
// already filled in by first paint after a hard refresh.
(function () {
  try {
    var disp = document.getElementById('classroomTimerDisplay');
    if (!disp) return;
    var subjectId = disp.dataset.subjectId;
    var raw = localStorage.getItem('classSessionTimer');
    if (!raw) return;
    var data = JSON.parse(raw);
    if (!data || String(data.subjectId) !== String(subjectId) || !data.timeStarted) return;
    var start = new Date(data.timeStarted);
    if (isNaN(start.getTime())) return;
    var elapsed = Math.max(0, Math.floor((Date.now() - start.getTime()) / 1000));
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var h = pad(Math.floor(elapsed / 3600));
    var m = pad(Math.floor((elapsed % 3600) / 60));
    var s = pad(elapsed % 60);
    var text = document.getElementById('classroomTimerText');
    if (text) text.textContent = h + ':' + m + ':' + s;
    disp.classList.add('is-on');
  } catch (e) { /* localStorage unavailable — silent fallback */ }
})();
