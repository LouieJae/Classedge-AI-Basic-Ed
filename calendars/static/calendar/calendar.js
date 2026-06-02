// ═══════════════════════════════════════════════════════════════
// Calendar page — combined client logic.
// Django-bound context lives on window.CL_CALENDAR_CONTEXT (set
// by an inline bootstrap script in calendar.html).
// ═══════════════════════════════════════════════════════════════

// ── Block A: helpers + initial table/modal setup ──
  document.addEventListener("DOMContentLoaded", function () {
    function getCSRFToken() {
      let cookieValue = null;
      if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.startsWith("csrftoken=")) {
            cookieValue = decodeURIComponent(cookie.substring(10));
            break;
          }
        }
      }
      return cookieValue;
    }
    const csrfToken = getCSRFToken();

    // Holiday form submission (time keepers only)
    const eventForm = document.getElementById("eventForm");
    if (eventForm) {
      eventForm.addEventListener("submit", function (e) {
        e.preventDefault();
        Swal.fire({
          title: "Confirm submission",
          text: "Do you want to save this holiday?",
          icon: "question",
          showCancelButton: true,
          confirmButtonText: "Yes, save",
          cancelButtonText: "Cancel",
          confirmButtonColor: (getComputedStyle(document.documentElement).getPropertyValue("--brand-primary") || "").trim() || "#1b4332",
          cancelButtonColor: "#a0a4b8",
        }).then((result) => {
          if (result.isConfirmed) {
            const id = document.getElementById("holidayId").value;
            const title = document.getElementById("eventTitle").value;
            const date = document.getElementById("eventDate").value;
            const holidayType = document.getElementById("holidayType").value;
            const color = document.getElementById("eventColor").value;

            const method = id ? "PUT" : "POST";
            fetch("/api/holidays/", {
              method: method,
              headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
              body: JSON.stringify({ id, title, date, holiday_type: holidayType, color }),
            })
              .then((response) => response.json())
              .then(() => {
                Swal.fire({
                  title: "Saved",
                  text: "Holiday saved successfully.",
                  icon: "success",
                  timer: 1800,
                  showConfirmButton: false,
                  confirmButtonColor: (getComputedStyle(document.documentElement).getPropertyValue("--brand-primary") || "").trim() || "#1b4332",
                }).then(() => window.location.reload());
              })
              .catch(() => {
                Swal.fire({
                  title: "Something went wrong",
                  text: "Failed to save holiday.",
                  icon: "error",
                  confirmButtonColor: (getComputedStyle(document.documentElement).getPropertyValue("--brand-primary") || "").trim() || "#1b4332",
                });
              });
          }
        });
      });
    }

    // Time keeper header button: open the holiday modal in a blank state.
    // (Clicking a calendar day still works; this is just a discoverable
    // entry point so users don't have to know about the date-select gesture.)
    const tkOpenBtn = document.getElementById("tkOpenHolidayModalBtn");
    if (tkOpenBtn) {
      tkOpenBtn.addEventListener("click", function() {
        const form = document.getElementById("eventForm");
        if (form) form.reset();
        document.getElementById("holidayId").value = "";
        document.getElementById("eventDate").value = new Date().toISOString().slice(0, 10);
        new bootstrap.Modal(document.getElementById("addEventModal")).show();
      });
    }

    // ── Registrar: institution-wide event + announcement creation ─────────
    // Both POSTs hit the existing DRF viewsets (`/api/events/` and
    // `/api/announcements/`). The model's `department` field stays null so
    // the rows are institution-wide per the user's design decision.
    const regEventForm = document.getElementById("registrarEventForm");
    const regEventModalEl = document.getElementById("registrarEventModal");
    function resetRegEventModal() {
      if (!regEventForm) return;
      regEventForm.reset();
      delete regEventForm.dataset.editingId;
      const label = document.getElementById("registrarEventModalLabel");
      if (label) label.textContent = "Create event";
      const submit = regEventForm.querySelector("button[type='submit']");
      if (submit) submit.textContent = "Create event";
      const del = document.getElementById("regEventDeleteBtn");
      if (del) del.classList.add("d-none");
    }
    if (regEventModalEl) {
      regEventModalEl.addEventListener("hidden.bs.modal", resetRegEventModal);
    }
    if (regEventForm) {
      regEventForm.addEventListener("submit", function(e) {
        e.preventDefault();
        const payload = {
          title: document.getElementById("regEventTitle").value.trim(),
          description: document.getElementById("regEventDescription").value.trim(),
          start_date: document.getElementById("regEventStart").value || null,
          end_date: document.getElementById("regEventEnd").value || null,
          time: document.getElementById("regEventTime").value || null,
          location: document.getElementById("regEventLocation").value.trim() || null,
        };
        const editingId = regEventForm.dataset.editingId;
        const url = editingId ? `/api/events/${editingId}/` : "/api/events/";
        const method = editingId ? "PATCH" : "POST";
        fetch(url, {
          method: method,
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
          body: JSON.stringify(payload),
        }).then(function(r) {
          if (!r.ok) return r.json().then(function(j) { throw new Error(JSON.stringify(j)); });
          return r.json();
        }).then(function() {
          bootstrap.Modal.getInstance(document.getElementById("registrarEventModal")).hide();
          if (typeof Swal !== "undefined") {
            Swal.fire({ icon: "success", title: editingId ? "Event updated" : "Event created", timer: 1400, showConfirmButton: false });
          }
          if (window.invalidateCalendarCache) window.invalidateCalendarCache();
          if (window.calendar && window.calendar.refetchEvents) window.calendar.refetchEvents();
        }).catch(function(err) {
          alert("Could not save event: " + (err.message || "unknown error"));
        });
      });
    }
    const regEventDeleteBtn = document.getElementById("regEventDeleteBtn");
    if (regEventDeleteBtn) {
      regEventDeleteBtn.addEventListener("click", function() {
        const id = regEventForm && regEventForm.dataset.editingId;
        if (!id) return;
        const go = function() {
          fetch(`/api/events/${id}/`, {
            method: "DELETE",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken },
          }).then(function(r) {
            if (!r.ok && r.status !== 204) throw new Error("HTTP " + r.status);
            bootstrap.Modal.getInstance(document.getElementById("registrarEventModal")).hide();
            if (typeof Swal !== "undefined") {
              Swal.fire({ icon: "success", title: "Event deleted", timer: 1400, showConfirmButton: false });
            }
            if (window.invalidateCalendarCache) window.invalidateCalendarCache();
            if (window.calendar && window.calendar.refetchEvents) window.calendar.refetchEvents();
          }).catch(function(err) {
            alert("Could not delete event: " + (err.message || "unknown error"));
          });
        };
        if (typeof Swal !== "undefined") {
          Swal.fire({
            title: "Delete this event?",
            text: "This cannot be undone.",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Delete",
            confirmButtonColor: "#b94a48",
          }).then(function(res) { if (res.isConfirmed) go(); });
        } else if (confirm("Delete this event?")) {
          go();
        }
      });
    }

    const regAnnForm = document.getElementById("registrarAnnouncementForm");
    const regAnnModal = document.getElementById("registrarAnnouncementModal");
    if (regAnnModal) {
      // Populate the optional 'link events' checklist when the modal opens.
      regAnnModal.addEventListener("show.bs.modal", function() {
        const dateInput = document.getElementById("regAnnDate");
        if (!dateInput.value) dateInput.value = new Date().toISOString().slice(0, 10);
        const list = document.getElementById("regAnnEventsList");
        list.innerHTML = '<p class="text-muted mb-0" style="font-size:13px;font-style:italic;">Loading events…</p>';
        fetch("/api/events/?page_size=50", { credentials: "same-origin" })
          .then(function(r) { return r.ok ? r.json() : { results: [] }; })
          .then(function(data) {
            const items = Array.isArray(data) ? data : (data.results || []);
            if (!items.length) {
              list.innerHTML = '<p class="text-muted mb-0" style="font-size:13px;font-style:italic;">No events to link.</p>';
              return;
            }
            // If we're editing, pre-check the announcement's linked events.
            let preChecked = [];
            try {
              preChecked = JSON.parse(regAnnForm && regAnnForm.dataset.linkedEventIds || "[]");
            } catch (_) { preChecked = []; }
            list.innerHTML = items.map(function(ev) {
              const id = ev.id;
              const title = ev.title || "(untitled)";
              const start = ev.start_date || ev.startDate || "";
              const checked = preChecked.indexOf(id) !== -1 ? " checked" : "";
              return '<div class="form-check">' +
                '<input class="form-check-input reg-ann-event-cb" type="checkbox" value="' + id + '" id="reg-ann-ev-' + id + '"' + checked + '>' +
                '<label class="form-check-label" for="reg-ann-ev-' + id + '">' + title + (start ? ' <span class="text-muted">(' + start + ')</span>' : '') + '</label>' +
                '</div>';
            }).join("");
          })
          .catch(function() {
            list.innerHTML = '<p class="text-danger mb-0" style="font-size:13px;">Failed to load events.</p>';
          });
      });
    }
    function resetRegAnnModal() {
      if (!regAnnForm) return;
      regAnnForm.reset();
      delete regAnnForm.dataset.editingId;
      delete regAnnForm.dataset.linkedEventIds;
      const label = document.getElementById("registrarAnnouncementModalLabel");
      if (label) label.textContent = "Create announcement";
      const submit = regAnnForm.querySelector("button[type='submit']");
      if (submit) submit.textContent = "Post announcement";
      const del = document.getElementById("regAnnDeleteBtn");
      if (del) del.classList.add("d-none");
    }
    if (regAnnModal) {
      regAnnModal.addEventListener("hidden.bs.modal", resetRegAnnModal);
    }
    if (regAnnForm) {
      regAnnForm.addEventListener("submit", function(e) {
        e.preventDefault();
        const linked = Array.from(document.querySelectorAll(".reg-ann-event-cb:checked"))
                        .map(function(cb) { return parseInt(cb.value, 10); });
        const payload = {
          title: document.getElementById("regAnnTitle").value.trim(),
          description: document.getElementById("regAnnDescription").value.trim(),
          date: document.getElementById("regAnnDate").value,
          // The serializer exposes a write-only `event_ids` field that
          // accepts an array of Event PKs and stores them via the M2M.
          event_ids: linked,
        };
        const editingId = regAnnForm.dataset.editingId;
        const url = editingId ? `/api/announcements/${editingId}/` : "/api/announcements/";
        const method = editingId ? "PATCH" : "POST";
        fetch(url, {
          method: method,
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
          body: JSON.stringify(payload),
        }).then(function(r) {
          if (!r.ok) return r.json().then(function(j) { throw new Error(JSON.stringify(j)); });
          return r.json();
        }).then(function() {
          bootstrap.Modal.getInstance(document.getElementById("registrarAnnouncementModal")).hide();
          if (typeof Swal !== "undefined") {
            Swal.fire({ icon: "success", title: editingId ? "Announcement updated" : "Announcement posted", timer: 1400, showConfirmButton: false });
          }
          if (window.invalidateCalendarCache) window.invalidateCalendarCache();
          if (window.calendar && window.calendar.refetchEvents) window.calendar.refetchEvents();
        }).catch(function(err) {
          alert("Could not save announcement: " + (err.message || "unknown error"));
        });
      });
    }
    const regAnnDeleteBtn = document.getElementById("regAnnDeleteBtn");
    if (regAnnDeleteBtn) {
      regAnnDeleteBtn.addEventListener("click", function() {
        const id = regAnnForm && regAnnForm.dataset.editingId;
        if (!id) return;
        const go = function() {
          fetch(`/api/announcements/${id}/`, {
            method: "DELETE",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken },
          }).then(function(r) {
            if (!r.ok && r.status !== 204) throw new Error("HTTP " + r.status);
            bootstrap.Modal.getInstance(document.getElementById("registrarAnnouncementModal")).hide();
            if (typeof Swal !== "undefined") {
              Swal.fire({ icon: "success", title: "Announcement deleted", timer: 1400, showConfirmButton: false });
            }
            if (window.invalidateCalendarCache) window.invalidateCalendarCache();
            if (window.calendar && window.calendar.refetchEvents) window.calendar.refetchEvents();
          }).catch(function(err) {
            alert("Could not delete announcement: " + (err.message || "unknown error"));
          });
        };
        if (typeof Swal !== "undefined") {
          Swal.fire({
            title: "Delete this announcement?",
            text: "This cannot be undone.",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Delete",
            confirmButtonColor: "#b94a48",
          }).then(function(res) { if (res.isConfirmed) go(); });
        } else if (confirm("Delete this announcement?")) {
          go();
        }
      });
    }
  });

// ── Block B: events + permissions ──
  document.addEventListener("DOMContentLoaded", function () {
    const ctx = window.CL_CALENDAR_CONTEXT || {};
    const userRole = ctx.userRole || "";
    // Permission flags from the server. Drives every "can this user
    // create/edit/delete X?" branch below so behavior follows Django
    // auth permissions, not hard-coded role names.
    const canManageEvents        = !!ctx.canManageEvents;
    const canManageAnnouncements = !!ctx.canManageAnnouncements;
    const canManageHolidays      = !!ctx.canManageHolidays;
    const calendarEl = document.getElementById("calendar");

    let cachedEvents = null;

    /* Translate API rows into FullCalendar events.
       Colors come from CSS via classNames (evt-assessment-ongoing,
       evt-holiday, etc.) — we deliberately don't set backgroundColor /
       borderColor / textColor on the event, so the chip rendering stays
       in one place (CSS) instead of split between JS and CSS. */
    function transformEvents(calendarData) {
      const now = new Date();
      return calendarData.map((item) => {
        const classNames = [];
        let assessmentStatus = null;

        if (item.type === "assessment") {
          const start = new Date(item.start);
          const end = item.end ? new Date(item.end) : null;
          if (end && now > end) {
            assessmentStatus = "finished";
          } else if (start > now) {
            assessmentStatus = "upcoming";
          } else if (start <= now && (!end || now <= end)) {
            assessmentStatus = item.answered ? "answered" : "ongoing";
          }
          if (assessmentStatus) classNames.push(`evt-assessment-${assessmentStatus}`);
        } else if (item.type) {
          classNames.push(`evt-${item.type}`);
        }

        let formattedStart = item.start;
        let formattedEnd = item.end || null;
        if (item.type === "event" && item.event_time) {
          formattedStart = `${item.date}T${item.event_time}`;
          formattedEnd   = `${item.date}T${item.event_time}`;
        }

        return {
          id: item.id,
          title: item.title,
          start: formattedStart,
          end: formattedEnd,
          allDay: item.allDay || false,
          display: item.type === "announcement" ? "list-item" : "auto",
          classNames: classNames,
          extendedProps: {
            type: item.type,
            holiday_type: item.holiday_type,
            assessmentStatus: assessmentStatus,
          },
        };
      });
    }

    const isMobile = window.innerWidth < 768;
    const initialView = isMobile ? "listWeek" : "dayGridMonth";

    const calendar = new FullCalendar.Calendar(calendarEl, {
      initialView: initialView,
      headerToolbar: {
        left:   "prev,next today",
        center: "title",
        right:  "dayGridMonth,listWeek",
      },
      buttonText: {
        today:  "Today",
        month:  "Month",
        week:   "Week",
        list:   "List",
      },
      windowResize: function () {
        const width = window.innerWidth;
        if (width < 768 && calendar.view.type === "dayGridMonth") {
          calendar.changeView("listWeek");
        } else if (width >= 768 && calendar.view.type === "listWeek") {
          calendar.changeView("dayGridMonth");
        }
      },
      height: window.innerWidth < 768 ? 600 : "auto",
      expandRows: true,
      selectable: true,
      events: function (fetchInfo, successCallback, failureCallback) {
        if (cachedEvents) { successCallback(cachedEvents); return; }
        fetch("/api/calendar/")
          .then((response) => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
          })
          .then((calendarData) => {
            cachedEvents = transformEvents(calendarData);
            successCallback(cachedEvents);
          })
          .catch((error) => {
            console.error("Error fetching calendar data:", error);
            failureCallback(error);
          });
      },
      dayMaxEvents: 3,
      moreLinkClick: "popover",
      fixedWeekCount: false,
      showNonCurrentDates: true,
      eventOrder: "start,title",
      eventTimeFormat: { hour: "numeric", minute: "2-digit", meridiem: "short" },
      eventContent: function (arg) {
        // List view has its own native row layout — let FullCalendar render it
        // so we get the dot + time column + title columns that the list styles
        // already target. Only customize the grid/cell chip rendering.
        if (arg.view.type.startsWith("list")) return;
        const isMobileView = window.innerWidth < 768;
        const maxLength = isMobileView ? 14 : 24;
        const rawTitle = arg.event.title || "";
        const safeTitle = rawTitle.replace(/[<>&"']/g, (c) => ({
          "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&#39;"
        }[c]));
        const display = rawTitle.length > maxLength ? safeTitle.substring(0, maxLength) + "…" : safeTitle;
        const timeHtml = arg.timeText
          ? `<span class="cal-evt-time">${arg.timeText}</span>`
          : "";
        return {
          html: `<div class="cal-evt"><span class="cal-evt-title" title="${safeTitle}">${display}</span>${timeHtml}</div>`,
        };
      },
      select: function (info) {
        // Permission-driven: prefer holiday management if the user has it,
        // else fall back to event creation. Users with neither permission
        // get no toast — date selection is just a no-op.
        if (canManageHolidays) {
          document.getElementById("eventDate").value = info.startStr;
          new bootstrap.Modal(document.getElementById("addEventModal")).show();
        } else if (canManageEvents) {
          const startEl = document.getElementById("regEventStart");
          if (startEl) startEl.value = info.startStr;
          new bootstrap.Modal(document.getElementById("registrarEventModal")).show();
        }
      },
      eventClick: function (info) {
        const rawId = info.event.id ? info.event.id.toString() : null;
        const eventType = info.event.extendedProps.type;
        if (!rawId) return;

        if (eventType === "assessment") {
          window.location.href = `/studentActivityView/${rawId}/`;
        } else if (eventType === "holiday" && canManageHolidays) {
          new bootstrap.Modal(document.getElementById("addEventModal")).show();
          document.getElementById("holidayId").value   = rawId.replace("holiday-", "");
          document.getElementById("eventTitle").value  = info.event.title;
          document.getElementById("eventDate").value   = info.event.startStr;
          document.getElementById("holidayType").value = info.event.extendedProps.holiday_type || "Regular Holiday";
          document.getElementById("eventColor").value  = info.event.backgroundColor;
        } else if (eventType === "event" && canManageEvents) {
          // Edit an existing registrar event. Fetch the full record so we
          // can repopulate description/time/location which aren't all on
          // the FullCalendar event object.
          fetch(`/api/events/${rawId}/`, { credentials: "same-origin" })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
              if (!data) return;
              const form = document.getElementById("registrarEventForm");
              form.dataset.editingId = rawId;
              document.getElementById("regEventTitle").value       = data.title || "";
              document.getElementById("regEventDescription").value = data.description || "";
              document.getElementById("regEventStart").value       = data.start_date || "";
              document.getElementById("regEventEnd").value         = data.end_date || "";
              document.getElementById("regEventTime").value        = data.time ? data.time.slice(0, 5) : "";
              document.getElementById("regEventLocation").value    = data.location || "";
              document.getElementById("registrarEventModalLabel").textContent = "Edit event";
              const submit = form.querySelector("button[type='submit']");
              if (submit) submit.textContent = "Save changes";
              const del = document.getElementById("regEventDeleteBtn");
              if (del) del.classList.remove("d-none");
              new bootstrap.Modal(document.getElementById("registrarEventModal")).show();
            });
        } else if (eventType === "announcement" && canManageAnnouncements) {
          const annId = rawId.replace("announcement-", "");
          fetch(`/api/announcements/${annId}/`, { credentials: "same-origin" })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
              if (!data) return;
              const form = document.getElementById("registrarAnnouncementForm");
              form.dataset.editingId = annId;
              document.getElementById("regAnnTitle").value       = data.title || "";
              document.getElementById("regAnnDescription").value = data.description || "";
              document.getElementById("regAnnDate").value        = data.date || "";
              document.getElementById("registrarAnnouncementModalLabel").textContent = "Edit announcement";
              const submit = form.querySelector("button[type='submit']");
              if (submit) submit.textContent = "Save changes";
              const del = document.getElementById("regAnnDeleteBtn");
              if (del) del.classList.remove("d-none");
              // Stash the linked event ids so the modal's show.bs.modal
              // handler can pre-check them once the events list loads.
              form.dataset.linkedEventIds = JSON.stringify(
                (data.events || []).map(function (ev) { return ev.id; })
              );
              new bootstrap.Modal(document.getElementById("registrarAnnouncementModal")).show();
            });
        }
      },
      eventDidMount: function (info) {
        if (info.el) {
          const tooltipEl = info.el.querySelector('[data-bs-toggle="tooltip"]');
          if (tooltipEl) new bootstrap.Tooltip(tooltipEl);
        }
      },
    });

    calendar.render();
    // Expose so the registrar create-event / create-announcement handlers
    // (registered in the earlier DOMContentLoaded block) can refetch after
    // a successful POST. Also expose a cache invalidator since `events:`
    // memoizes the first fetch in `cachedEvents`.
    window.calendar = calendar;
    window.invalidateCalendarCache = function () { cachedEvents = null; };
  });

  // Hoist Bootstrap modals to <body> before opening so they're never
  // trapped inside an ancestor stacking context (which would let the
  // .modal-backdrop paint over them).
  document.querySelectorAll('#registrarEventModal, #registrarAnnouncementModal, #addEventModal').forEach(function (el) {
    el.addEventListener('show.bs.modal', function () {
      if (el.parentNode !== document.body) document.body.appendChild(el);
    });
  });
