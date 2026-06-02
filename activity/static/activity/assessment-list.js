    ;(function () {
      var search = document.getElementById('actSearch')
      var body = document.getElementById('actBody')
      var summary = document.getElementById('actSummary')
      var noMatch = document.getElementById('actNoMatch')
      var chipsRow = document.getElementById('actChips')
      var rows = body ? Array.prototype.slice.call(body.querySelectorAll('.act-row')) : []
      var activeType = ''

      function update() {
        var q = (search && search.value || '').trim().toLowerCase()
        var visible = 0
        rows.forEach(function (row) {
          var name = row.getAttribute('data-name') || ''
          var typeId = row.getAttribute('data-type-id') || ''
          var matchText = !q || name.indexOf(q) !== -1
          var matchType = !activeType || typeId === activeType
          var show = matchText && matchType
          row.style.display = show ? '' : 'none'
          if (show) {
            visible++
            var counter = row.querySelector('.counter')
            if (counter) counter.textContent = visible
          }
        })
        if (summary) {
          var total = rows.length
          summary.textContent = (q || activeType)
            ? visible + ' of ' + total + ' activit' + (total === 1 ? 'y' : 'ies')
            : total + ' activit' + (total === 1 ? 'y' : 'ies')
        }
        if (noMatch) noMatch.style.display = (q || activeType) && visible === 0 ? '' : 'none'
      }

      if (search) search.addEventListener('input', update)
      if (chipsRow) {
        chipsRow.addEventListener('click', function (e) {
          var btn = e.target.closest('.act-chip')
          if (!btn) return
          chipsRow.querySelectorAll('.act-chip').forEach(function (c) { c.classList.remove('is-active') })
          btn.classList.add('is-active')
          activeType = btn.getAttribute('data-type-id') || ''
          update()
        })
      }

      // Subject picker modal — teleport to <body> so position:fixed covers
      // the whole viewport (the .page-content wrapper has a transform).
      var picker = document.getElementById('actSubjectPicker')
      var pickerType = document.getElementById('actModalType')
      var pickerList = document.getElementById('actSubjectList')
      var currentTypeId = ''
      if (picker && picker.parentElement !== document.body) {
        document.body.appendChild(picker)
      }

      function openPicker(typeId, typeName) {
        if (!picker) return
        currentTypeId = typeId
        if (pickerType) pickerType.textContent = 'subject for ' + typeName
        if (pickerList) {
          pickerList.querySelectorAll('a').forEach(function (a) {
            var base = a.getAttribute('data-base-url') || ''
            a.setAttribute('href', base + (typeId ? '?activity_type_id=' + typeId : ''))
          })
        }
        picker.classList.add('is-open')
        picker.setAttribute('aria-hidden', 'false')
        document.body.style.overflow = 'hidden'
      }
      function closePicker() {
        if (!picker) return
        picker.classList.remove('is-open')
        picker.setAttribute('aria-hidden', 'true')
        document.body.style.overflow = ''
      }

      // "New activity" dropdown
      var addDropdown = document.getElementById('actAddDropdown')
      var addTrigger = document.getElementById('actAddTrigger')
      function closeAddMenu() {
        if (!addDropdown) return
        addDropdown.classList.remove('is-open')
        if (addTrigger) addTrigger.setAttribute('aria-expanded', 'false')
      }
      if (addTrigger) {
        addTrigger.addEventListener('click', function (e) {
          e.stopPropagation()
          var open = addDropdown.classList.toggle('is-open')
          addTrigger.setAttribute('aria-expanded', open ? 'true' : 'false')
        })
      }

      document.querySelectorAll('.act-add-item').forEach(function (btn) {
        btn.addEventListener('click', function () {
          closeAddMenu()
          openPicker(btn.getAttribute('data-type-id') || '', btn.getAttribute('data-type-name') || 'activity')
        })
      })

      // Per-row action menus — teleport menu to <body> with position:fixed
      // so parent overflow:hidden / overflow-x:auto can't clip it.
      function closeAllActionMenus() {
        // Find every teleported menu (regardless of whether its wrapper still
        // has the is-open class) and put it back where it came from.
        document.querySelectorAll('.act-actions-menu[data-cltp="1"]').forEach(function (m) {
          // Clear every inline style we set so the original class rules win again.
          m.removeAttribute('style')
          m.dataset.cltp = ''
          var origin = m._origWrap
          if (origin && origin.parentNode) origin.appendChild(m)
          m._origWrap = null
        })
        document.querySelectorAll('.act-actions.is-open').forEach(function (w) {
          w.classList.remove('is-open')
        })
      }
      function positionActionMenu(btn, menu, wrap) {
        // Move to body so we escape ANY ancestor overflow / transform.
        menu._origWrap = wrap
        document.body.appendChild(menu)
        menu.dataset.cltp = '1'
        // Override the class-level "right: 0" with explicit "auto"
        // (otherwise the menu stretches between left and right:0 → huge!)
        menu.style.position = 'fixed'
        menu.style.right = 'auto'
        menu.style.bottom = 'auto'
        menu.style.width = 'auto'
        menu.style.maxWidth = '180px'
        menu.style.display = 'block'
        menu.style.zIndex = '1000'
        // Measure first
        menu.style.top = '-9999px'
        menu.style.left = '0px'
        var rect = btn.getBoundingClientRect()
        var menuRect = menu.getBoundingClientRect()
        var spaceBelow = window.innerHeight - rect.bottom
        var spaceAbove = rect.top
        var top = (spaceBelow >= menuRect.height + 8 || spaceBelow >= spaceAbove)
          ? rect.bottom + 4
          : Math.max(8, rect.top - menuRect.height - 4)
        var left = rect.right - menuRect.width
        if (left + menuRect.width > window.innerWidth - 8) {
          left = window.innerWidth - menuRect.width - 8
        }
        if (left < 8) left = 8
        menu.style.top = top + 'px'
        menu.style.left = left + 'px'
      }
      document.querySelectorAll('.act-actions').forEach(function (wrap) {
        var btn = wrap.querySelector('.act-actions-btn')
        var menu = wrap.querySelector('.act-actions-menu')
        if (!btn || !menu) return
        btn.addEventListener('click', function (e) {
          e.stopPropagation()
          var wasOpen = wrap.classList.contains('is-open')
          closeAllActionMenus()
          if (!wasOpen) {
            wrap.classList.add('is-open')
            positionActionMenu(btn, menu, wrap)
          }
        })
      })
      window.addEventListener('scroll', closeAllActionMenus, true)
      window.addEventListener('resize', closeAllActionMenus)
      document.querySelectorAll('.act-actions-menu form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
          if (!confirm(form.getAttribute('data-confirm'))) e.preventDefault()
        })
      })

      document.addEventListener('click', function (e) {
        if (!e.target.closest('.act-add')) closeAddMenu()
        // The menu is teleported to <body>, so check both the wrapper AND the menu itself.
        if (!e.target.closest('.act-actions') && !e.target.closest('.act-actions-menu')) {
          closeAllActionMenus()
        }
      })
      if (picker) {
        picker.addEventListener('click', function (e) {
          if (e.target === picker || e.target.closest('[data-close-picker]')) closePicker()
        })
        document.addEventListener('keydown', function (e) {
          if (e.key === 'Escape') closePicker()
        })
      }
    })()
  