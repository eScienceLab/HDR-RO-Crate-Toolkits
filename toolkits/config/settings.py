import os 

from dotenv import load_dotenv

load_dotenv()

CRATEY_VALIDATOR_API_URL = os.getenv("CRATEY_VALIDATOR_API_URL")
