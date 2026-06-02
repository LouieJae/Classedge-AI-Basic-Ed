let screenshotInterval;
let screenshotTimeout;
let hasPromptedTeacher = false;
let timerInterval;
let classStartTime = null;

async function captureScreenshot(subjectId, attendanceId) {
  if (typeof html2canvas === "undefined") {
    return;
  }

  const canvas = await html2canvas(document.body);
  const imgData = canvas.toDataURL("image/png");

  fetch(`/save-screenshot/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify({
      image: imgData,
      subject_id: subjectId,
      attendance_id: attendanceId
    })
  })
    .then(response => response.json())
    .then(data => {
      localStorage.setItem("screenshotSession", JSON.stringify({
        subjectId,
        attendanceId,
        lastCaptureTime: Date.now()
      }));
    })
    .catch(error => console.error("Screenshot Error:", error));
}

function checkClassEndTime(subjectId) {
  fetch(`/teacher_attendance/${subjectId}/get-end-time/`)
    .then(response => {
      if (!response.ok) throw new Error("API response not OK");
      return response.json();
    })
    .then(data => {
      if (!data || data.error) return;
      if (typeof data.end_time !== "string" || !data.end_time.includes(":")) return;

      const [h, m, s] = data.end_time.split(":").map(Number);
      if ([h, m, s].some(n => Number.isNaN(n))) return;
      const now = new Date();
      const scheduledEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, s);

      const warningThresholds = [5 * 60 * 1000, 1 * 60 * 1000];

      // Calculate time until end
      const timeUntilEnd = Math.max(0, scheduledEnd - now);

      // Set warnings for 5 min and 1 min before end
      warningThresholds.forEach(threshold => {
        const warningTime = timeUntilEnd - threshold;
        if (warningTime > 0) {
          setTimeout(() => {
            const minutesLeft = threshold / (60 * 1000);
            Swal.fire({
              title: `Class Ending Soon`,
              text: `Your scheduled class time will end in ${minutesLeft} minute${minutesLeft > 1 ? 's' : ''}.`,
              icon: "warning",
              timer: 10000,
              timerProgressBar: true,
              showConfirmButton: false
            });
          }, warningTime);
        }
      });

      // Show notification when class end time is reached
      // Note: Celery will automatically end the class server-side
      if (timeUntilEnd > 0) {
        setTimeout(() => {
          Swal.fire({
            title: "Class Time Ended",
            text: "Your scheduled class time has ended. Reloading page...",
            icon: "info",
            timer: 5000,
            timerProgressBar: true,
            showConfirmButton: false,
            allowOutsideClick: false
          }).then(() => {
            location.reload();
          });
        }, timeUntilEnd);
      } else if (now >= scheduledEnd) {
        // Class should have already ended
        Swal.fire({
          title: "Class Time Ended",
          text: "Your scheduled class time has ended. Reloading page...",
          icon: "info",
          timer: 5000,
          timerProgressBar: true,
          showConfirmButton: false,
          allowOutsideClick: false
        }).then(() => {
          location.reload();
        });
      }
    })
    .catch(error => console.error("❌ Error fetching end time:", error));
}

function endClass(subjectId, shouldReload = false) {
  fetch(`/teacher_attendance/${subjectId}/end-class/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    }
  })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        Swal.fire("Error", data.error, "error");
      } else {
        Swal.fire({
          title: "Class Ended",
          text: "Your class has been successfully ended.",
          icon: "success",
          confirmButtonText: "OK"
        }).then(() => {
          if (shouldReload) location.reload();
        });
      }
    })
    .catch(error => console.error("❌ Error ending class:", error));
}

function startScreenshotLoop(subjectId, attendanceId) {
  if (!attendanceId) {
    return;
  }

  if (screenshotInterval) {
    clearInterval(screenshotInterval);
    screenshotInterval = null;
  }
  if (screenshotTimeout) {
    clearTimeout(screenshotTimeout);
    screenshotTimeout = null;
  }
  const intervalDuration = 600000;

  fetch(`/teacher_attendance/${subjectId}/current-state/`)
    .then(response => response.json())
    .then(data => {
      const isA = (data.is_active !== undefined) ? data.is_active : data.isActive;
      const ts  = data.time_started || data.timeStarted;
      if (!isA) {
        stopScreenshotLoop();
        stopTimer();
        return;
      }

      if (ts) {
        startTimer(ts, subjectId);
      }

      const stored = JSON.parse(localStorage.getItem("screenshotSession") || '{}');
      let lastCaptureTime = stored.lastCaptureTime ? Number(stored.lastCaptureTime) : null;
      const now = Date.now();
      let timeUntilNext = intervalDuration;
      let shouldCaptureImmediately = true;

      if (lastCaptureTime) {
        const elapsed = now - lastCaptureTime;
        if (elapsed >= intervalDuration) {
          timeUntilNext = intervalDuration;
        } else {
          shouldCaptureImmediately = false;
          timeUntilNext = intervalDuration - elapsed;
        }
      }

      if (shouldCaptureImmediately) {
        captureScreenshot(subjectId, attendanceId);
        lastCaptureTime = Date.now();
      }

      localStorage.setItem("screenshotSession", JSON.stringify({
        subjectId,
        attendanceId,
        lastCaptureTime
      }));

      const scheduleScreenshot = () => {
        captureScreenshot(subjectId, attendanceId);
        const newTime = Date.now();
        localStorage.setItem("screenshotSession", JSON.stringify({
          subjectId,
          attendanceId,
          lastCaptureTime: newTime
        }));
      };

      screenshotTimeout = setTimeout(() => {
        screenshotTimeout = null;
        scheduleScreenshot();
        screenshotInterval = setInterval(scheduleScreenshot, intervalDuration);
      }, timeUntilNext);

      checkClassEndTime(subjectId);
    })
    .catch(error => console.error("❌ Error checking class state:", error));
}

function stopScreenshotLoop() {
  if (screenshotInterval) {
    clearInterval(screenshotInterval);
    screenshotInterval = null;
  }
  if (screenshotTimeout) {
    clearTimeout(screenshotTimeout);
    screenshotTimeout = null;
  }
  localStorage.removeItem("screenshotSession");
}

function formatTime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function updateTimer() {
  if (!classStartTime) return;
  
  const timerDisplay = document.getElementById('classroomTimerDisplay');
  const timerText = document.getElementById('classroomTimerText');
  
  if (!timerDisplay || !timerText) return;
  
  const now = new Date();
  const elapsed = Math.floor((now - classStartTime) / 1000);
  timerText.textContent = formatTime(elapsed);
}

// localStorage key for class-session start time, scoped by subject so each
// subject keeps its own elapsed timer across refreshes.
const CLASS_TIMER_LS_KEY = "classSessionTimer";

function persistTimerSession(subjectId, timeStartedISO) {
  try {
    localStorage.setItem(
      CLASS_TIMER_LS_KEY,
      JSON.stringify({ subjectId: String(subjectId), timeStarted: timeStartedISO })
    );
  } catch (e) { /* localStorage may be unavailable in some contexts */ }
}

function clearTimerSession() {
  try { localStorage.removeItem(CLASS_TIMER_LS_KEY); } catch (e) {}
}

function readTimerSession() {
  try {
    const raw = localStorage.getItem(CLASS_TIMER_LS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}

function startTimer(timeStartedISO, subjectId) {
  classStartTime = new Date(timeStartedISO);

  const timerDisplay = document.getElementById('classroomTimerDisplay');
  const classActionButton = document.getElementById('classActionButton');
  const currentSubjectId = classActionButton ? classActionButton.getAttribute('data-subject-id') : null;

  // Only show the timer on the page for the subject whose class is active.
  if (timerDisplay) {
    if (!currentSubjectId || String(currentSubjectId) === String(subjectId)) {
      timerDisplay.classList.add('is-on');
    } else {
      timerDisplay.classList.remove('is-on');
      return;
    }
  }

  // Cache so the next page refresh can show the timer immediately, before
  // the server `current-state` round-trip resolves.
  persistTimerSession(subjectId, timeStartedISO);

  if (timerInterval) {
    clearInterval(timerInterval);
  }

  updateTimer();
  timerInterval = setInterval(updateTimer, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  classStartTime = null;

  const timerDisplay = document.getElementById('classroomTimerDisplay');
  if (timerDisplay) {
    timerDisplay.classList.remove('is-on');
  }

  clearTimerSession();
}

// Hydrate timer from localStorage immediately on page load so the elapsed
// time is visible without waiting for the server fetch. The server's
// current-state response remains authoritative — if it disagrees, the
// timer is corrected or hidden a moment later.
document.addEventListener("DOMContentLoaded", function () {
  const classActionButton = document.getElementById('classActionButton');
  const timerDisplay = document.getElementById('classroomTimerDisplay');
  if (!classActionButton || !timerDisplay) return;

  const subjectId = classActionButton.getAttribute('data-subject-id');
  const cached = readTimerSession();
  if (cached && String(cached.subjectId) === String(subjectId) && cached.timeStarted) {
    classStartTime = new Date(cached.timeStarted);
    timerDisplay.classList.add('is-on');
    updateTimer();
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(updateTimer, 1000);
  } else if (cached && String(cached.subjectId) !== String(subjectId)) {
    // Stale entry belongs to a different subject — leave it alone; the
    // other subject's page is the one that should clear it.
  }
});

// Restore screenshot session on load
document.addEventListener("DOMContentLoaded", function () {
  if (typeof html2canvas === "undefined") {
    return;
  }

  const storedSession = localStorage.getItem("screenshotSession");
  if (storedSession) {
    const { subjectId, attendanceId } = JSON.parse(storedSession);

    fetch(`/teacher_attendance/${subjectId}/current-state/`)
      .then(res => res.json())
      .then(data => {
        const isA = (data.is_active !== undefined) ? data.is_active : data.isActive;
        if (isA) {
          startScreenshotLoop(subjectId, attendanceId);
        } else {
          stopScreenshotLoop();
        }
      })
      .catch(error => console.error("❌ Error restoring session:", error));
  }
});

// Resume screenshot session on tab focus
window.addEventListener("focus", () => {
  const storedSession = localStorage.getItem("screenshotSession");
  if (storedSession) {
    const { subjectId, attendanceId } = JSON.parse(storedSession);

    fetch(`/teacher_attendance/${subjectId}/current-state/`)
      .then(res => res.json())
      .then(data => {
        const isA = (data.is_active !== undefined) ? data.is_active : data.isActive;
        if (isA) {
          startScreenshotLoop(subjectId, attendanceId);
        } else {
          stopScreenshotLoop();
        }
      })
      .catch(error => console.error("❌ Error on focus:", error));
  }
});

// Start/end class button logic
document.addEventListener("DOMContentLoaded", function () {
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  const classActionButton = document.getElementById('classActionButton');

  if (!classActionButton) {
    console.warn("⚠️ No classActionButton found on this page.");
    return;
  }

  const subjectId = classActionButton.getAttribute('data-subject-id');
  const currentStateUrl = `/teacher_attendance/${subjectId}/current-state/`;

  // Fetch initial class state
  fetch(currentStateUrl, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  })
    .then(response => response.ok ? response.json() : Promise.reject("Failed to fetch state."))
    .then(data => {
      // DRF's CamelCaseJSONRenderer converts snake_case keys, so accept both.
      const isActiveRaw   = (data.is_active   !== undefined) ? data.is_active   : data.isActive;
      const timeStarted   = data.time_started || data.timeStarted;
      const attendanceId  = data.attendance_id || data.attendanceId;
      const isActive = isActiveRaw === true;
      classActionButton.setAttribute('data-is-active', isActive);
      classActionButton.innerHTML = isActive
        ? '<i class="fas fa-chalkboard-teacher"></i> End Class'
        : '<i class="fas fa-chalkboard-teacher"></i> Start Class';
      if (isActive && timeStarted) {
        // Server is authoritative — re-sync the timer (and localStorage) to
        // the server's start time in case the cached value was stale.
        startTimer(timeStarted, subjectId);
        startScreenshotLoop(subjectId, attendanceId);
      } else if (isActiveRaw === false) {
        // Server explicitly says no active class — clear any cached timer
        // so the UI matches reality (covers ending the class in another tab).
        stopTimer();
      }
      // Any other shape (missing is_active, network/JSON malformed) → keep
      // whatever the localStorage hydration started; better a slightly-stale
      // timer than a wrongly-reset one.
    })
    .catch(error => {
      // Network/parse failure — leave the cached timer running.
      console.error("Error fetching current state:", error);
    });

  // Re-sync when the tab regains focus, so a stale display catches up to
  // any state change that happened while the tab was hidden.
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState !== 'visible') return;
    fetch(currentStateUrl, { method: 'GET', headers: { 'Content-Type': 'application/json' } })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (!d) return;
        const isA = (d.is_active !== undefined) ? d.is_active : d.isActive;
        const ts  = d.time_started || d.timeStarted;
        if (isA === true && ts) {
          startTimer(ts, subjectId);
        } else if (isA === false) {
          stopTimer();
        }
      })
      .catch(function () { /* keep cached state on failure */ });
  });

  // Button click behavior
  classActionButton.addEventListener('click', function () {
    // Prevent multiple clicks by checking if button is already disabled
    if (classActionButton.disabled) {
      return;
    }
    
    const isActive = this.getAttribute('data-is-active') === 'true';
    const url = isActive
      ? `/teacher_attendance/${subjectId}/end-class/`
      : `/teacher_attendance/${subjectId}/start-class/`;

    // Disable button and show loading state
    classActionButton.disabled = true;
    const originalHTML = classActionButton.innerHTML;
    classActionButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      }
    })
      .then(response => response.ok ? response.json() : response.json().then(err => { throw new Error(err.error || 'Unknown error'); }))
      .then(data => {        
        Swal.fire({
          icon: 'success',
          title: isActive ? 'Class ended successfully!' : 'Class started successfully!',
          confirmButtonText: 'OK',
          allowOutsideClick: false,
          allowEscapeKey: false
        }).then(() => {
          if (isActive) {
            stopScreenshotLoop();
            stopTimer();
            location.reload();
          } else {
            classActionButton.setAttribute('data-is-active', 'true');
            classActionButton.innerHTML = '<i class="fas fa-chalkboard-teacher"></i> End Class';
            if (data.time_started) {
              startTimer(data.time_started, subjectId);
            } else {
              console.warn('[CLASS ACTION] No time_started in response!');
            }
            startScreenshotLoop(subjectId, data.attendance_id);
          }
          // Re-enable button after successful operation
          classActionButton.disabled = false;
        });
      })
      .catch(error => {
        console.error("Action error:", error);
        // Re-enable button and restore original text
        classActionButton.disabled = false;
        classActionButton.innerHTML = originalHTML;
        
        Swal.fire({
          icon: 'error',
          title: 'Oops...',
          text: error.message,
          confirmButtonText: 'OK',
          allowOutsideClick: false,
          allowEscapeKey: false
        });
      });
  });
});
