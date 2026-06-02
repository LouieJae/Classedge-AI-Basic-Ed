/**
 * drag.js — HTML5 drag-and-drop helpers for sort and match activities.
 * Plain JS, no modules. All functions are global.
 */

function initDragSort(container) {
    var dragSrcEl = null;

    var items = container.querySelectorAll('[data-drag-item]');
    items.forEach(function(item) {
        item.setAttribute('draggable', 'true');

        item.addEventListener('dragstart', function(e) {
            dragSrcEl = this;
            this.style.opacity = '0.4';
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', '');
        });

        item.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            this.style.borderTop = '2px solid #2563eb';
        });

        item.addEventListener('dragleave', function() {
            this.style.borderTop = '';
        });

        item.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.borderTop = '';
            if (dragSrcEl !== this) {
                var parent = this.parentNode;
                var allItems = Array.prototype.slice.call(parent.children);
                var srcIdx = allItems.indexOf(dragSrcEl);
                var tgtIdx = allItems.indexOf(this);
                if (srcIdx < tgtIdx) {
                    parent.insertBefore(dragSrcEl, this.nextSibling);
                } else {
                    parent.insertBefore(dragSrcEl, this);
                }
            }
        });

        item.addEventListener('dragend', function() {
            this.style.opacity = '';
            container.querySelectorAll('[data-drag-item]').forEach(function(el) {
                el.style.borderTop = '';
            });
        });
    });

    return {
        getOrder: function() {
            var currentItems = container.querySelectorAll('[data-drag-item]');
            var order = [];
            currentItems.forEach(function(el) {
                order.push(parseInt(el.getAttribute('data-original-index'), 10));
            });
            return order;
        }
    };
}

function initDragMatch(leftContainer, rightContainer) {
    var matches = {};
    var draggedItem = null;

    var leftItems = leftContainer.querySelectorAll('[data-match-left]');
    var rightTargets = rightContainer.querySelectorAll('[data-match-right]');

    leftItems.forEach(function(item) {
        item.setAttribute('draggable', 'true');

        item.addEventListener('dragstart', function(e) {
            draggedItem = this;
            this.style.opacity = '0.4';
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', this.getAttribute('data-match-left'));
        });

        item.addEventListener('dragend', function() {
            this.style.opacity = '';
            rightTargets.forEach(function(t) {
                t.style.outline = '';
            });
        });
    });

    rightTargets.forEach(function(target) {
        target.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            this.style.outline = '2px solid #2563eb';
        });

        target.addEventListener('dragleave', function() {
            this.style.outline = '';
        });

        target.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.outline = '';
            if (!draggedItem) return;
            var leftKey = draggedItem.getAttribute('data-match-left');
            var rightKey = this.getAttribute('data-match-right');
            matches[leftKey] = rightKey;
            draggedItem.style.opacity = '0.6';
            draggedItem.setAttribute('draggable', 'false');
            this.style.background = '#e0f2fe';
            draggedItem = null;
        });
    });

    return {
        getMatches: function() {
            return Object.assign({}, matches);
        }
    };
}
