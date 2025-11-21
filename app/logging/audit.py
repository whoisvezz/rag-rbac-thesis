import json
import os
from datetime import datetime
import dotenv

dotenv.load_dotenv()

LOG_FILE = os.getenv("LOG_FILE", "audit_log.jsonl")

def log_request(user_role: str, query: str, response_text: str, 
                allowed_docs: list, blocked_count: int, latency_seconds: float):
    """
    Schreibt einen Eintrag in das Audit-Log.
    """
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": user_role,
        "query": query,
        "response_preview": response_text[:100] + "...", # Nur die ersten 100 Zeichen
        "metrics": {
            "allowed_docs_count": len(allowed_docs),
            "blocked_docs_count": blocked_count,
            "latency_seconds": round(latency_seconds, 2)
        },
        "allowed_doc_ids": [doc_id for doc_id in allowed_docs] # Wir speichern hier nur IDs, falls wir sie hätten, oder den Textanfang
    }
    
    # Anhängen an die Datei (append mode 'a')
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"📝 Log-Eintrag geschrieben: {LOG_FILE}")