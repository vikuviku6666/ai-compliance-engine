from dotenv import load_dotenv
import os

load_dotenv()

print("OPENROUTER_API_KEY:", os.getenv("OPENROUTER_API_KEY")[:20] + "..." if os.getenv("OPENROUTER_API_KEY") else "Not set")
print("DATABASE_URL:", os.getenv("DATABASE_URL"))
print("NEO4J_URI:", os.getenv("NEO4J_URI"))
