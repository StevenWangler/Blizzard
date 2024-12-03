# Snow Day Prediction Platform

A multi-agent system that predicts snow days using weather data and simulates a decision-making process between school administrators. Features a modern web interface for viewing predictions and customizable snow day criteria.

## Prerequisites

- Python 3.8 or higher
- OpenAI API key with GPT-4 access
- WeatherAPI key (free tier works fine)
- Git (for version control)

## Features

- Weather analysis using real-time data from WeatherAPI
- Three specialized agents:
  1. Weather Agent: Analyzes weather data
  2. Superintendent: Makes initial snow day decisions with probability assessment
  3. Vice Superintendent: Reviews and validates decisions
- Natural conversation flow between agents
- Automated decision-making process
- Modern web interface for viewing predictions
- Daily updates via GitHub Actions
- Customizable snow day criteria via external file
- School-specific theming support

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.template` to `.env`:
   ```bash
   cp .env.template .env
   ```
4. Get your API keys:
   - OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - Weather API key from [WeatherAPI](https://www.weatherapi.com/)
5. Add your API keys and configuration to the `.env` file

## Snow Day Criteria Configuration

The system uses a customizable criteria file to determine snow day conditions:

1. Create a `snowday_criteria.txt` file in your preferred location
2. Format each criterion on a new line
3. Example criteria:
   ```
   Snow accumulation of 6 inches or more
   Temperature below 15°F
   Wind chill advisory in effect
   Freezing rain forecast
   ```
4. The system will dynamically load these criteria during the decision process
5. Superintendent will consider ALL criteria when making decisions
6. Each decision includes a percentage probability of declaring a snow day

### Criteria File Guidelines

- Keep criteria clear and specific
- One condition per line
- Focus on measurable weather conditions
- Include both weather and safety factors
- File can be updated without code changes

## Usage

Run the snow day prediction system:
```bash
python main.py
```

The agents will automatically:
1. Fetch current weather data for your configured ZIP code
2. Analyze weather conditions
3. Make a snow day decision
4. Review and validate the decision
5. Reach a consensus
6. Generate a data.json file with the results

## Web Interface

The project includes a modern web interface for viewing predictions:

- Located in the `static/` directory
- Displays the final decision and agent conversation
- Updates automatically when new predictions are made
- Supports markdown formatting for agent messages
- Customizable color scheme for school branding
- Clear distinction between conversation participants

### Local Development
```bash
# Using Python's built-in server
python -m http.server --directory static

# Or using any static file server
```

### GitHub Pages Deployment

The project is set up to automatically deploy to GitHub Pages using GitHub Actions. Here's how to set it up:

1. In your repository settings:
   - Go to "Settings" > "Pages"
   - Under "Build and deployment", select "GitHub Actions" as the source

2. Set up required secrets in your repository:
   - Go to "Settings" > "Secrets and variables" > "Actions"
   - Add these secrets:
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `WEATHER_API_KEY`: Your WeatherAPI key
     - `ZIP_CODE`: Your target ZIP code

3. Set up model variables (optional):
   - In the same section, go to the "Variables" tab
   - Add these variables if you want to customize the models:
     - `MODEL_NAME`
     - `WEATHER_MODEL`
     - `BLIZZARD_MODEL`
     - `ASSISTANT_MODEL`
     - `SELECTION_MODEL`
     - `TERMINATION_MODEL`

4. The workflow will:
   - Run automatically at 8PM EST daily
   - Update the weather data and predictions
   - Deploy to GitHub Pages
   - You can also trigger it manually from the Actions tab

Your site will be available at: `https://[your-username].github.io/[repository-name]/`

## Configuration

- ZIP code is configurable in .env file
- Weather data focuses on evening to morning period (7 PM - 8 AM)
- Maximum conversation iterations is set to 10
- Supports custom OpenAI models via MODEL_NAME in .env
- Customizable snow day criteria via external file
- Configurable UI theming in styles.css

## Troubleshooting

### Common Issues

1. **OpenAI API Error**
   - Ensure your API key is valid and has access to GPT-4
   - Check your API quota and billing status
   - Verify MODEL_NAME in .env matches available models

2. **Weather API Error**
   - Verify your API key is active
   - Check if your ZIP code is valid
   - Ensure you're within the API rate limits

3. **Web Interface Not Updating**
   - Verify data.json is being generated in the static directory
   - Check file permissions
   - Clear browser cache

### Logs

The application logs important information to the console. For debugging:
1. Run the script with default logging
2. Check the console output for ERROR or WARNING messages
3. Ensure all required environment variables are set

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Please ensure your changes:
- Include appropriate documentation
- Maintain existing code style
- Add necessary tests
- Update README if needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.
