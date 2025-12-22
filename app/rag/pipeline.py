import os
import time
import dotenv
import chromadb
from typing import List, Dict, Any, Union
from openai import OpenAI

# Eigene Module
from app.security.rbac import check_access
from app.logging.audit import log_request

# Initialisierung der Umgebungsvariablen
dotenv.load_dotenv()

# Konfigurationsparameter
CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chromadb")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4-turbo")
COLLECTION_NAME = "company_kb"
RETRIEVAL_COUNT = 5  # Anzahl der abzurufenden Dokumente (Top-K)

class RbacRagPipeline:
    """
    Implementiert die Retrieval-Augmented Generation (RAG) Pipeline mit integrierter
    rollenbasierter Zugriffskontrolle (RBAC).
    
    Diese Klasse orchestriert den Prozess von der Einbettung der Anfrage über
    die Dokumentensuche und Filterung bis hin zur Generierung der Antwort und
    dem Logging der Transaktion.
    """

    def __init__(self):
        """
        Initialisiert die Clients für die Vektordatenbank (ChromaDB) und
        das Sprachmodell (OpenAI).
        """
        try:
            self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
            self.collection = self.chroma_client.get_collection(name=COLLECTION_NAME)
            self.openai_client = OpenAI()
            print(f"Pipeline initialisiert. Collection: '{COLLECTION_NAME}'")
        except Exception as e:
            print(f"Kritischer Fehler bei der Initialisierung der Pipeline: {e}")
            raise

    def get_embedding(self, text: str) -> List[float]:
        """
        Generiert eine Vektoreinbettung (Embedding) für den übergebenen Text.

        Args:
            text (str): Der Eingabetext.

        Returns:
            List[float]: Der Vektor, der den Text repräsentiert.
        """
        # Bereinigung von Zeilenumbrüchen für bessere Embedding-Qualität
        text = text.replace("\n", " ")
        
        response = self.openai_client.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding

    def ask(self, user_role: str, query: str) -> Dict[str, Any]:
        """
        Führt eine vollständige RAG-Abfrage unter Berücksichtigung der Benutzerrolle durch.

        Prozessschritte:
        1. Vektorisierung der Suchanfrage.
        2. Semantische Suche in der Wissensbasis (Retrieval).
        3. Anwendung des RBAC-Filters auf die Suchergebnisse (Enforcement).
        4. Konstruktion des Prompts mit nur erlaubten Kontexten.
        5. Generierung der Antwort durch das LLM.
        6. Protokollierung der Anfrage (Logging).

        Args:
            user_role (str): Die Rolle des Anfragenden (z. B. 'Mitarbeiter').
            query (str): Die natürlichsprachliche Frage.

        Returns:
            Dict[str, Any]: Enthält die generierte Antwort sowie Metadaten zur Filterung.
        """
        start_time = time.time()
        
        print(f"\n--- Start RAG-Prozess ---")
        print(f"Input: Rolle='{user_role}' | Query='{query}'")

        # --- SCHRITT 1: RETRIEVAL ---
        query_vec = self.get_embedding(query)
        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=RETRIEVAL_COUNT
        )

        allowed_docs_content = []  # Liste der Texte für das LLM
        allowed_doc_ids = []       # Liste der IDs für das Audit-Log
        blocked_docs_count = 0

        # Die ChromaDB-Ergebnisse sind verschachtelte Listen. Wir extrahieren die erste Ebene.
        if results['documents']:
            num_found = len(results['documents'][0])
            
            print(f"Retrieval: {num_found} Dokumente gefunden. Starte RBAC-Prüfung...")

            for i in range(num_found):
                doc_text = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                doc_id = results['ids'][0][i]
                
                # Extraktion der Sicherheitsklassifizierung (Default: 'internal')
                classification = metadata.get("classification", "internal")

                # --- SCHRITT 2: RBAC FILTERUNG (Enforcement Point) ---
                is_allowed = check_access(user_role, classification)

                if is_allowed:
                    allowed_docs_content.append(doc_text)
                    allowed_doc_ids.append(doc_id)
                    print(f"  Zugriff gewährt: ID={doc_id} (Class={classification})")
                else:
                    blocked_docs_count += 1
                    print(f"  Zugriff verweigert: ID={doc_id} (Class={classification})")
        else:
            print("⚠️ Keine Dokumente im Vektorraum gefunden.")

        # --- SCHRITT 3: KONTEXT-KONSTRUKTION ---
        if not allowed_docs_content:
            context_text = "Keine relevanten Informationen in den für diese Rolle freigegebenen Dokumenten gefunden."
        else:
            context_text = "\n\n".join(allowed_docs_content)

        # System-Prompt Instruktion
        system_prompt = (
            f"Du bist ein hilfreicher interner Unternehmensassistent. "
            f"Du interagierst mit einem Benutzer der Rolle: {user_role}. "
            f"Beantworte die Frage ausschließlich basierend auf dem untenstehenden Kontext. "
            f"Wenn der Kontext die Antwort nicht enthält, antworte wahrheitsgemäß mit 'Das weiß ich nicht' "
            f"oder 'Dazu liegen mir keine Informationen vor'. Erfinde keine Fakten.\n\n"
            f"--- ANFANG KONTEXT ---\n{context_text}\n--- ENDE KONTEXT ---"
        )

        # --- SCHRITT 4: ANTWORT-GENERIERUNG (LLM) ---
        chat_completion = self.openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.3 # Geringere Kreativität für faktentreue Antworten
        )

        answer = chat_completion.choices[0].message.content
        
        # Berechnung der Verarbeitungszeit
        end_time = time.time()
        process_duration = end_time - start_time

        # --- SCHRITT 5: LOGGING & AUDIT ---
        try:
            log_request(
                user_role=user_role,
                query=query,
                response_text=answer,
                allowed_docs=allowed_doc_ids, # Übergabe der IDs für Traceability
                blocked_count=blocked_docs_count,
                latency_seconds=process_duration
            )
        except Exception as e:
            # Das Logging darf den Hauptprozess nicht abbrechen, daher nur Konsolenausgabe
            print(f"⚠️ Warnung: Audit-Logging fehlgeschlagen: {e}")
        
        return {
            "answer": answer,
            "allowed_docs": allowed_docs_content,
            "blocked_count": blocked_docs_count,
            "latency": process_duration
        }