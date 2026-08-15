"""
list_models.py

CHERA IN SCRIPT VOJUD DARE
--------------------------
Model name-ha deprecate mishan. text-embedding-004 to 14 January 2026
hazf shod va pipeline-haye kheili-ha ye shab shekast.

Rah-e hal: hich vaght model name ro az hafeze/tutorial hads nazan -
az khode API beporrs ke alan chi mojud-e.

Estefade:
    python scripts/list_models.py
"""

import os

from dotenv import load_dotenv
from google import genai


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY peyda nashod. .env ro check kon.")

    client = genai.Client(api_key=api_key)

    embedding_models = []
    generation_models = []

    for model in client.models.list():
        actions = model.supported_actions or []
        if "embedContent" in actions:
            embedding_models.append(model)
        if "generateContent" in actions:
            generation_models.append(model)

    print("=== EMBEDDING models (embedContent) ===")
    for m in embedding_models:
        print(f"  {m.name}")

    print("\n=== GENERATION models (generateContent) ===")
    for m in generation_models:
        print(f"  {m.name}")


if __name__ == "__main__":
    main()
