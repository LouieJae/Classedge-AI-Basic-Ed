function getCookie(name) {
  var v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? decodeURIComponent(v[2]) : '';
}
function getCsrfToken() {
  // Prefer the cookie (works after Django has issued one). Fall back to the
  // hidden input rendered by the page's the csrf_token template tag tag for the first POST.
  var c = getCookie('csrftoken');
  if (c) return c;
  var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
  return input ? input.value : '';
}
// Move the modal to <body> on first open so position:fixed truly covers the
// viewport. Ancestors inside .app can otherwise create a containing block that
// clips the backdrop.
(function teleportSaModal() {
  var m = document.getElementById('sa-modal');
  if (m && m.parentNode !== document.body) document.body.appendChild(m);
})();

function subjectAnnouncementsOpen(mode, data) {
  document.getElementById('sa-modal-eyebrow').textContent = mode === 'edit' ? 'Edit post' : 'New post';
  document.getElementById('sa-modal-title').textContent = mode === 'edit' ? 'Edit announcement' : 'New announcement';
  document.getElementById('sa-submit-btn').textContent = mode === 'edit' ? 'Save' : 'Post';
  document.getElementById('sa-id').value = data.id || '';
  document.getElementById('sa-subject-id').value = data.subjectId || '';
  document.getElementById('sa-subject-name').value = data.subjectName || '';
  document.getElementById('sa-title').value = data.title || '';
  document.getElementById('sa-description').value = data.description || '';
  document.getElementById('sa-date').value = data.date || new Date().toISOString().slice(0, 10);
  document.getElementById('sa-modal').classList.add('open');
  setTimeout(function() { document.getElementById('sa-title').focus(); }, 50);
}
function subjectAnnouncementsClose() {
  document.getElementById('sa-modal').classList.remove('open');
  document.getElementById('sa-form').reset();
}
async function subjectAnnouncementsSubmit() {
  var id = document.getElementById('sa-id').value;
  var payload = {
    subject_id: document.getElementById('sa-subject-id').value,
    title: document.getElementById('sa-title').value.trim(),
    description: document.getElementById('sa-description').value.trim(),
    date: document.getElementById('sa-date').value,
  };
  var url = id
    ? '/api/subject-announcements/' + id + '/'
    : '/api/subject-announcements/';
  var method = id ? 'PUT' : 'POST';
  try {
    var r = await fetch(url, {
      method: method,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      var err = await r.json().catch(function(){return {};});
      alert(err.error || 'Failed to save announcement.');
      return;
    }
    subjectAnnouncementsClose();
    location.reload();
  } catch (_) {
    alert('Network error.');
  }
}
document.addEventListener('click', function(e) {
  var openCreate = e.target.closest('.sa-open-create');
  if (openCreate) {
    subjectAnnouncementsOpen('create', {
      subjectId: openCreate.dataset.subjectId,
      subjectName: openCreate.dataset.subjectName,
    });
    return;
  }
  var openEdit = e.target.closest('.sa-open-edit');
  if (openEdit) {
    var card = openEdit.closest('.sa-subject-card');
    subjectAnnouncementsOpen('edit', {
      id: openEdit.dataset.id,
      subjectId: openEdit.dataset.subjectId,
      subjectName: card.querySelector('.sa-subject-name').textContent,
      title: openEdit.dataset.title,
      description: openEdit.dataset.description,
      date: openEdit.dataset.date,
    });
    return;
  }
  var delBtn = e.target.closest('.sa-delete');
  if (delBtn) {
    if (!confirm('Delete this announcement?')) return;
    fetch('/api/subject-announcements/' + delBtn.dataset.id + '/', {
      method: 'DELETE',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': getCsrfToken() },
    }).then(function(r) {
      if (r.ok) location.reload();
      else alert('Failed to delete.');
    }).catch(function() { alert('Network error.'); });
  }
});
