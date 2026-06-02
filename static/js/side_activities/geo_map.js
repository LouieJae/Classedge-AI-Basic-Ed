/**
 * geo_map.js — Geography / image-click map activity.
 * Plain JS, no modules. All functions are global.
 */

function initGeoMap(container, targets, onComplete) {
    var currentIndex = 0;
    var correctClicks = 0;
    var totalTargets = targets.length;

    var image = container.querySelector('.geo-image');
    var promptEl = container.querySelector('.geo-prompt') || null;

    function showPrompt() {
        if (currentIndex >= totalTargets) {
            if (typeof onComplete === 'function') onComplete(correctClicks);
            return;
        }
        if (promptEl) {
            promptEl.textContent = 'Click on: ' + targets[currentIndex].label;
        }
    }

    image.addEventListener('click', function(e) {
        if (currentIndex >= totalTargets) return;

        var rect = image.getBoundingClientRect();
        var clickX = ((e.clientX - rect.left) / rect.width) * 100;
        var clickY = ((e.clientY - rect.top) / rect.height) * 100;

        var target = targets[currentIndex];
        var dx = clickX - target.x;
        var dy = clickY - target.y;
        var distance = Math.sqrt(dx * dx + dy * dy);

        var tolerance = target.tolerance || 5;

        // Visual feedback
        var marker = document.createElement('div');
        marker.style.cssText = 'position:absolute;width:12px;height:12px;border-radius:50%;transform:translate(-50%,-50%);pointer-events:none;';
        marker.style.left = clickX + '%';
        marker.style.top = clickY + '%';

        if (distance <= tolerance) {
            correctClicks++;
            marker.style.background = '#22c55e';
        } else {
            marker.style.background = '#ef4444';
        }

        // Ensure container is positioned for absolute marker
        if (getComputedStyle(container).position === 'static') {
            container.style.position = 'relative';
        }
        container.appendChild(marker);

        currentIndex++;
        showPrompt();
    });

    showPrompt();
}
