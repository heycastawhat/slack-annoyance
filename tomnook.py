import os
import random

from slack_sdk import WebClient

# optionally load environment variables from a .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception as e:
    print(f"Err: {e}")

# --- CONFIG ---
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")

# to do 
# - add quotes
# - add random
# - add channel
QUOTES = [
#quotes go here, josh (if youre too stupid to figure it out, i dont know, 11:37pm you is different than sleep deprived morning you. good luck.)
]