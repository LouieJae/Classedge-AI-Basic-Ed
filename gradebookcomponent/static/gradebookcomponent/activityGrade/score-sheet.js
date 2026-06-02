    (function () {
      'use strict'

      const rows = Array.from(document.querySelectorAll('.ss-row'))
      const search = document.getElementById('ssSearch')
      const chips = document.querySelectorAll('.ss-chip')
      const emptyFilter = document.getElementById('ssEmptyFilter')
      let activeFilter = 'all'

      function rowStatus(row) {
        const score = parseFloat(row.dataset.score) || 0
        let passing = parseFloat(row.dataset.passing) || 0
        const max = parseFloat(row.dataset.max) || 0
        const submitted = row.dataset.submitted === '1'
        if (passing > 0 && passing <= 1 && max > 0) passing = passing * max
        if (!submitted) return 'pending'
        return score >= passing ? 'pass' : 'fail'
      }

      function tokenColor(name, fallback) {
        const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
        return v || fallback
      }

      const forest = tokenColor('--forest', '#1b4332')
      const rose = tokenColor('--rose', '#c08479')
      const gold = tokenColor('--gold', '#b7925a')
      const muted = tokenColor('--ink-muted', '#a0a4b8')

      rows.forEach(function (row) {
        const score = parseFloat(row.dataset.score) || 0
        const max = parseFloat(row.dataset.max) || 0
        const submitted = row.dataset.submitted === '1'
        const status = rowStatus(row)
        const pct = max > 0 ? Math.max(0, Math.min(100, (score / max) * 100)) : 0

        const fill = row.querySelector('.ss-bar-fill')
        const text = row.querySelector('.ss-bar-text')
        const pill = row.querySelector('.ss-grade-pill')

        if (!submitted) {
          fill.style.width = '0%'
          fill.style.background = muted
          text.textContent = '—'
        } else {
          fill.style.width = pct.toFixed(1) + '%'
          fill.style.background = status === 'pass' ? forest : rose
          text.textContent = pct.toFixed(0) + '%'
        }

        if (pill) {
          if (!submitted) {
            pill.classList.add('is-pending')
            pill.innerHTML = '<i class="fas fa-clock"></i> Pending'
          } else if (status === 'pass') {
            pill.classList.add('is-pass')
            pill.innerHTML = '<i class="fas fa-check"></i> Pass'
          } else {
            pill.classList.add('is-fail')
            pill.innerHTML = '<i class="fas fa-xmark"></i> Fail'
          }
        }
      })

      // Aggregate stats
      const submittedRows = rows.filter(r => r.dataset.submitted === '1')
      const submittedCount = submittedRows.length
      const passCount = rows.filter(r => rowStatus(r) === 'pass').length
      const avgPct = submittedCount > 0
        ? submittedRows.reduce(function (acc, r) {
            const s = parseFloat(r.dataset.score) || 0
            const m = parseFloat(r.dataset.max) || 0
            return acc + (m > 0 ? (s / m) * 100 : 0)
          }, 0) / submittedCount
        : 0

      const totalEl = document.getElementById('ssTotalStudents')
      const avgEl = document.getElementById('ssClassAvg')
      const rateEl = document.getElementById('ssPassRate')
      const submEl = document.getElementById('ssSubmitted')

      if (totalEl) totalEl.textContent = rows.length
      if (avgEl) avgEl.textContent = submittedCount > 0 ? avgPct.toFixed(0) + '%' : '—'
      if (rateEl) rateEl.textContent = rows.length > 0 ? Math.round((passCount / rows.length) * 100) + '%' : '—'
      if (submEl) submEl.textContent = submittedCount + ' / ' + rows.length

      // Mirror the same numbers into the print-only summary line so the
      // printed sheet always carries real figures (the .ss-stats card row
      // is hidden under @media print to avoid duplicating the masthead).
      const printTotal = document.querySelector('[data-print-total]')
      const printSubm = document.querySelector('[data-print-submitted]')
      const printAvg = document.querySelector('[data-print-avg]')
      const printRate = document.querySelector('[data-print-passrate]')
      if (printTotal) printTotal.textContent = rows.length
      if (printSubm) printSubm.textContent = submittedCount + ' / ' + rows.length
      if (printAvg) printAvg.textContent = submittedCount > 0 ? avgPct.toFixed(0) + '%' : '—'
      if (printRate) printRate.textContent = rows.length > 0 ? Math.round((passCount / rows.length) * 100) + '%' : '—'

      // Search + filter
      function applyFilters() {
        const qRaw = (search.value || '').trim()
        const q = qRaw.toLowerCase()
        let visible = 0
        rows.forEach(function (row) {
          const name = (row.dataset.name || '').toLowerCase()
          const email = (row.dataset.email || '').toLowerCase()
          const matchSearch = !q || name.includes(q) || email.includes(q)
          const matchFilter = activeFilter === 'all' || rowStatus(row) === activeFilter
          const show = matchSearch && matchFilter
          row.style.display = show ? '' : 'none'
          if (show) {
            visible++
            if (window.ClHighlight) window.ClHighlight.wrap(row, qRaw)
          } else if (window.ClHighlight) {
            window.ClHighlight.clear(row)
          }
        })
        if (emptyFilter) emptyFilter.hidden = (visible !== 0 || rows.length === 0)
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

      // CSV export
      const exportBtn = document.getElementById('ssExportBtn')
      if (exportBtn) {
        exportBtn.addEventListener('click', function () {
          const header = ['#', 'Student', 'Email', 'Status', 'Submitted', 'Score', 'Max', 'Percent', 'Result']
          const lines = [header.join(',')]
          rows.forEach(function (row, idx) {
            const name = row.dataset.name || ''
            const email = row.dataset.email || ''
            const score = parseFloat(row.dataset.score) || 0
            const max = parseFloat(row.dataset.max) || 0
            const submitted = row.dataset.submitted === '1'
            const pct = max > 0 ? (score / max) * 100 : 0
            const status = rowStatus(row)
            const dateCell = row.querySelector('.ss-date')
            const dateText = dateCell ? dateCell.innerText.replace(/\s+/g, ' ').trim() : ''
            const cells = [
              idx + 1,
              '"' + name.replace(/"/g, '""') + '"',
              '"' + email.replace(/"/g, '""') + '"',
              submitted ? 'Submitted' : 'Pending',
              '"' + dateText + '"',
              score.toFixed(0),
              max.toFixed(0),
              submitted ? pct.toFixed(1) + '%' : '',
              submitted ? (status === 'pass' ? 'Pass' : 'Fail') : 'Pending',
            ]
            lines.push(cells.join(','))
          })
          const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = 'score-sheet.csv'
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          URL.revokeObjectURL(url)
        })
      }
    })()
  