// Get the current environment
function getEnvironment() {
    const metaTag = document.querySelector('meta[name="blizzard-env"]');
    return metaTag ? metaTag.content : 'development';
}

// Function to calculate prediction statistics
function calculateStats(data) {
    if (!data || !Array.isArray(data.predictions)) {
        return {
            total: 0,
            completed: 0,
            correct: 0,
            accuracy: 0
        };
    }

    const stats = {
        total: data.predictions.length,
        completed: 0,
        correct: 0,
        accuracy: 0
    };

    data.predictions.forEach(prediction => {
        // Skip predictions without actual outcomes
        if (prediction.actual === null) return;

        stats.completed++;
        
        // Extract verdict from prediction
        let predictedVerdict = 'NO';
        if (prediction.prediction && prediction.prediction.includes('SNOW DAY VERDICT:')) {
            const match = prediction.prediction.match(/SNOW DAY VERDICT:\s*(\w+)/);
            if (match) {
                predictedVerdict = match[1].toUpperCase();
            }
        }

        // Compare prediction with actual outcome
        const actualVerdict = prediction.actual.toUpperCase();
        if (predictedVerdict === actualVerdict) {
            stats.correct++;
        }
    });

    // Calculate accuracy (avoid division by zero)
    stats.accuracy = stats.completed > 0 ? (stats.correct / stats.completed * 100) : 0;

    return stats;
}

// Function to update the stats display
function updateStats(data) {
    const stats = calculateStats(data);
    
    // Update total predictions
    const totalElement = document.getElementById('totalPredictions');
    if (totalElement) {
        totalElement.textContent = stats.total;
    }

    // Update correct predictions
    const correctElement = document.getElementById('correctPredictions');
    if (correctElement) {
        correctElement.textContent = `${stats.correct}/${stats.completed}`;
    }

    // Update accuracy
    const accuracyElement = document.getElementById('accuracyStats');
    if (accuracyElement) {
        accuracyElement.textContent = stats.completed > 0 
            ? `${stats.accuracy.toFixed(1)}%`
            : 'N/A';
    }
}

// Function to load historical data
async function loadHistoricalData() {
    try {
        const env = getEnvironment();
        const historyFile = env === 'production' ? 'history.json' : 'history_local.json';
        console.info(`Loading history from ${historyFile} (${env} environment)`);

        const response = await fetch(historyFile);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        let data;
        try {
            const text = await response.text();
            data = text.trim() ? JSON.parse(text) : { predictions: [] };
        } catch (e) {
            console.warn('Invalid JSON in history file, starting fresh');
            data = { predictions: [] };
        }

        // Validate data structure
        if (!data || typeof data !== 'object' || !Array.isArray(data.predictions)) {
            console.warn('Invalid history data structure, resetting');
            data = { predictions: [] };
        }

        window._historyData = data; // Store data globally
        updateHistoryTable(data);
        updateStats(data); // Update the statistics display
    } catch (error) {
        console.error('Error loading historical data:', error);
        const tableBody = document.getElementById('historyTableBody');
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="4" class="error-message">No prediction history available yet.</td></tr>';
        }
        // Update stats with empty data
        updateStats({ predictions: [] });
    }
}

// Function to update the history table
function updateHistoryTable(data) {
    const tableBody = document.getElementById('historyTableBody');
    if (!tableBody || !Array.isArray(data.predictions)) return;

    if (data.predictions.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="empty-message">No predictions have been made yet. Check back tomorrow!</td></tr>';
        return;
    }

    const rows = data.predictions.map(entry => {
        const date = new Date(entry.timestamp);
        const formattedDate = date.toLocaleString('en-US', {
            timeZone: 'America/New_York',
            year: 'numeric',
            month: 'numeric',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });

        // Extract the verdict from the prediction if it's in markdown format
        let verdict = entry.prediction;
        if (entry.prediction && entry.prediction.includes('SNOW DAY VERDICT:')) {
            const match = entry.prediction.match(/SNOW DAY VERDICT:\s*(\w+)/);
            if (match) {
                verdict = match[1];
            }
        }

        // Extract chance if available
        let chance = '';
        if (entry.prediction && entry.prediction.includes('CHANCE OF SNOW DAY:')) {
            const match = entry.prediction.match(/CHANCE OF SNOW DAY:\s*(\d+)%/);
            if (match) {
                chance = ` (${match[1]}%)`;
            }
        }

        return `
            <tr>
                <td>${formattedDate}</td>
                <td>${verdict}${chance}</td>
                <td>${entry.actual || 'Pending'}</td>
                <td>
                    <button class="details-button" onclick="showDetails('${entry.id}')">
                        View Details
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    tableBody.innerHTML = rows;
}

// Function to show prediction details
function showDetails(id) {
    const data = window._historyData; // Store data globally when loaded
    if (!data || !data.predictions) return;
    
    const prediction = data.predictions.find(p => p.id === id);
    if (!prediction) return;

    // Create modal content
    const modalContent = `
        <div class="modal-content">
            <h3>Prediction Details for ${new Date(prediction.timestamp).toLocaleDateString('en-US', {
                timeZone: 'America/New_York',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            })}</h3>
            <div class="prediction-details">
                ${prediction.details}
            </div>
        </div>
    `;

    // Show modal (you'll need to implement modal UI)
    alert(prediction.details); // Temporary solution - replace with proper modal
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    loadHistoricalData();
    // Set up periodic reload
    setInterval(loadHistoricalData, 300000); // Every 5 minutes
});