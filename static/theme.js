// Function to initialize theme
function initializeTheme() {
    const themeToggle = document.querySelector('.theme-toggle');
    const themeIcon = document.getElementById('themeIcon');
    const htmlElement = document.documentElement;

    if (!themeToggle || !themeIcon) {
        console.error('Theme toggle elements not found');
        return;
    }

    // Check saved theme preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        htmlElement.setAttribute('data-theme', savedTheme);
        themeIcon.textContent = savedTheme === 'dark' ? '🌙' : '☀️';
    } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        htmlElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        themeIcon.textContent = prefersDark ? '🌙' : '☀️';
    }

    // Theme toggle handler
    themeToggle.addEventListener('click', () => {
        const currentTheme = htmlElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        htmlElement.setAttribute('data-theme', newTheme);
        themeIcon.textContent = newTheme === 'dark' ? '🌙' : '☀️';
        localStorage.setItem('theme', newTheme);
    });
}

// Initialize theme when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeTheme); 