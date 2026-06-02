/**
 * typing.js — Typing drill activity.
 * Plain JS, no modules. All functions are global.
 */

function initTypingDrill(container, text, onComplete) {
    var targetEl = container.querySelector('.typing-target');
    var inputEl = container.querySelector('.typing-input');
    var wpmEl = container.querySelector('.typing-wpm');
    var accuracyEl = container.querySelector('.typing-accuracy');

    if (targetEl) targetEl.textContent = text;

    var startTime = null;
    var targetLen = text.length;
    var totalKeystrokes = 0;
    var correctChars = 0;
    var done = false;

    inputEl.addEventListener('input', function() {
        if (done) return;

        if (!startTime) startTime = Date.now();

        totalKeystrokes++;
        var typed = inputEl.value;

        // Calculate current accuracy
        correctChars = 0;
        for (var i = 0; i < typed.length; i++) {
            if (i < targetLen && typed[i] === text[i]) {
                correctChars++;
            }
        }

        var accuracy = totalKeystrokes > 0 ? Math.round((correctChars / typed.length) * 100) : 100;
        var elapsedMin = (Date.now() - startTime) / 60000;
        var wordCount = typed.length / 5;
        var wpm = elapsedMin > 0 ? Math.round(wordCount / elapsedMin) : 0;

        if (wpmEl) wpmEl.textContent = wpm + ' WPM';
        if (accuracyEl) accuracyEl.textContent = accuracy + '%';

        if (typed.length >= targetLen) {
            done = true;
            var elapsedSeconds = Math.round((Date.now() - startTime) / 1000);
            if (typeof onComplete === 'function') onComplete(accuracy, wpm, elapsedSeconds);
        }
    });
}
