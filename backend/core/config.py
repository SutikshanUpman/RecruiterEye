import os
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

"""
load_dotenv() opens your .env file and loads each line 
(GITHUB_TOKEN=...) into the program’s environment variables.
"""

