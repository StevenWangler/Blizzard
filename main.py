"""
Snow Day Prediction Platform

This module implements a multi-agent system for predicting snow days using weather data
and simulating a decision-making process between school administrators. It uses the
Semantic Kernel framework to coordinate multiple AI agents that analyze weather data
and make collaborative decisions.

The system consists of three main agents:
1. Weather Agent: Analyzes weather conditions and provides detailed reports
2. Superintendent: Makes initial snow day decisions based on weather analysis
3. Vice Superintendent: Reviews and validates decisions

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

# Local imports
from weather.weather_data import WeatherAPI, get_relevant_weather_information

# Constants
WEATHER_AGENT = "WeatherAgent"
SUPERINTENDENT = "Superintendent"
VICE_SUPERINTENDENT = "ViceSuperintendent"
MAX_RETRIES = 5
RETRY_DELAY = 1  # seconds
REQUEST_TIMEOUT = 30  # seconds

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
        self._min_request_interval = 1.0

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
        
        for attempt in range(MAX_RETRIES):
            try:
                self._last_request_time = time.time()
                return await super()._send_completion_request(settings)
            except Exception as e:
                if "rate" in str(e).lower() and attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    logging.info(f"Rate limit hit, waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                raise

def _create_kernel_with_chat_service(service_id: str) -> Kernel:
    """
    Create a new kernel with a rate-limited chat service.
    
    Args:
        service_id (str): Unique identifier for the chat service
        
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
            ai_model_id=model_name,
            api_key=openai_key
        )
        kernel.add_service(chat_service)
        return kernel
    except Exception as e:
        logging.error(f"Error creating kernel: {str(e)}")
        if "api_key" in str(e).lower():
            logging.error("API key validation failed. Please check your .env file and ensure the OPENAI_API_KEY is correct.")
        elif "model" in str(e).lower():
            logging.error(f"Model '{model_name}' not available. Please check your OpenAI account access.")
        raise

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
        # Create separate kernels for each agent
        weather_kernel = _create_kernel_with_chat_service("weather_chat")
        superintendent_kernel = _create_kernel_with_chat_service("superintendent_chat")
        vice_kernel = _create_kernel_with_chat_service("vice_chat")
        selection_kernel = _create_kernel_with_chat_service("selection_chat")
        termination_kernel = _create_kernel_with_chat_service("termination_chat")

        # Create Weather Agent with enhanced weather analysis capabilities
        agent_weather = ChatCompletionAgent(
            service_id="weather_chat",
            kernel=weather_kernel,
            name=WEATHER_AGENT,
            instructions="""
                You are a weather analysis agent with expertise in winter weather conditions. Your role is to:
                1. Analyze detailed weather data including:
                   - Temperature and wind chill
                   - Snow accumulation and precipitation chances
                   - Wind speeds and visibility
                   - Weather alerts and their severity
                2. Focus on the critical overnight period (7 PM to 8 AM)
                3. Provide a comprehensive analysis considering:
                   - Ground conditions and snow accumulation
                   - Travel safety based on visibility and wind
                   - Temperature trends and wind chill factors
                4. Highlight any weather alerts and their implications
                
                Format your response with specific data points and clear analysis of safety implications.
                """,
        )

        # Create Superintendent Agent with detailed decision criteria
        agent_superintendent = ChatCompletionAgent(
            service_id="superintendent_chat",
            kernel=superintendent_kernel,
            name=SUPERINTENDENT,
            instructions="""
                You are a school superintendent responsible for snow day decisions. Your role is to:
                1. Analyze the detailed weather report considering:
                   - Snow accumulation and timing
                   - Road conditions and visibility
                   - Temperature and wind chill factors
                   - Weather alerts and their severity
                2. Consider multiple factors:
                   - Student and staff safety during commute times
                   - Building accessibility and parking lot conditions
                   - Bus route safety and timing
                   - Walking conditions for students
                3. Make a clear decision with detailed reasoning
                4. Consider both immediate and developing conditions
                
                Base your decision on concrete data and clear safety thresholds.
                """,
        )

        # Create Vice Superintendent Agent with enhanced review criteria
        agent_vice = ChatCompletionAgent(
            service_id="vice_chat",
            kernel=vice_kernel,
            name=VICE_SUPERINTENDENT,
            instructions="""
                You are the vice superintendent reviewing snow day decisions. Your role is to:
                1. Critically analyze the superintendent's decision considering:
                   - All weather metrics and their trends
                   - Historical precedents for similar conditions
                   - Impact on academic calendar and makeup days
                   - Community impact and expectations
                2. Challenge assumptions and identify overlooked factors
                3. Consider alternative solutions (delayed opening, early dismissal)
                4. Work towards a consensus based on data and safety
                
                Be constructive but thorough in your analysis, always prioritizing safety.
                """,
        )

        # Create selection strategy
        selection_function = KernelFunctionFromPrompt(
            function_name="selection",
            prompt=f"""
            Determine which participant takes the next turn based on the conversation flow.
            State only the name of the participant to take the next turn.

            Participants:
            - {WEATHER_AGENT}
            - {SUPERINTENDENT}
            - {VICE_SUPERINTENDENT}

            Rules:
            - Start with {WEATHER_AGENT}
            - After {WEATHER_AGENT}, {SUPERINTENDENT} should analyze and decide
            - After {SUPERINTENDENT}, {VICE_SUPERINTENDENT} should review
            - If there's disagreement, continue the conversation between {SUPERINTENDENT} and {VICE_SUPERINTENDENT}
            - End when both superintendents agree

            History:
            {{$history}}
            """,
        )

        # Create termination strategy
        termination_function = KernelFunctionFromPrompt(
            function_name="termination",
            prompt="""
                Determine if the conversation should end based on these criteria:
                1. Both superintendents have reached an agreement
                2. A final decision has been clearly stated
                3. All safety concerns have been addressed
                4. Weather data has been thoroughly analyzed

                Respond with 'TERMINATE' if these criteria are met.

                History:
                {{$history}}
                """,
        )

        # Create group chat
        chat = AgentGroupChat(
            agents=[agent_weather, agent_superintendent, agent_vice],
            selection_strategy=KernelFunctionSelectionStrategy(
                function=selection_function,
                kernel=selection_kernel,
                result_parser=lambda result: str(result.value[0]) if result.value is not None else WEATHER_AGENT,
                agent_variable_name="agents",
                history_variable_name="history",
            ),
            termination_strategy=KernelFunctionTerminationStrategy(
                agents=[agent_superintendent, agent_vice],
                function=termination_function,
                kernel=termination_kernel,
                result_parser=lambda result: "TERMINATE" in str(result.value[0]).upper(),
                history_variable_name="history",
                maximum_iterations=10,
            ),
        )

        # Get detailed weather data
        weather_api = WeatherAPI()
        forecast_data = weather_api.get_forecast()
        if not forecast_data:
            logging.error("Failed to fetch weather data")
            return

        weather_data = get_relevant_weather_information(forecast_data)
        initial_prompt = (
            f"Please analyze this detailed weather data for snow day prediction:\n"
            f"Weather Data: {weather_data}\n\n"
            f"Consider all metrics including temperature, snow accumulation, visibility, "
            f"wind conditions, and any weather alerts. Provide a thorough analysis for "
            f"making a snow day decision."
        )
        
        conversation_data = {
            "timestamp": datetime.now().isoformat(),
            "conversation": [],
            "decision": None
        }

        await chat.add_chat_message(ChatMessageContent(role=AuthorRole.USER, content=initial_prompt))

        try:
            async for response in chat.invoke():
                print(f"# {response.role} - {response.name}: '{response.content}'")
                conversation_data["conversation"].append({
                    "role": str(response.role),
                    "name": response.name,
                    "content": response.content
                })
                # If this is the final message from a superintendent, use it as the decision
                if response.name in [SUPERINTENDENT, VICE_SUPERINTENDENT] and chat.is_complete:
                    conversation_data["decision"] = response.content

        except Exception as e:
            logging.error(f"Error during chat invocation: {str(e)}")
            if "quota" in str(e).lower():
                logging.error("OpenAI API quota exceeded. Please check your billing details or try using a different API key.")
            raise

        # Save the conversation data to a JSON file
        with open("static/data.json", "w") as f:
            json.dump(conversation_data, f, indent=2)

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s'
    )

    # Set more verbose loggers to WARNING level
    logging.getLogger('semantic_kernel').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)

    # Load and validate environment variables
    load_dotenv(override=True)
    time.sleep(0.1)  # Small delay to ensure environment variables are loaded

    openai_key = os.getenv("OPENAI_API_KEY")
    weather_key = os.getenv("WEATHER_API_KEY")
    model_name = os.getenv("MODEL_NAME")

    # Validate environment variables
    if not openai_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    if not openai_key.startswith('sk-'):
        raise ValueError(f"Invalid API key format. Key should start with 'sk-', got: {openai_key[:5]}...")
    if not weather_key:
        raise ValueError("WEATHER_API_KEY not found in environment variables")
    if not model_name:
        raise ValueError("MODEL_NAME not found in environment variables")

    logging.info(f"API key validated (first 15 chars): {openai_key[:15]}...")
    logging.info(f"Using model: {model_name}")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        sys.exit(1) 