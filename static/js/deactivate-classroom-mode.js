document.addEventListener("DOMContentLoaded", () => {
    const exitButton = document.querySelector('.btn-light');

    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (!csrfTokenMeta) {
        console.error("CSRF token meta tag not found!");
        return; // Exit the function early
    }

    const csrfToken = csrfTokenMeta.getAttribute('content');

    if (exitButton) { // Check if the button exists
        exitButton.addEventListener('click', function (event) {
            // Prevent default action to stop immediate navigation
            event.preventDefault();

            const redirectUrl = exitButton.getAttribute('href'); // Capture the redirect URL

            fetch('/toggle_mode/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
                
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (!data.is_classroom_mode) {
                    window.location.href = redirectUrl;
                }
            })
            .catch(error => {
                console.error('Error deactivating classroom mode:', error);
            });
        });
    }
});
