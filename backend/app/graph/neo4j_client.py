from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv(override=True)

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "").strip(),
    auth=(
        os.getenv("NEO4J_USERNAME", "").strip(),
        os.getenv("NEO4J_PASSWORD", "").strip()
    )
)
