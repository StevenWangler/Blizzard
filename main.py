"""
Snow Day Prediction Platform

This module implements a multi-agent system for predicting snow days using weather data
and simulating a decision-making process between school administrators. It uses the
Semantic Kernel framework to coordinate multiple AI agents that analyze weather data
and make collaborative decisions.

The system consists of four main agents:
1. Weather Agent: Analyzes weather conditions and provides detailed reports
2. Snow Research Lead: Makes initial snow day analysis based on weather data
3. Research Assistant: Reviews and validates analysis
4. Blizzard: Final decision maker who reports the verdict with confidence percentage

The agents communicate through a structured chat system, with their conversation
and final decision being saved to a JSON file for web display.

Author: Steven
License: MIT
"""

# Standard library imports
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Third-party imports
from dotenv import load_dotenv
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies.selection.kernel_function_selection_strategy import (
    KernelFunctionSelectionStrategy,
)
from semantic_kernel.agents.strategies.termination.kernel_function_termination_strategy import (
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.functions.kernel_function_from_prompt import KernelFunctionFromPrompt
from semantic_kernel.kernel import Kernel
import yaml

# Local imports
from weather.weather_data import WeatherAPI, get_relevant_weather_information

# Constants
WEATHER_AGENT = "WeatherAgent"
SNOW_RESEARCH_LEAD = "SnowResearchLead"
RESEARCH_ASSISTANT = "ResearchAssistant"
BLIZZARD = "Blizzard"
MAX_RETRIES = 5
RETRY_DELAY = 1  # seconds
REQUEST_TIMEOUT = 30  # seconds

# Set up logging configuration immediately
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_dir / "blizzard.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting Blizzard snow day prediction system")

class RateLimitedOpenAIChatCompletion(OpenAIChatCompletion):
    """
    Extended OpenAI Chat Completion with rate limiting and retry logic.
    
    This class adds rate limiting and exponential backoff retry functionality
    to the base OpenAI Chat Completion class to handle API rate limits gracefully.
    
    Attributes:
        _last_request_time (float): Timestamp of the last request
        _min_request_interval (float): Minimum time between requests in seconds
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_request_time = 0
        self._min_request_interval = 2.0
        self._backoff_factor = 2
        self._max_backoff = 30

    async def _send_completion_request(self, settings):
        """
        Send a completion request with rate limiting and retry logic.
        
        Args:
            settings: The completion request settings
            
        Returns:
            The completion response from the API
            
        Raises:
            Exception: If the request fails after all retries
        """
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last_request)
        
        backoff = self._min_request_interval
        for attempt in range(MAX_RETRIES):
            try:
                self._last_request_time = time.time()
                return await super()._send_completion_request(settings)
            except Exception as e:
                if "rate" in str(e).lower() and attempt < MAX_RETRIES - 1:
                    backoff = min(backoff * self._backoff_factor, self._max_backoff)
                    logging.info(f"Rate limit hit, waiting {backoff} seconds before retry...")
                    await asyncio.sleep(backoff)
                    continue
                raise

def _create_kernel_with_chat_service(service_id: str, model_override: str = None) -> Kernel:
    """
    Create a new kernel with a rate-limited chat service.
    
    Args:
        service_id (str): Unique identifier for the chat service
        model_override (str, optional): Override the default model for this specific service
        
    Returns:
        Kernel: Configured kernel with the chat service added
        
    Raises:
        ValueError: If required environment variables are missing
        Exception: If kernel creation fails
    """
    try:
        kernel = Kernel()
        chat_service = RateLimitedOpenAIChatCompletion(
            service_id=service_id,
            ai_model_id=model_override or model_name,  # Use override if provided, else default
            api_key=openai_key
        )
        kernel.add_service(chat_service)
        return kernel
    except Exception as e:
        logging.error(f"Error creating kernel: {str(e)}")
        if "api_key" in str(e).lower():
            logging.error("API key validation failed. Please check your .env file and ensure the OPENAI_API_KEY is correct.")
        elif "model" in str(e).lower():
            logging.error(f"Model '{model_override or model_name}' not available. Please check your OpenAI account access.")
        raise

def read_prompt(filename):
    """Read a prompt from a file in the agent instructions directory."""
    with open(f"agent instructions/{filename}", "r") as f:
        return f.read().strip()

def read_criteria():
    """
    Read the district's closure criteria for weather-related school cancellations.
    
    Returns:
        str: The district's criteria for school closures, or a default message if not found.
        
    The function looks for the criteria file in the following locations:
    1. config/district/closure_criteria.txt (preferred location)
    2. misc data/snowday_criteria.txt (legacy location for backward compatibility)
    """
    possible_locations = [
        "config/district/closure_criteria.txt",  # New preferred location
        "misc data/snowday_criteria.txt"         # Legacy location
    ]
    
    for file_path in possible_locations:
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    logging.warning(f"Criteria file {file_path} is empty")
                    continue
                logging.info(f"Successfully loaded district criteria from {file_path}")
                return content
        except FileNotFoundError:
            logging.debug(f"No criteria file found at {file_path}")
            continue
        except PermissionError:
            logging.error(f"Permission denied when trying to read {file_path}")
            continue
        except UnicodeDecodeError:
            logging.error(f"Encoding issue when reading {file_path}. Ensure the file is UTF-8 encoded.")
            continue
        except Exception as e:
            logging.error(f"Unexpected error reading {file_path}: {str(e)}")
            continue

    # If we get here, no valid criteria file was found
    default_criteria = """Default School Closure Criteria:
- Consider student and staff safety as the primary factor
- Monitor weather conditions including temperature, precipitation, and wind
- Evaluate road conditions and transportation safety
- Account for building and facility operations
Please replace this with your district's specific criteria in config/district/closure_criteria.txt"""
    
    logging.warning("No district criteria file found. Using default criteria. "
                   "Please create config/district/closure_criteria.txt with your district's specific criteria.")
    return default_criteria

def read_settings():
    """Read district settings from YAML file."""
    try:
        with open("config/district/settings.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Failed to load district settings: {str(e)}")
        return {}

def format_settings_for_agents(settings):
    """Format settings into a readable string for agents."""
    if not settings:
        return "No district settings available."
    
    formatted = "DISTRICT CONTEXT AND SETTINGS:\n\n"
    
    # Snow Days Status
    snow_days = settings.get('snow_days', {})
    formatted += "Snow Day Status:\n"
    formatted += f"- Allotted snow days: {snow_days.get('allotted', 'N/A')}\n"
    formatted += f"- Used snow days: {snow_days.get('used', 'N/A')}\n\n"
    
    # Community Context
    community = settings.get('community', {})
    formatted += "Community Context:\n"
    formatted += f"- State: {community.get('state', 'N/A')}\n"
    formatted += f"- Community type: {community.get('type', 'N/A')}\n"
    formatted += f"- Winter experience: {community.get('winter_experience', 'N/A')}\n"
    formatted += f"- Bus dependent students: {community.get('bus_dependent_percentage', 'N/A')}%\n\n"
    
    # Current Conditions
    current = settings.get('current', {})
    formatted += "Current Conditions:\n"
    formatted += f"- Community hype level: {current.get('hype_level', 'N/A')}/10\n"
    formatted += f"- Nearby district closures: {current.get('nearby_closures', 'N/A')}\n"
    formatted += f"- Social media activity: {current.get('social_media_buzz', 'N/A')}\n\n"
    
    # Additional Notes
    notes = settings.get('notes', [])
    if notes:
        formatted += "Important Community Notes:\n"
        for note in notes:
            formatted += f"- {note}\n"
    
    return formatted

def get_history_file():
    """Get the appropriate history file path based on environment."""
    env = os.getenv('BLIZZARD_ENV', 'development')  # Default to development if not set
    logging.info(f"Running in {env} environment")
    return "static/history.json" if env == 'production' else "static/history_local.json"

def update_history(data):
    """Update history.json with the latest prediction."""
    history_file = get_history_file()
    try:
        # Create or read history file
        history = {"predictions": []}
        if os.path.exists(history_file) and os.path.getsize(history_file) > 0:
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
                    if not isinstance(history, dict) or "predictions" not in history:
                        history = {"predictions": []}
            except json.JSONDecodeError:
                # If file is invalid JSON, start fresh
                history = {"predictions": []}

        # Create new prediction entry
        new_prediction = {
            "id": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": data["timestamp"],
            "prediction": data["decision"],
            "actual": None,
            "details": data["conversation"][-1]["content"]  # Last Blizzard message
        }

        # Add new prediction to history
        if not isinstance(history.get("predictions"), list):
            history["predictions"] = []
        history["predictions"].insert(0, new_prediction)  # Add at the beginning

        # Write updated history
        with open(history_file, "w") as f:
            json.dump(history, f, indent=4)

        logging.info(f"Successfully updated {history_file}")
    except Exception as e:
        logging.error(f"Error updating {history_file}: {str(e)}")

def inject_environment_into_html():
    """Inject the current environment into HTML files."""
    env = os.getenv('BLIZZARD_ENV', 'development')
    html_files = ['static/index.html', 'static/history.html']
    
    for file_path in html_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Replace environment placeholder
            content = content.replace('{{ env }}', env)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            logging.info(f"Injected environment '{env}' into {file_path}")
        except Exception as e:
            logging.error(f"Error injecting environment into {file_path}: {str(e)}")

async def main():
    """
    Main function that orchestrates the snow day prediction process.
    
    This function:
    1. Sets up the agent infrastructure
    2. Fetches weather data
    3. Initiates the agent conversation
    4. Saves the results to a JSON file
    
    Raises:
        Exception: If any part of the process fails
    """
    try:
        # Read district criteria and settings
        try:
            district_criteria = read_criteria()
            district_settings = read_settings()
            settings_text = format_settings_for_agents(district_settings)
        except Exception as e:
            logging.error(f"Failed to load district information: {str(e)}")
            district_criteria = "ERROR: Failed to load district criteria."
            settings_text = "ERROR: Failed to load district settings."
        
        # Create separate kernels for each agent with specific models
        weather_kernel = _create_kernel_with_chat_service("weather_chat", os.getenv("WEATHER_MODEL"))
        research_lead_kernel = _create_kernel_with_chat_service("research_lead_chat", os.getenv("BLIZZARD_MODEL"))
        research_assistant_kernel = _create_kernel_with_chat_service("research_assistant_chat", os.getenv("ASSISTANT_MODEL"))
        blizzard_kernel = _create_kernel_with_chat_service("blizzard_chat", os.getenv("BLIZZARD_MODEL"))
        selection_kernel = _create_kernel_with_chat_service("selection_chat", os.getenv("SELECTION_MODEL"))
        termination_kernel = _create_kernel_with_chat_service("termination_chat", os.getenv("TERMINATION_MODEL"))

        # Create Weather Agent with enhanced weather analysis capabilities
        agent_weather = ChatCompletionAgent(
            service_id="weather_chat",
            kernel=weather_kernel,
            name=WEATHER_AGENT,
            instructions=read_prompt("weather_agent.txt"),
        )

        # Create Snow Research Lead Agent with detailed analysis criteria and settings
        research_lead_instructions = (
            f"{read_prompt('snow_research_lead.txt')}\n\n"
            f"DISTRICT CLOSURE CRITERIA:\n{district_criteria}\n\n"
            f"{settings_text}"
        )
        agent_research_lead = ChatCompletionAgent(
            service_id="research_lead_chat",
            kernel=research_lead_kernel,
            name=SNOW_RESEARCH_LEAD,
            instructions=research_lead_instructions,
        )

        # Create Research Assistant Agent with enhanced review criteria and settings
        research_assistant_instructions = (
            f"{read_prompt('research_assistant.txt')}\n\n"
            f"DISTRICT CLOSURE CRITERIA:\n{district_criteria}\n\n"
            f"{settings_text}"
        )
        agent_research_assistant = ChatCompletionAgent(
            service_id="research_assistant_chat",
            kernel=research_assistant_kernel,
            name=RESEARCH_ASSISTANT,
            instructions=research_assistant_instructions,
        )

        # Create Blizzard Reporter Agent for final verdict
        blizzard_instructions = (
            f"{read_prompt('blizzard_reporter.txt')}\n\n"
            f"DISTRICT CLOSURE CRITERIA:\n{district_criteria}\n\n"
            f"{settings_text}"
        )
        agent_blizzard = ChatCompletionAgent(
            service_id="blizzard_chat",
            kernel=blizzard_kernel,
            name=BLIZZARD,
            instructions=blizzard_instructions,
        )

        # Create selection strategy with modified result parser
        selection_function = KernelFunctionFromPrompt(
            function_name="selection",
            prompt=read_prompt("selection_strategy.txt"),
        )

        def selection_parser(result):
            """Parse the selection strategy result, handling TERMINATE gracefully"""
            result_str = str(result.value[0]).strip()
            
            if result_str.upper() in ['TERMINATE', 'NONE', '']:
                # Return the last agent who spoke to give them a chance to conclude
                return chat.history.messages[-1].name if chat.history.messages else None
            
            # Find the matching agent by name (case-insensitive)
            agent_map = {agent.name.upper(): agent.name for agent in chat.agents}
            return agent_map.get(result_str.upper())

        # Create termination strategy
        termination_function = KernelFunctionFromPrompt(
            function_name="termination",
            prompt=read_prompt("termination_strategy.txt"),
        )

        # Create group chat with modified selection strategy
        chat = AgentGroupChat(
            agents=[agent_weather, agent_research_lead, agent_research_assistant, agent_blizzard],
            selection_strategy=KernelFunctionSelectionStrategy(
                function=selection_function,
                kernel=selection_kernel,
                result_parser=selection_parser,
                agent_variable_name="agents",
                history_variable_name="history",
            ),
            termination_strategy=KernelFunctionTerminationStrategy(
                agents=[agent_weather, agent_research_lead, agent_research_assistant, agent_blizzard],
                function=termination_function,
                kernel=termination_kernel,
                result_parser=lambda result: str(result.value[0]).upper() == 'TERMINATE',
                history_variable_name="history",
                maximum_iterations=20,
            ),
        )

        # Get detailed weather data
        weather_api = WeatherAPI()
        forecast_data = weather_api.get_forecast()
        if not forecast_data:
            logging.error("Failed to fetch weather data")
            return

        # Prepare the initial weather analysis request
        weather_data = get_relevant_weather_information(forecast_data)
        initial_prompt = (
            f"Please provide a detailed weather report for the following data.\n\n"
            f"Weather Data: {weather_data}\n\n"
            f"Focus ONLY on reporting the weather conditions. DO NOT make any predictions or analysis about snow days."
        )

        # Start the conversation with the initial prompt
        await chat.add_chat_message(ChatMessageContent(role=AuthorRole.USER, content=initial_prompt))

        # Initialize conversation data
        conversation_data = {
            "timestamp": datetime.now().isoformat(),
            "conversation": [],
            "decision": None
        }

        try:
            async for response in chat.invoke():
                print(f"# {response.role} - {response.name}: '{response.content}'")
                conversation_data["conversation"].append({
                    "role": str(response.role),
                    "name": response.name,
                    "content": response.content
                })
                # Only use Blizzard's final verdict as the decision
                if response.name == BLIZZARD and "SNOW DAY VERDICT" in response.content:
                    conversation_data["decision"] = response.content

        except Exception as e:
            logging.error(f"Error during chat invocation: {str(e)}")
            if "quota" in str(e).lower():
                logging.error("OpenAI API quota exceeded. Please check your billing details or try using a different API key.")
            raise

        # Save the conversation data to a JSON file
        with open("static/data.json", "w") as f:
            json.dump(conversation_data, f, indent=2)

        # Update history.json with the latest prediction
        update_history(conversation_data)

        # After generating predictions, inject environment
        inject_environment_into_html()

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO,  # Keep default at INFO but move routine messages to DEBUG
        handlers=[logging.StreamHandler()]
    )

    # Load environment variables
    load_dotenv()
    openai_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("MODEL_NAME", "gpt-4")

    if not openai_key:
        logging.error("OPENAI_API_KEY not found in environment variables")
        sys.exit(1)

    # Validate API key format (first 15 chars only for security)
    logging.info(f"API key validated (first 15 chars): {openai_key[:15]}...")
    logging.info(f"Using model: {model_name}")

    # Run the main async function
    asyncio.run(main()) 
