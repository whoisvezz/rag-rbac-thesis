import json
import os
from datetime import datetime
from typing import List, Union, Dict, Any
import dotenv

# Laden der Umgebungsvariablen für Konfigurationsparameter
dotenv.load_dotenv()

# Definition des Pfades zur Log-Datei. Standardwert ist 'audit_log.jsonl'.
LOG_FILE = os.getenv("LOG_FILE", "audit_log.jsonl")

def log_request(
    user_role: str, 
    query: str, 
    response_text: str, 
    allowed_docs: List[Union[Dict[str, Any], str]], 
    blocked_count: int, 
    latency_seconds: float
) -> None:
    """
    Dokumentiert eine Benutzerinteraktion im Audit-Log für spätere Analysen.

    Args:
        user_role (str): Die Rolle des Benutzers (z. B. 'Mitarbeiter', 'Geschäftsführung').
        query (str): Die ursprüngliche Eingabeaufforderung des Benutzers.
        response_text (str): Die vom System generierte Antwort.
        allowed_docs (List): Liste der Dokumente, die den RBAC-Filter passiert haben.
        blocked_count (int): Anzahl der Dokumente, die durch den Enforcer blockiert wurden.
        latency_seconds (float): Gemessene Verarbeitungszeit der Anfrage in Sekunden.
    """
    
    # Extraktion der Dokumenten-IDs für die Nachvollziehbarkeit, welche Informationen
    # in den Kontext eingeflossen sind. Es wird geprüft, ob es sich um Dokumenten-Objekte
    # oder reine ID-Strings handelt.
    allowed_doc_ids = []
    for doc in allowed_docs:
        if isinstance(doc, dict):
            allowed_doc_ids.append(doc.get("id", "unknown_id"))
        else:
            allowed_doc_ids.append(str(doc))

    # Aufbau des Log-Eintrags als Dictionary
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": user_role,
        "query": query,
        # begrenzt auf 100 Zeichen zur Reduktion der Log-Größe.
        "response_preview": response_text[:100] + "..." if response_text else "",
        "metrics": {
            "allowed_docs_count": len(allowed_docs),
            "blocked_docs_count": blocked_count,
            "latency_seconds": round(latency_seconds, 3)  # Rundung auf 3 Dezimalstellen für Millisekunden-Genauigkeit
        },
        "allowed_doc_ids": allowed_doc_ids
    }
    
    # Persistierung des Eintrags im JSONL-Format (JSON Lines).
    # Der Modus 'a' (append) stellt sicher, dass bestehende Logs nicht überschrieben werden.
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        # Ausgabe einer Bestätigung auf der Konsole (optional für Debugging)
        print(f"📝 Audit-Log aktualisiert: {LOG_FILE}")
        
    except IOError as e:
        print(f"❌ Fehler beim Schreiben des Audit-Logs: {e}")