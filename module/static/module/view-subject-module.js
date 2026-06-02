  function enterFs(id, btn) {
    var el = document.getElementById(id);
    if (!el) return;
    if (!document.fullscreenElement) {
      var req = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen;
      if (req) req.call(el);
      if (btn) btn.innerHTML = '<i class="fas fa-compress"></i>';
    } else {
      (document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen).call(document);
      if (btn) btn.innerHTML = '<i class="fas fa-expand"></i>';
    }
  }
  document.addEventListener('fullscreenchange', function () {
    if (!document.fullscreenElement) {
      document.querySelectorAll('.lesson-fs-btn').forEach(function (b) {
        b.innerHTML = '<i class="fas fa-expand"></i>';
      });
    }
  });