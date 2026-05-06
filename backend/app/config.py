import os
from dotenv import load_dotenv

# Load only for local development
if os.getenv("RUN_ENV") != "docker":
    load_dotenv(".env.local")

DATABASE_URL = os.environ["DATABASE_URL"]