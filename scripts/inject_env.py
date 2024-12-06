"""
Environment injection utility script.

This script reads the environment configuration from env/.env and injects it into the HTML files.
It's used to ensure the web interface uses the correct environment (development/production).

Usage:
    python3 scripts/inject_env.py
"""

from dotenv import load_dotenv
import os
from pathlib import Path

def inject_env():
    """Inject the environment from env/.env into HTML files."""
    # Get root directory
    root_dir = Path(__file__).parent.parent
    
    # Load environment from .env
    env_path = root_dir / 'env' / '.env'
    load_dotenv(env_path)
    env = os.getenv('BLIZZARD_ENV', 'development')
    
    # Files to update
    html_files = [
        root_dir / 'static' / 'index.html',
        root_dir / 'static' / 'history.html'
    ]
    
    for file_path in html_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Replace environment placeholder or existing environment
            content = content.replace('content="development"', 'content="{{ env }}"')
            content = content.replace('content="production"', 'content="{{ env }}"')
            content = content.replace('{{ env }}', env)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Injected environment '{env}' into {file_path.name}")
        except Exception as e:
            print(f"❌ Error injecting environment into {file_path.name}: {str(e)}")

if __name__ == "__main__":
    inject_env() 