import os
import json
import chromadb
from openai import OpenAI
import dotenv

# 1. Konfiguration laden
dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chromadb")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
COLLECTION_NAME = "company_kb"

# Clients initialisieren
client_openai = OpenAI(api_key=OPENAI_API_KEY)
client_chroma = chromadb.PersistentClient(path=CHROMA_PATH)

def get_embedding(text):
    """Erzeugt einen Vektor für einen gegebenen Text mittels OpenAI API."""
    text = text.replace("\n", " ") # Zeilenumbrüche entfernen für bessere Vektoren
    response = client_openai.embeddings.create(
        input=[text],
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def build_index():
    print(f"--- Starte Indexierung ---")
    
    # 2. Daten laden
    doc_path = os.path.join("data", "docs", "documents.json")
    with open(doc_path, "r", encoding="utf-8") as f:
        documents = json.load(f)
    
    print(f"Lade {len(documents)} Dokumente aus {doc_path}...")

    # 3. Chroma Collection erstellen (löschen falls existent, um sauber neu zu bauen)
    try:
        client_chroma.delete_collection(name=COLLECTION_NAME)
        print(f"Alte Collection '{COLLECTION_NAME}' gelöscht.")
    except Exception:
        pass # Collection existierte noch nicht
    
    collection = client_chroma.create_collection(name=COLLECTION_NAME)

    # 4. Embeddings erzeugen und speichern
    for doc in documents:
        content = doc["content"]
        meta = doc["metadata"]
        doc_id = doc["id"]

        print(f"Verarbeite: {doc_id} ({meta['classification']})...")
        
        # Vektor holen
        vector = get_embedding(content)

        # In DB speichern
        collection.add(
            documents=[content],       # Der Text
            embeddings=[vector],       # Der Vektor
            metadatas=[meta],          # Die Metadaten (für RBAC wichtig!)
            ids=[doc_id]               # Eindeutige ID
        )
    
    print(f"✅ Indexierung abgeschlossen. Datenbank gespeichert in {CHROMA_PATH}")

    # 5. Kurzer Test: Ein Dokument suchen
    print("\n--- Test-Suche ---")
    query = "Was plant die Geschäftsführung?"
    query_vec = get_embedding(query)
    
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=2
    )
    
    print(f"Frage: '{query}'")
    for i, doc_text in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][i]
        print(f"Gefundenes Dok ({meta['classification']}): {doc_text}")

if __name__ == "__main__":
    build_index()