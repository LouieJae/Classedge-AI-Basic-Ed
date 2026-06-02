/**
 * flashcard.js — Flashcard drill for side activities.
 * Plain JS, no modules. All functions are global.
 */

function initFlashcards(container, cards, onComplete) {
    var currentIndex = 0;
    var knewCount = 0;
    var totalCards = cards.length;

    var cardEl = container.querySelector('.flashcard-card');
    var frontEl = container.querySelector('.flashcard-front');
    var backEl = container.querySelector('.flashcard-back');
    var knewBtn = container.querySelector('.flashcard-knew');
    var didntBtn = container.querySelector('.flashcard-didnt');
    var counterEl = container.querySelector('.flashcard-counter');

    if (totalCards === 0) {
        counterEl.textContent = '0 / 0';
        frontEl.style.display = '';
        frontEl.textContent = 'This activity has no flashcards yet.';
        return;
    }

    function showCard(index) {
        if (index >= totalCards) {
            if (typeof onComplete === 'function') onComplete(knewCount);
            return;
        }
        var card = cards[index];
        frontEl.textContent = card.front;
        backEl.textContent = card.back;
        backEl.style.display = 'none';
        frontEl.style.display = '';
        knewBtn.style.display = 'none';
        didntBtn.style.display = 'none';
        counterEl.textContent = (index + 1) + ' / ' + totalCards;
    }

    cardEl.addEventListener('click', function() {
        if (backEl.style.display === 'none') {
            backEl.style.display = '';
            frontEl.style.display = 'none';
            knewBtn.style.display = '';
            didntBtn.style.display = '';
        }
    });

    knewBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        knewCount++;
        currentIndex++;
        showCard(currentIndex);
    });

    didntBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        currentIndex++;
        showCard(currentIndex);
    });

    showCard(0);
}
