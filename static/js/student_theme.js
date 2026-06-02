(function() {
    var theme = localStorage.getItem('theme');
    if (!theme) {
        var match = document.cookie.match(/(?:^|; )theme=([^;]*)/);
        theme = match ? match[1] : 'dark';
    }
    document.body.setAttribute('data-theme', theme);

    window.toggleStudentTheme = function() {
        var current = document.body.getAttribute('data-theme');
        var next = current === 'dark' ? 'light' : 'dark';
        document.body.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        document.cookie = 'theme=' + next + ';path=/;max-age=31536000;SameSite=Lax';
        var icon = document.getElementById('theme-toggle-icon');
        if (icon) icon.className = next === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        var label = document.getElementById('theme-toggle-label');
        if (label) label.textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
    };
})();
