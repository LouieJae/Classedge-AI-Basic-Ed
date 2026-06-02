/**
 * submit.js — Shared AJAX helper for side activity submissions.
 * Plain JS, no modules. All functions are global.
 */

function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.indexOf('csrftoken=') === 0) {
            return c.substring('csrftoken='.length);
        }
    }
    return '';
}

function submitAttempt(activityId, score, timeTaken, details) {
    var url = '/gamification/side-activity/' + activityId + '/submit/';
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            score: score,
            time_taken: timeTaken,
            details: details
        })
    })
    .then(function(response) {
        if (!response.ok) throw new Error('Submit failed: ' + response.status);
        return response.json();
    })
    .then(function(data) {
        showResult(data);
        return data;
    });
}

function showResult(data) {
    var existing = document.getElementById('side-activity-result-overlay');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'side-activity-result-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.6);';

    var scorePercent = typeof data.score_percent !== 'undefined' ? data.score_percent : (data.score || 0);
    var xpEarned = data.xp_earned || 0;

    var card = document.createElement('div');
    card.style.cssText = 'background:#fff;border-radius:12px;padding:2.5rem;text-align:center;min-width:300px;max-width:420px;box-shadow:0 8px 32px rgba(0,0,0,0.25);';

    card.innerHTML =
        '<h2 style="margin:0 0 0.5rem;font-size:1.75rem;">Activity Complete</h2>' +
        '<p style="font-size:2.5rem;font-weight:700;margin:0.5rem 0;color:#2563eb;">' + scorePercent + '%</p>' +
        '<p style="color:#666;margin:0 0 1.5rem;">XP earned: <strong>' + xpEarned + '</strong></p>' +
        '<button id="side-activity-continue-btn" style="padding:0.65rem 2rem;font-size:1rem;border:none;border-radius:8px;background:#2563eb;color:#fff;cursor:pointer;">Continue</button>';

    overlay.appendChild(card);
    document.body.appendChild(overlay);

    document.getElementById('side-activity-continue-btn').addEventListener('click', function() {
        overlay.remove();
    });
}
