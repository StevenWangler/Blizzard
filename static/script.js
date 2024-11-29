// Function to format the timestamp
function formatDate(date) {
    return new Date(date).toLocaleString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Configure marked options
marked.setOptions({
    breaks: true,  // Convert line breaks to <br>
    gfm: true,     // Enable GitHub Flavored Markdown
    sanitize: false // Allow HTML in the markdown
});

// Function to safely render markdown
function renderMarkdown(content) {
    try {
        return marked.parse(content);
    } catch (error) {
        console.error('Error parsing markdown:', error);
        return content; // Fallback to plain text if markdown parsing fails
    }
}

// Function to create a message element
function createMessageElement(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.role.toLowerCase()}`;
    
    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = message.name;
    
    const content = document.createElement('div');
    content.className = 'message-content markdown-content';
    content.innerHTML = renderMarkdown(message.content);
    
    messageDiv.appendChild(header);
    messageDiv.appendChild(content);
    return messageDiv;
}

// Function to update the UI with the conversation and decision
function updateUI(data) {
    // Update timestamp
    document.getElementById('updateTime').textContent = formatDate(data.timestamp);
    
    // Update final decision
    const decisionElement = document.getElementById('finalDecision');
    decisionElement.innerHTML = data.decision ? renderMarkdown(data.decision) : '';
    
    // Update conversation
    const conversationElement = document.getElementById('conversation');
    conversationElement.innerHTML = ''; // Clear existing content
    
    data.conversation.forEach(message => {
        const messageElement = createMessageElement(message);
        conversationElement.appendChild(messageElement);
    });
}

// Function to load the data
async function loadData() {
    try {
        const response = await fetch('data.json');
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('conversation').innerHTML = '<p>Error loading conversation data.</p>';
    }
}

// Load data when the page loads
document.addEventListener('DOMContentLoaded', loadData); 