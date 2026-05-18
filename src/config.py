import os
from dotenv import load_dotenv

# Load environment variables once centrally
load_dotenv()

# OpenAI Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-5.4-mini")

# Payment API Config
PAYMENT_API_BASE_URL = os.getenv("PAYMENT_API_BASE_URL", "").rstrip("/")

# Application Constants
MAX_VERIFICATION_ATTEMPTS = int(os.getenv("MAX_VERIFICATION_ATTEMPTS", "3"))
MAX_PAYMENT_ATTEMPTS = int(os.getenv("MAX_PAYMENT_ATTEMPTS", "3"))
