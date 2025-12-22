import json
import csv
import os
import glob
from datetime import datetime

# --- KONFIGURATION ---
LOG_DIR = "raw_logs"
OUTPUT_FILE = "anhang_messdaten_export.csv"

def clean_text(text):
    """
    Entfernt Zeilenumbrüche und Semikolons aus Texten, 
    damit das CSV-Format nicht kaputt geht.
    """
    if not text:
        return ""
    # Zeilenumbrüche durch Leerzeichen ersetzen
    text = text.replace("\n", " ").replace("\r", "")
    # Semikolons (unser Trennzeichen) durch Kommas ersetzen
    text = text.replace(";", ",")
    return text

def export_logs():
    if not os.path.exists(LOG_DIR):
        print(f"❌ Fehler: Ordner '{LOG_DIR}' fehlt.")
        return

    # Alle Log-Dateien finden
    files = glob.glob(os.path.join(LOG_DIR, "*.jsonl")) + glob.glob(os.path.join(LOG_DIR, "*.json"))
    
    print(f"📂 Lese {len(files)} Log-Dateien aus '{LOG_DIR}'...")
    
    # CSV Datei öffnen und schreiben
    # encoding='utf-8-sig' sorgt dafür, dass Excel Umlaute korrekt anzeigt (BOM)
    with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8-sig') as csv_file:
        writer = csv.writer(csv_file, delimiter=';')
        
        # 1. Header schreiben (Spaltennamen für den Anhang)
        header = [
            "Zeitstempel",
            "Rolle",
            "Suchanfrage (Query)",
            "Antwort (Preview)",
            "Erlaubte Docs (Anzahl)",
            "Blockierte Docs (Anzahl)",
            "Latenz (Sek)",
            "Zugriff auf Doc-IDs"
        ]
        writer.writerow(header)
        
        row_count = 0
        
        # 2. Dateien durchgehen
        for filepath in files:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    
                    try:
                        data = json.loads(line)
                        
                        # --- DATEN EXTRAHIEREN ---
                        
                        # Basisdaten
                        timestamp = data.get('timestamp', '')[:19] # Kürzen auf YYYY-MM-DD HH:MM:SS
                        role = data.get('role', 'Unknown')
                        query = clean_text(data.get('query', ''))
                        
                        # Antwort bereinigen (Wichtig für CSV!)
                        # Versuche response_preview, fallback auf response_content
                        raw_response = data.get('response_preview', data.get('response_content', ''))
                        response = clean_text(raw_response)
                        
                        # Metriken (Nested Dictionary handling)
                        metrics = data.get('metrics', {})
                        allowed_count = metrics.get('allowed_docs_count', 0)
                        blocked_count = metrics.get('blocked_docs_count', 0)
                        latency = metrics.get('latency_seconds', 0.0)
                        
                        # Doc-IDs (Liste in String umwandeln: "doc_01, doc_02")
                        doc_ids_list = data.get('allowed_doc_ids', [])
                        if not doc_ids_list and 'allowed_docs' in data:
                             # Fallback für alte Logs
                             doc_ids_list = [d.get('id') for d in data['allowed_docs'] if 'id' in d]
                        
                        doc_ids_str = ", ".join(doc_ids_list)
                        
                        # --- ZEILE SCHREIBEN ---
                        row = [
                            timestamp,
                            role,
                            query,
                            response,
                            allowed_count,
                            blocked_count,
                            str(latency).replace('.', ','), # Excel mag Komma statt Punkt bei Zahlen
                            doc_ids_str
                        ]
                        
                        writer.writerow(row)
                        row_count += 1
                        
                    except json.JSONDecodeError:
                        continue
                        
    print(f"✅ Export erfolgreich!")
    print(f"📄 Datei erstellt: {OUTPUT_FILE}")
    print(f"📊 Anzahl Datensätze: {row_count}")

if __name__ == "__main__":
    export_logs()