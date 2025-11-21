import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import dotenv

# Konfiguration
LOG_FILE = "audit_log.jsonl"
OUTPUT_IMAGE = "evaluation_chart.png"

def load_data():
    """Liest das Audit-Log und wandelt es in einen Pandas DataFrame um."""
    if not os.path.exists(LOG_FILE):
        print(f"❌ Fehler: Datei '{LOG_FILE}' nicht gefunden. Bitte erst Chat-Anfragen stellen!")
        return None

    data = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                # Wir flachen die verschachtelte Struktur etwas ab für die Tabelle
                row = {
                    "timestamp": entry["timestamp"],
                    "role": entry["role"],
                    "query": entry["query"],
                    "allowed": entry["metrics"]["allowed_docs_count"],
                    "blocked": entry["metrics"]["blocked_docs_count"],
                    "latency": entry["metrics"]["latency_seconds"]
                }
                data.append(row)
            except json.JSONDecodeError:
                continue # Defekte Zeilen überspringen
    
    return pd.DataFrame(data)

def analyze_and_plot(df):
    """Führt die statistische Auswertung durch und erstellt Diagramme."""
    
    print("\n=== 📊 Quantitative Auswertung für Masterarbeit ===")
    print(f"Anzahl der ausgewerteten Anfragen: {len(df)}")

    # 1. Gruppierung nach Rolle (Das Herzstück der Auswertung)
    # Wir berechnen den Durchschnitt (mean) für allowed/blocked/latency
    grouped = df.groupby("role")[["allowed", "blocked", "latency"]].mean()
    
    print("\n--- Durchschnittswerte pro Rolle ---")
    print(grouped.round(2))

    # 2. Visualisierung erstellen
    # Wir erstellen ein Balkendiagramm: Zugriff vs. Blockiert pro Rolle
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Plot 1: Sicherheit (Dokumente)
    # Wir plotten 'allowed' und 'blocked' nebeneinander
    grouped[["allowed", "blocked"]].plot(kind="bar", ax=ax1, color=["#4CAF50", "#F44336"])
    ax1.set_title("Durchschnittliche Dokumenten-Zugriffe pro Anfrage")
    ax1.set_ylabel("Anzahl Dokumente")
    ax1.set_xlabel("Rolle")
    ax1.legend(["Erlaubt (Allowed)", "Blockiert (Blocked)"])
    ax1.grid(axis='y', linestyle='--', alpha=0.7)

    # Plot 2: Performance (Latenz)
    grouped["latency"].plot(kind="bar", ax=ax2, color="#2196F3")
    ax2.set_title("Durchschnittliche Latenz (Performance)")
    ax2.set_ylabel("Sekunden")
    ax2.set_xlabel("Rolle")
    ax2.grid(axis='y', linestyle='--', alpha=0.7)

    # Layout optimieren und speichern
    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE)
    print(f"\n✅ Diagramm gespeichert als: {OUTPUT_IMAGE}")
    print("Du kannst dieses Bild direkt in deine Arbeit einfügen.")

if __name__ == "__main__":
    df = load_data()
    if df is not None and not df.empty:
        analyze_and_plot(df)
    elif df is not None:
        print("Das Log ist noch leer. Bitte nutze erst die App (frontend/ui.py)!")
        