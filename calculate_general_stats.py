import json
import os
import glob
import csv

# --- KONFIGURATION ---
DOCS_FILE = "data/docs/documents.json"
LOG_DIR = "raw_logs"
RBAC_FILE = "config/rbac_policy.csv"  # Pfad zur Policy-Datei anpassen!

FALLBACK_PHRASES = [
    "das weiß ich nicht",
    "dazu habe ich keine informationen",
    "ich kann diese frage nicht beantworten",
    "keine relevanten dokumente gefunden"
]

def load_doc_classifications():
    """Zählt, wie viele Dokumente es pro Klassifizierung gibt."""
    if not os.path.exists(DOCS_FILE):
        print(f"⚠️ Warnung: '{DOCS_FILE}' nicht gefunden.")
        return {}, 0

    counts = {}
    total = 0
    try:
        with open(DOCS_FILE, 'r', encoding='utf-8') as f:
            docs = json.load(f)
            total = len(docs)
            for doc in docs:
                # Wir lesen metadata.classification (z.B. 'public', 'secret')
                # Fallback: 'internal' wenn nichts gesetzt ist
                cls = doc.get('metadata', {}).get('classification', 'internal').strip().lower()
                counts[cls] = counts.get(cls, 0) + 1
    except Exception as e:
        print(f"❌ Fehler bei Docs: {e}")
    
    return counts, total

def calculate_theoretical_access(doc_counts):
    """
    Liest die RBAC-Policy und berechnet, wie viele Dokumente 
    jede Rolle theoretisch sehen darf.
    """
    if not os.path.exists(RBAC_FILE):
        return {}

    role_access = {} # Speichert: Rolle -> Set von erlaubten Klassifizierungen
    
    try:
        with open(RBAC_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                # Erwartetes Format: p, rolle, klassifizierung, read
                # Wir ignorieren Zeilen, die nicht mit 'p' starten oder Kommentar '#' sind
                if not row or row[0].strip().startswith('#'): continue
                
                if row[0].strip() == 'p':
                    role = row[1].strip()
                    allowed_cls = row[2].strip().lower()
                    
                    if role not in role_access:
                        role_access[role] = set()
                    role_access[role].add(allowed_cls)
    except Exception as e:
        print(f"❌ Fehler bei RBAC Policy: {e}")
        return {}

    # Jetzt summieren
    access_stats = {}
    for role, allowed_classes in role_access.items():
        count = 0
        for cls in allowed_classes:
            count += doc_counts.get(cls, 0)
        access_stats[role] = count
        
    return access_stats

def analyze_logs():
    """Berechnet Nutzungsstatistiken aus den Logs."""
    if not os.path.exists(LOG_DIR): return None

    stats = {
        "files_count": 0,
        "total_queries": 0,
        "fallback_count": 0
    }

    files = glob.glob(os.path.join(LOG_DIR, "*.jsonl")) + glob.glob(os.path.join(LOG_DIR, "*.json"))
    stats["files_count"] = len(files)

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    entry = json.loads(line)
                    stats["total_queries"] += 1
                    
                    response = entry.get('response_preview', entry.get('response_content', "")).lower()
                    for phrase in FALLBACK_PHRASES:
                        if phrase in response:
                            stats["fallback_count"] += 1
                            break
                except: continue
    return stats

def print_report(total_docs, doc_counts, access_stats, log_stats):
    print("\n" + "="*60)
    print("📈 ALLGEMEINE PROTOTYP-KENNZAHLEN (Descriptive Stats)")
    print("="*60)
    
    print(f"{'Metrik':<40} | {'Wert':<15}")
    print("-" * 60)
    print(f"{'Wissensbasis (Total Documents)':<40} | {total_docs}")
    print(f"{'Anzahl ausgewerteter Logs':<40} | {log_stats['files_count']}")
    print(f"{'Anzahl aller Eingaben (Queries)':<40} | {log_stats['total_queries']}")
    print("-" * 60)
    print(f"{'Fallback-Antworten („Weiß nicht“)':<40} | {log_stats['fallback_count']}")
    if log_stats['total_queries'] > 0:
        rate = log_stats['fallback_count'] / log_stats['total_queries'] * 100
        print(f"{'Fallback-Quote':<40} | {rate:.1f}%")
    
    print("\n" + "="*60)
    print("🔐 THEORETISCHER ZUGRIFFSRAUM (Information Space)")
    print("="*60)
    print("Verteilung der Dokumente nach Klassifizierung:")
    for cls, count in doc_counts.items():
        print(f"  • {cls:<15}: {count}")
    
    print("-" * 60)
    print(f"{'Rolle':<20} | {'Zugängliche Docs':<15} | {'Anteil am Wissen':<15}")
    print("-" * 60)
    
    # Sortieren für schöne Ausgabe (Geschäftsführung nach unten wenn möglich)
    sorted_roles = sorted(access_stats.items(), key=lambda x: x[1])
    
    for role, count in sorted_roles:
        share = (count / total_docs * 100) if total_docs > 0 else 0
        print(f"{role:<20} | {count:<15} | {share:.1f}%")
    print("="*60)

def main():
    # 1. Dokumente analysieren
    doc_counts, total_docs = load_doc_classifications()
    
    # 2. RBAC Policy analysieren (Wer darf was?)
    access_stats = calculate_theoretical_access(doc_counts)
    
    # 3. Logs analysieren (Was passierte wirklich?)
    log_stats = analyze_logs()
    
    if log_stats:
        print_report(total_docs, doc_counts, access_stats, log_stats)
    else:
        print("Keine Logs gefunden.")

if __name__ == "__main__":
    main()