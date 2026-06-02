document.addEventListener("DOMContentLoaded", function () {
  fetchEvents();

  // wire up modal open/close safely
  const addBtn = document.getElementById("openAddModalBtn");
  if (addBtn) addBtn.addEventListener("click", openAddModal);
  const closeAddBtn = document.getElementById("closeAddModalBtn");
  if (closeAddBtn) closeAddBtn.addEventListener("click", closeAddModal);
  const closeUpdateBtn = document.getElementById("close_update_modal");
  if (closeUpdateBtn) closeUpdateBtn.addEventListener("click", closeEditModal);

  // forms
  const addForm = document.getElementById("addEventForm");
  if (addForm) addForm.addEventListener("submit", handleAddSubmit);

  const updateForm = document.getElementById("updateEventForm");
  if (updateForm) updateForm.addEventListener("submit", handleUpdateSubmit);

  // bootstrap-select init if present
  if (window.jQuery) {
    $(document).ready(function() {
      if ($('.selectpicker').length) {
        $('.selectpicker').selectpicker('refresh');
      }
    });
  }
});

function fetchEvents() {
  fetch("/api/events/") // ✅ use API route
    .then(response => response.json())
    .then(data => {
      const tableBody = document.querySelector("#dataTable tbody");
      if (!tableBody) return;

      tableBody.innerHTML = "";

      // Handle paginated response - data.results contains the actual array
      const events = data.results || data;
      
      if (!Array.isArray(events) || events.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No events found</td></tr>';
        return;
      }

      events.forEach((event, index) => {
        // Backend now has start_date/end_date/time
        const shownDate = formatDate(event.start_date) || "N/A";
        const shownTime = formatTime(event.time);
        const desc = event.description || "No Description";
        const loc = event.location || "N/A";

        // If your serializer returns a numeric id, this is fine; if it returns a string, keep as-is
        const idAttr = typeof event.id === "number" ? event.id : `'${String(event.id).replace(/'/g, "\\'")}'`;

        const row = `<tr>
            <td>${index + 1}</td>
            <td>${event.title || "Untitled"}</td>
            <td>${escapeHtml(desc)}</td>
            <td>${shownDate}</td>
            <td>${shownTime}</td>
            <td>${escapeHtml(loc)}</td>
            <td class="text-center">
              <a href="javascript:void(0);" class="text-warning mx-1" onclick="openEditModal(${idAttr})" title="Edit Event">
                <i class="fas fa-edit"></i>
              </a>
              <a href="javascript:void(0);" class="text-danger mx-1" onclick="confirmDelete(${idAttr})" title="Delete Event">
                <i class="fas fa-trash-alt"></i>
              </a>
            </td>
          </tr>`;
        tableBody.insertAdjacentHTML('beforeend', row);
      });
    })
    .catch(error => console.error("Error fetching events:", error));
}

function openAddModal() {
  const addModal = document.getElementById("addModal");
  const addBackdrop = document.getElementById("addModalBackdrop");
  if (addModal) addModal.classList.add("show");
  if (addBackdrop) addBackdrop.classList.add("show");
}

function closeAddModal() {
  const addModal = document.getElementById("addModal");
  const addBackdrop = document.getElementById("addModalBackdrop");
  if (addModal) addModal.classList.remove("show");
  if (addBackdrop) addBackdrop.classList.remove("show");
}

function openEditModal(id) {
  fetch(`/api/events/${id}/`) // ✅ use API route
    .then(response => response.json())
    .then(data => {
      // Fill fields (note: backend uses start_date)
      setValue("eventId", data.id);
      setValue("eventTitle", data.title || "");
      setValue("eventDescription", data.description || "");
      setValue("eventDate", data.start_date || "");   // ✅ start_date
      setValue("eventTime", data.time || "");         // "HH:MM:SS" or null
      setValue("eventLocation", data.location || "");

      const editModal = document.getElementById("editModal");
      const editBackdrop = document.getElementById("editModalBackdrop");
      if (editModal) editModal.classList.add("show");
      if (editBackdrop) editBackdrop.classList.add("show");
    })
    .catch(error => console.error("Error fetching event details:", error));
}

function closeEditModal() {
  const editModal = document.getElementById("editModal");
  const editBackdrop = document.getElementById("editModalBackdrop");
  if (editModal) editModal.classList.remove("show");
  if (editBackdrop) editBackdrop.classList.remove("show");
}

// Handle Add Event
function handleAddSubmit(e) {
  e.preventDefault();

  const title = getValue("newEventTitle");
  const description = getValue("newEventDescription");
  const start_date = getValue("newEventDate");  // ✅ send start_date
  const time = normalizeTime(getValue("newEventTime")); // "HH:MM" -> "HH:MM:00"
  const location = getValue("newEventLocation");

  fetch("/api/events/", { // ✅ use API route
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify({
      title,
      description,
      start_date,     // ✅ correct field
      end_date: start_date,  // ✅ default to same day for single-day events
      time: time || null,
      location: location || null,
    }),
  })
  .then(r => r.json().then(body => ({ status: r.status, body })))
  .then(({ status, body }) => {
    if (status >= 200 && status < 300) {
      displayToast?.("Event created successfully.", "success");
      closeAddModal();
      fetchEvents();
    } else {
      throw new Error(body?.detail || "Failed to create event.");
    }
  })
  .catch(err => {
    displayToast?.("Error creating event. Please try again.", "error");
  });
}

// Handle Update Event
function handleUpdateSubmit(e) {
  e.preventDefault();

  const id = getValue("eventId");
  const title = getValue("eventTitle");
  const description = getValue("eventDescription");
  const start_date = getValue("eventDate"); // ✅ send start_date
  const time = normalizeTime(getValue("eventTime"));
  const location = getValue("eventLocation");

  fetch(`/api/events/${id}/`, { // ✅ use API route
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify({
      title,
      description,
      start_date,         // ✅ correct field
      end_date: start_date,  // ✅ default to same day for single-day events
      time: time || null, // string or null
      location: location || null,
    }),
  })
  .then(r => r.json().then(body => ({ status: r.status, body })))
  .then(({ status, body }) => {
    if (status >= 200 && status < 300) {
      displayToast?.("Event updated successfully.", "success");
      closeEditModal();
      fetchEvents();
    } else {
      throw new Error(body?.detail || "Failed to update event.");
    }
  })
  .catch(err => {
    displayToast?.("Error updating event. Please try again.", "error");
  });
}

// Delete
function confirmDelete(id) {
  Swal.fire({
    title: 'Are you sure?',
    text: "You won't be able to revert this!",
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#3085d6',
    cancelButtonColor: '#d33',
    confirmButtonText: 'Yes, delete it!'
  }).then((result) => {
    if (!result.isConfirmed) return;

    fetch(`/api/events/${id}/`, { // ✅ use API route
      method: 'DELETE',
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      }
    })
    .then((response) => {
      if (response.ok) {
        Swal.fire({ title: 'Deleted!', text: 'The event has been deleted.', icon: 'success' })
          .then(() => fetchEvents()); // ✅ refresh instead of full reload
      } else {
        Swal.fire({ title: 'Error!', text: 'There was an issue deleting the event.', icon: 'error' });
      }
    })
    .catch(err => {
      Swal.fire({ title: 'Error!', text: 'Network error deleting the event.', icon: 'error' });
    });
  });
}

/* -------- helpers -------- */

function getValue(id) {
  const el = document.getElementById(id);
  return el ? el.value : "";
}

function setValue(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val ?? "";
}

function formatDate(dateString) {
  if (!dateString) return null;
  // If your API returns "YYYY-MM-DD", you can show as-is or prettify:
  // return new Date(dateString).toLocaleDateString(); // if you want localized
  return dateString;
}

function formatTime(timeString) {
  if (!timeString) return "N/A";
  // Accept "HH:MM:SS" or "HH:MM"
  const parts = timeString.split(":").map(Number);
  let hours = parts[0], minutes = parts[1] ?? 0;
  const period = hours >= 12 ? "PM" : "AM";
  hours = hours % 12 || 12;
  return `${hours}:${String(minutes).padStart(2, "0")} ${period}`;
}

function normalizeTime(timeString) {
  if (!timeString) return null;
  // Ensure backend gets "HH:MM:SS"
  if (/^\d{2}:\d{2}$/.test(timeString)) return `${timeString}:00`;
  return timeString; // assume already HH:MM:SS
}

function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getCSRFToken() {
  let cookieValue = null;
  if (document.cookie) {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith("csrftoken=")) {
        cookieValue = cookie.substring("csrftoken=".length);
        break;
      }
    }
  }
  return cookieValue;
}
