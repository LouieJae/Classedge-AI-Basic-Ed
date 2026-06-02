/**
 * timer.js — Countdown timer for timed side activities.
 * Plain JS, no modules. All functions are global.
 */

function startTimer(seconds, timerEl, onExpire) {
    var remaining = seconds;
    var startTime = Date.now();
    var stopped = false;

    function formatTime(s) {
        var m = Math.floor(s / 60);
        var sec = s % 60;
        return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
    }

    timerEl.textContent = formatTime(remaining);

    var interval = setInterval(function() {
        if (stopped) return;
        var elapsed = Math.floor((Date.now() - startTime) / 1000);
        remaining = Math.max(0, seconds - elapsed);
        timerEl.textContent = formatTime(remaining);
        if (remaining <= 0) {
            clearInterval(interval);
            if (typeof onExpire === 'function') onExpire();
        }
    }, 250);

    return {
        stop: function() {
            stopped = true;
            clearInterval(interval);
            return Math.floor((Date.now() - startTime) / 1000);
        }
    };
}
