from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file

api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    print("API Key loaded successfully!")
else:
    print("Failed to load API Key.")

print("Loaded API Key:", api_key)  # Debugging output