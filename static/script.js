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
        timeElement.textContent = date.toLocaleString('en-US', {
            timeZone: 'America/New_York',
            year: 'numeric',
            month: 'numeric',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });

        // Check if data is from today
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const dataDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
        
        const staleBanner = document.getElementById('staleBanner');
        const currentBanner = document.getElementById('currentBanner');
        const isCurrentData = dataDate.getTime() === today.getTime();
        
        if (staleBanner && currentBanner) {
            staleBanner.style.display = isCurrentData ? 'none' : 'block';
            currentBanner.style.display = isCurrentData ? 'block' : 'none';
        }
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

// Get the current environment
function getEnvironment() {
    const metaTag = document.querySelector('meta[name="blizzard-env"]');
    return metaTag ? metaTag.content : 'development';
}

// Function to load data
async function loadData() {
    try {
        const env = getEnvironment();
        const dataFile = env === 'production' ? 'data.json' : 'data_local.json';
        console.info(`Loading data from ${dataFile} (${env} environment)`);
        
        const response = await fetch(dataFile);
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

// Initialize data loading when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Load data only for the prediction page
    if (document.getElementById('finalDecision')) {
        loadData();
        // Set up periodic reload
        setInterval(loadData, 300000);
    }
}); 