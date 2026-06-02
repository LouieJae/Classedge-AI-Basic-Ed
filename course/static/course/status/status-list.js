    function getCookie(name) {
      let cookieValue = null
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';')
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim()
          if (cookie.substring(0, name.length + 1) === name + '=') {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
            break
          }
        }
      }
      return cookieValue
    }
    const csrfToken = getCookie('csrftoken')
    
    function confirmDelete(statusPointsId) {
      Swal.fire({
        title: 'Are you sure?',
        text: "You won't be able to revert this!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#1b4332',
        cancelButtonColor: '#a0a4b8',
        confirmButtonText: 'Yes, delete it!'
      }).then((result) => {
        if (result.isConfirmed) {
          fetch(`/status/delete-points/${statusPointsId}/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken }
          }).then((response) => {
            if (response.ok) {
              Swal.fire({
                title: 'Deleted!',
                text: 'The status points entry has been deleted.',
                icon: 'success',
                confirmButtonColor: '#1b4332'
              }).then(() => location.reload())
            } else {
              Swal.fire({ title: 'Error!', text: 'There was an issue deleting the entry.', icon: 'error', confirmButtonColor: '#1b4332' })
            }
          })
        }
      })
    }
    
    document.addEventListener('DOMContentLoaded', function () {
      // Compute summary stats from rendered rows
      const rows = document.querySelectorAll('#spTbody .sp-row')
      if (rows.length) {
        let sum = 0,
          max = 0
        rows.forEach((r) => {
          const numEl = r.querySelector('.sp-points-num')
          const v = parseFloat(numEl ? numEl.textContent : 0)
          if (!isNaN(v)) {
            sum += v
            if (v > max) max = v
          }
        })
        const avg = (sum / rows.length).toFixed(1)
        const setStat = (k, v) => {
          const el = document.querySelector(`[data-stat="${k}"]`)
          if (el) el.textContent = v
        }
        setStat('max', max.toFixed(1))
        setStat('avg', avg)
      }
    
      // Realtime search
      const searchInput = document.getElementById('spSearchInput')
      const countEl = document.getElementById('spCount')
      if (searchInput) {
        searchInput.addEventListener('input', () => {
          const q = searchInput.value.trim().toLowerCase()
          let visible = 0
          rows.forEach((row) => {
            const name = row.dataset.name || ''
            const show = !q || name.includes(q)
            row.style.display = show ? '' : 'none'
            if (show) visible++
          })
          if (countEl) {
            countEl.textContent = q ? `${visible} of ${rows.length} matching "${searchInput.value.trim()}"` : `${rows.length} entr${rows.length === 1 ? 'y' : 'ies'}`
          }
        })
      }
    })
  