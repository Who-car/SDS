import os
from dotenv import load_dotenv

load_dotenv()
AUTH = os.getenv("AUTH")
FOLDER_ID = os.getenv("FOLDER_ID")
PORT = int(os.getenv("PORT"))
ASSISTANT_ID = os.getenv("ASSISTANT_ID")