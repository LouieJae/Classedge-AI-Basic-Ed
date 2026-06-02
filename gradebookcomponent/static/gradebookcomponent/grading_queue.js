  (function () {
    'use strict'

    const rows = Array.from(document.querySelectorAll('.gq-row'))
    if (!rows.length) return

    const search = document.getElementById('gqSearch')
    const chips = document.querySelectorAll('.gq-chip')
    const emptyFilter = document.getElementById('gqEmptyFilter')

    let activeFilter = 'all'

    // Aggregate counts
    const totalCount = rows.length
    const needsCount = rows.filter(r => r.dataset.badge === 'Needs grading').length
    const reviewCount = totalCount - needsCount
    const subjects = new Set(rows.map(r => r.dataset.subject))

    const setText = (id, value) => {
      const el = document.getElementById(id)
      if (el) el.textContent = value
    }
    setText('gqStatTotal', totalCount)
    setText('gqStatNeeds', needsCount)
    setText('gqStatReview', reviewCount)
    setText('gqStatSubjects', subjects.size)
    setText('gqCountAll', totalCount)
    setText('gqCountNeeds', needsCount)
    setText('gqCountReview', reviewCount)

    function applyFilters() {
      const qRaw = (search.value || '').trim()
      const q = qRaw.toLowerCase()
      let visible = 0
      rows.forEach(function (row) {
        const blob = [
          row.dataset.name,
          row.dataset.subject,
          row.dataset.activity,
        ].join(' ').toLowerCase()
        const matchSearch = !q || blob.includes(q)
        const matchFilter = activeFilter === 'all' || row.dataset.badge === activeFilter
        const show = matchSearch && matchFilter
        row.style.display = show ? '' : 'none'
        if (show) {
          visible++
          if (window.ClHighlight) window.ClHighlight.wrap(row, qRaw)
        } else if (window.ClHighlight) {
          window.ClHighlight.clear(row)
        }
      })
      if (emptyFilter) emptyFilter.hidden = (visible !== 0)
    }

    if (search) search.addEventListener('input', applyFilters)
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        chips.forEach(c => c.classList.remove('is-active'))
        chip.classList.add('is-active')
        activeFilter = chip.dataset.filter || 'all'
        applyFilters()
      })
    })
  })()