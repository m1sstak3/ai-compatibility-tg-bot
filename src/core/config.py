import os
import logging
from dotenv import load_dotenv

# Load local '.env' file if present
load_dotenv()

# Logger setup
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Bot Credentials
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.warning("TELEGRAM_TOKEN is not set in environment or .env file.")

# LLM Providers
LLM_API_KEY = os.getenv("LLM_API_KEY") 
if not LLM_API_KEY:
    logger.warning("LLM_API_KEY is not set. OpenRouter will not work.")

# We don't use cerebras directly anymore if we switched to Openrouter, but keeping config if needed
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

# Models Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "qwen/qwen3-next-80b-a3b-instruct:free")
MODEL_QUESTIONS = os.getenv("MODEL_QUESTIONS", "qwen/qwen3-235b-a22b-thinking-2507")
MODEL_FAKES = os.getenv("MODEL_FAKES", "qwen/qwen3-next-80b-a3b-instruct:free")

# Database Configuration
DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///game.db")
