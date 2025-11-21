import os
import time  # Neu: Für die Zeitmessung
import chromadb
from openai import OpenAI
from app.security.rbac import check_access
from app.logging.audit import log_request # Neu: Import des Loggers
import dotenv

# Konfiguration laden
dotenv.load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chromadb")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4-turbo")
COLLECTION_NAME = "company_kb"

class RbacRagPipeline:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.chroma_client.get_collection(name=COLLECTION_NAME)
        self.openai_client = OpenAI()

    def get_embedding(self, text):
        text = text.replace("\n", " ")
        response = self.openai_client.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding

    def ask(self, user_role: str, query: str):
        start_time = time.time() # Startzeit messen
        
        print(f"\n--- Neue Anfrage ---")
        print(f"Rolle: {user_role} | Frage: {query}")

        # 1. RETRIEVAL
        query_vec = self.get_embedding(query)
        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=5
        )

        allowed_docs = [] # Liste der Texte
        allowed_ids = []  # Liste der IDs für das Log
        blocked_docs_count = 0

        num_results = len(results['documents'][0])
        
        print("Prüfe Dokumente:")
        for i in range(num_results):
            doc_text = results['documents'][0][i]
            metadata = results['metadatas'][0][i]
            doc_id = results['ids'][0][i]
            classification = metadata.get("classification", "internal")

            # 2. RBAC FILTERUNG
            is_allowed = check_access(user_role, classification)

            if is_allowed:
                allowed_docs.append(doc_text)
                allowed_ids.append(doc_id)
                print(f"  [🔓 ERLAUBT] ID: {doc_id} ({classification})")
            else:
                blocked_docs_count += 1
                print(f"  [🔒 BLOCKIERT] ID: {doc_id} ({classification})")

        # 3. CONTEXT & PROMPT
        if not allowed_docs:
            context_text = "Keine relevanten Informationen in den freigegebenen Dokumenten gefunden."
        else:
            context_text = "\n\n".join(allowed_docs)

        system_prompt = (
            f"Du bist ein hilfreicher Assistent für das Unternehmen. "
            f"Deine Rolle ist: {user_role}. "
            f"Antworte NUR basierend auf dem folgenden Kontext. "
            f"Wenn der Kontext die Antwort nicht enthält, sage 'Das weiß ich nicht'.\n\n"
            f"KONTEXT:\n{context_text}"
        )

        # 4. LLM GENERATION
        response = self.openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
        )

        answer = response.choices[0].message.content
        
        end_time = time.time()
        duration = end_time - start_time # Dauer berechnen

        # 5. LOGGING (NEU)
        try:
            log_request(
                user_role=user_role,
                query=query,
                response_text=answer,
                allowed_docs=allowed_ids,
                blocked_count=blocked_docs_count,
                latency_seconds=duration
            )
        except Exception as e:
            print(f"Warnung: Logging fehlgeschlagen: {e}")
        
        return {
            "answer": answer,
            "allowed_docs": allowed_docs,
            "blocked_count": blocked_docs_count
        }