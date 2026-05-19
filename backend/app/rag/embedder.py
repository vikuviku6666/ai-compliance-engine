import os
import warnings
from dotenv import load_dotenv

load_dotenv(override=True)

# Suppress unauthenticated HF Hub warnings — public models work without a token
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ.setdefault("HUGGINGFACE_HUB_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore", message=".*unauthenticated.*")
warnings.filterwarnings("ignore", message=".*HF_TOKEN.*")

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-large-en-v1.5")


def create_embedding(text):
    embedding = model.encode(text)
    return embedding.tolist()
