from dotenv import load_dotenv
import os

load_dotenv()

print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY")[:20] + "..." if os.getenv("GEMINI_API_KEY") else "Not set")
print("DATABASE_URL:", os.getenv("DATABASE_URL"))
print("NEO4J_URI:", os.getenv("NEO4J_URI"))
