from dotenv import load_dotenv
import os
from openai import OpenAI
import time

# Print current working directory and .env file location
print(f"Current working directory: {os.getcwd()}")
print(f"Looking for .env in: {os.path.abspath('.env')}")
print(f".env file exists: {os.path.exists('.env')}")

# Load environment variables
load_dotenv(override=True)  # Add override=True to ensure .env takes precedence
time.sleep(0.1)  # Small delay to ensure environment variables are loaded

# Print the API key (first few characters) to verify it's loaded
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No OPENAI_API_KEY found in environment variables!")

if not api_key.startswith('sk-'):
    raise ValueError(f"Invalid API key format. Key should start with 'sk-', got: {api_key[:5]}...")

print(f"API key loaded (first 15 chars): {api_key[:15]}...")
print(f"API key length: {len(api_key)}")

# Get model name from environment
model_name = os.getenv("DEFAULT_MODEL")
if not model_name:
    raise ValueError("No MODEL_NAME found in environment variables!")
print(f"Using model: {model_name}")

# Print all environment variables containing "OPENAI"
print("\nAll OPENAI environment variables:")
for key, value in os.environ.items():
    if 'OPENAI' in key:
        print(f"{key}: {value[:15]}...")

# Initialize the client with your API key
client = OpenAI(api_key=api_key)

try:
    # First verify we can connect by listing models
    models = client.models.list()
    print("\nSuccessfully connected to OpenAI API!")
    print("Available models:", [model.id for model in models.data[:3]])
    
    # Now try a chat completion
    print("\nTesting chat completion...")
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    print("Chat response:", response.choices[0].message.content)
except Exception as e:
    print(f"\nError occurred: {str(e)}")
    raise  # Re-raise the exception to see the full stack trace
