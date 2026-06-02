function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function sendFriendRequest(userId) {
  fetch(`/social/friend/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({ to_user: userId }),
  })
    .then(r => r.json().then(d => ({ ok: r.ok, data: d })).catch(() => ({ ok: r.ok, data: {} })))
    .then(({ ok, data }) => {
      if (ok) location.reload();
      else alert(data.error || data.detail || 'Could not send request.');
    })
    .catch(() => alert('Network error. Try again.'));
}

function acceptFriendRequest(requestId) {
  fetch(`/social/friend/${requestId}/accept/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
  })
    .then(r => r.json().then(d => ({ ok: r.ok, data: d })).catch(() => ({ ok: r.ok, data: {} })))
    .then(({ ok, data }) => {
      if (ok) location.reload();
      else alert(data.error || 'Could not accept request.');
    });
}

function rejectFriendRequest(requestId) {
  fetch(`/social/friend/${requestId}/reject/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
  })
    .then(r => r.json().then(d => ({ ok: r.ok, data: d })).catch(() => ({ ok: r.ok, data: {} })))
    .then(({ ok, data }) => {
      if (ok) location.reload();
      else alert(data.error || 'Could not reject request.');
    });
}

function vspPreview(url, title) {
  const overlay = document.getElementById('vspPreviewOverlay');
  document.getElementById('vspPreviewImg').src = url;
  overlay.classList.add('open');
}
function vspClosePreview() {
  document.getElementById('vspPreviewOverlay').classList.remove('open');
}
document.getElementById('vspPreviewOverlay').addEventListener('click', (e) => {
  if (e.target.id === 'vspPreviewOverlay') vspClosePreview();
});

const photoTrigger = document.getElementById('profilePhotoTrigger');
const photoImg = photoTrigger ? photoTrigger.querySelector('img') : null;
if (photoTrigger && photoImg) {
  photoTrigger.addEventListener('click', () => vspPreview(photoImg.src, ''));
}
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') vspClosePreview();
});