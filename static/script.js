// Configure marked options
marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false
});

// Function to safely render markdown
function renderMarkdown(content) {
    if (!content) return '';
    try {
        // Special handling for prediction format
        if (content.includes('SNOW DAY VERDICT:')) {
            // Remove backticks and trim
            content = content.replace(/```/g, '').trim();
            
            // Split content into sections
            const sections = content.split('\n\n').map(section => {
                // Replace single newlines with <br> for proper line breaks
                const formattedSection = section.replace(/\n/g, '<br>');
                return `<div class="prediction-section">${formattedSection}</div>`;
            });
            
            return `<div class="prediction">${sections.join('')}</div>`;
        }
        return marked.parse(content);
    } catch (error) {
        console.error('Error parsing markdown:', error);
        return content;
    }
}

// Function to update the UI
function updateUI(data) {
    // Update timestamp
    const timeElement = document.getElementById('updateTime');
    if (timeElement && data.timestamp) {
        const date = new Date(data.timestamp);
        timeElement.textContent = date.toLocaleString();
    }
    
    // Update final decision
    const decisionElement = document.getElementById('finalDecision');
    if (decisionElement && data.decision) {
        decisionElement.innerHTML = renderMarkdown(data.decision);
    }
    
    // Update conversation
    const conversationElement = document.getElementById('conversation');
    if (conversationElement && Array.isArray(data.conversation)) {
        const conversationHtml = data.conversation.map(message => `
            <div class="message">
                <div class="message-header">${message.name || ''}</div>
                <div class="message-content">${renderMarkdown(message.content || '')}</div>
            </div>
        `).join('');
        conversationElement.innerHTML = conversationHtml;
    }
}

// Function to load data
async function loadData() {
    try {
        const response = await fetch('data.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error loading data:', error);
        const conversationElement = document.getElementById('conversation');
        if (conversationElement) {
            conversationElement.innerHTML = '<p class="error-message">Error loading data. Please refresh the page.</p>';
        }
    }
}

// Function to initialize theme
function initializeTheme() {
    const themeToggle = document.querySelector('.theme-toggle');
    const themeIcon = document.getElementById('themeIcon');
    const htmlElement = document.documentElement;

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

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme(); // Initialize theme toggle for all pages
    loadData();       // Load data only for pages that need it
});

// Reload data periodically (only affects pages that use it)
setInterval(loadData, 300000); 