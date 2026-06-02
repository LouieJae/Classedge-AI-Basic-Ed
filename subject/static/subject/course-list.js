  (function () {
    const perPage = document.getElementById('subjPerPage');
    const form = document.getElementById('subjFilterForm');
    if (perPage && form) perPage.addEventListener('change', () => form.submit());
  })();

  function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || document.querySelector('meta[name="csrf-token"]')?.content;
  }
  function confirmDelete(subjectId) {
    Swal.fire({
      title: 'Are you sure?',
      text: "You won't be able to revert this!",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#1b4332',
      cancelButtonColor: '#a0a4b8',
      confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
      if (!result.isConfirmed) return;
      fetch(`/delete_subject/${subjectId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() }
      }).then((response) => {
        if (response.ok) {
          Swal.fire({
            title: 'Deleted!', text: 'The course has been deleted.', icon: 'success', confirmButtonColor: '#1b4332',
          }).then(() => location.reload());
        } else {
          Swal.fire({ title: 'Error', text: 'There was an issue deleting the course.', icon: 'error', confirmButtonColor: '#1b4332' });
        }
      });
    });
  }

  (function () {
    if (!window.bootstrap || !document.body) return;

    function teleportShow(e) {
      var trigger = e.target;
      if (!trigger.classList || !trigger.classList.contains('dropdown-toggle')) return;
      if (!trigger.closest('.subj-table')) return;
      var menu = trigger.parentNode.querySelector('.dropdown-menu');
      if (!menu) return;
      menu._origParent = menu.parentNode;
      menu._origNextSibling = menu.nextSibling;
      menu.classList.add('subj-action-menu');
      var rect = trigger.getBoundingClientRect();
      menu.style.transform = 'none';
      menu.style.inset = 'auto';
      menu.style.bottom = 'auto';
      menu.style.position = 'fixed';
      menu.style.top = (rect.bottom + 6) + 'px';
      menu.style.left = 'auto';
      menu.style.right = (window.innerWidth - rect.right) + 'px';
      menu.style.zIndex = '1080';
      menu.style.minWidth = '200px';
      document.body.appendChild(menu);
      var menuRect = menu.getBoundingClientRect();
      if (menuRect.bottom > window.innerHeight - 8) {
        var topAbove = rect.top - menuRect.height - 6;
        menu.style.top = Math.max(8, topAbove) + 'px';
      }
    }

    function teleportHide(e) {
      var trigger = e.target;
      if (!trigger.classList || !trigger.classList.contains('dropdown-toggle')) return;
      var menu = document.querySelector('.dropdown-menu[aria-labelledby="' + trigger.id + '"]');
      if (!menu || !menu._origParent) return;
      menu.style.position = '';
      menu.style.top = '';
      menu.style.left = '';
      menu.style.right = '';
      menu.style.bottom = '';
      menu.style.transform = '';
      menu.style.inset = '';
      menu.style.zIndex = '';
      menu.style.minWidth = '';
      if (menu._origNextSibling) {
        menu._origParent.insertBefore(menu, menu._origNextSibling);
      } else {
        menu._origParent.appendChild(menu);
      }
      menu._origParent = null;
      menu._origNextSibling = null;
    }

    document.addEventListener('shown.bs.dropdown', teleportShow);
    document.addEventListener('hide.bs.dropdown', teleportHide);
    function reposition() {
      var open = document.querySelector('.dropdown-menu.show');
      if (!open || !open._origParent) return;
      var trigger = document.getElementById(open.getAttribute('aria-labelledby'));
      if (!trigger) return;
      var rect = trigger.getBoundingClientRect();
      open.style.top = (rect.bottom + 6) + 'px';
      open.style.right = (window.innerWidth - rect.right) + 'px';
    }
    window.addEventListener('scroll', reposition, true);
    window.addEventListener('resize', reposition);
  })();