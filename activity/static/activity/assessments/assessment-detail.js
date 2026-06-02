  let answerActivityClicked = false;
  function confirmActivityStart() {
    if (answerActivityClicked) return false;
    answerActivityClicked = true;
    const btn = document.getElementById('ad-start-btn');
    if (btn) {
      btn.style.pointerEvents = 'none';
      btn.style.opacity = '0.65';
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';
    }
    return true;
  }