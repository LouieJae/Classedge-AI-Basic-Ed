  document.addEventListener('DOMContentLoaded', function () {
    var imgContainer = document.getElementById('image-container');
    var imgBtn = document.getElementById('image-fullscreen-btn');
    if (imgBtn) {
      imgBtn.addEventListener('click', function () {
        if (!document.fullscreenElement) {
          (imgContainer.requestFullscreen
            || imgContainer.webkitRequestFullscreen
            || imgContainer.msRequestFullscreen).call(imgContainer);
          imgBtn.innerHTML = '<i class="fas fa-compress"></i>';
        } else {
          document.exitFullscreen();
          imgBtn.innerHTML = '<i class="fas fa-expand"></i>';
        }
      });
    }
  });