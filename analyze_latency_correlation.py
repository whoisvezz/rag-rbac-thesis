import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import glob
import numpy as np
from scipy import stats

# --- KONFIGURATION ---
LOG_DIR = "raw_logs"
OUTPUT_DIR = "evaluation_results"

# Style für wissenschaftliche Diagramme
sns.set_theme(style="whitegrid")
plt.rcParams.update({'figure.figsize': (14, 6), 'font.size': 12})

def parse_log_entry(entry):
    """Liest die relevanten Zahlen für die Korrelationsanalyse aus."""
    metrics = entry.get('metrics', {})
    
    return {
        'n_allowed': metrics.get('allowed_docs_count', 0),
        'n_blocked': metrics.get('blocked_docs_count', 0),
        # Latenz in Sekunden
        'latency_sec': metrics.get('latency_seconds', 0.0)
    }

def load_data(directory):
    if not os.path.exists(directory):
        print(f"❌ Fehler: Ordner '{directory}' fehlt.")
        return None

    all_data = []
    files = glob.glob(os.path.join(directory, "*.jsonl")) + glob.glob(os.path.join(directory, "*.json"))
    print(f"📂 Lade {len(files)} Dateien für Latenz-Analyse...")

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            raw = json.loads(line)
                            all_data.append(parse_log_entry(raw))
                        except: continue
        except: continue
    
    if not all_data: return None
    return pd.DataFrame(all_data)

def calculate_correlations(df):
    """Berechnet den Korrelationskoeffizienten (Pearson)."""
    # Wir filtern Ausreißer (z.B. Latenz > 30 Sek), falls nötig. Hier nehmen wir alles.
    
    corr_blocked = df['n_blocked'].corr(df['latency_sec'])
    corr_allowed = df['n_allowed'].corr(df['latency_sec'])
    
    print("\n" + "="*60)
    print("📊 KORRELATIONS-ANALYSE (Pearson-Koeffizient r)")
    print("="*60)
    print(f"Wertebereich: -1 (negativ) bis +1 (positiv), 0 = kein Zshg.\n")
    
    print(f"1. Blockierte Docs vs. Latenz: r = {corr_blocked:.3f}")
    if abs(corr_blocked) < 0.1:
        print("   -> Interpretation: KEIN spürbarer Einfluss (Sicherheitscheck ist schnell).")
    elif corr_blocked > 0:
        print("   -> Interpretation: Leichter Anstieg der Zeit durch Filterung.")
        
    print("-" * 60)
    
    print(f"2. Erlaubte Docs vs. Latenz:   r = {corr_allowed:.3f}")
    if corr_allowed > 0.3:
        print("   -> Interpretation: DEUTLICHER Einfluss (Mehr Kontext = Mehr Rechenzeit für LLM).")
    else:
        print("   -> Interpretation: Geringer Einfluss.")
    print("="*60)
    
    return corr_blocked, corr_allowed

def plot_correlation(df, r_blocked, r_allowed):
    """Erstellt zwei Scatterplots nebeneinander."""
    
    fig, axes = plt.subplots(1, 2, sharey=True) # sharey=True damit man die Y-Achse vergleichen kann
    
    # Plot 1: Blockierte Docs vs Latenz
    sns.regplot(
        data=df, x='n_blocked', y='latency_sec', 
        ax=axes[0], color='#e74c3c', scatter_kws={'alpha':0.5}, line_kws={'color': 'darkred'}
    )
    axes[0].set_title(f'Einfluss RBAC-Filterung\n(Korrelation r={r_blocked:.2f})')
    axes[0].set_xlabel('Anzahl blockierter Dokumente')
    axes[0].set_ylabel('Systemlatenz (Sekunden)')
    
    # Plot 2: Erlaubte Docs vs Latenz
    sns.regplot(
        data=df, x='n_allowed', y='latency_sec', 
        ax=axes[1], color='#2ecc71', scatter_kws={'alpha':0.5}, line_kws={'color': 'darkgreen'}
    )
    axes[1].set_title(f'Einfluss Kontext-Größe\n(Korrelation r={r_allowed:.2f})')
    axes[1].set_xlabel('Anzahl erlaubter Dokumente (an LLM)')
    axes[1].set_ylabel('') # Y-Label sparen wir uns hier, da sharey
    
    plt.tight_layout()
    filename = os.path.join(OUTPUT_DIR, "fig_correlation_latency.png")
    plt.savefig(filename, dpi=300)
    print(f"\n✅ Diagramm gespeichert: {filename}")
    plt.close()

def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    df = load_data(LOG_DIR)
    if df is not None and not df.empty:
        # Metriken berechnen
        r_blocked, r_allowed = calculate_correlations(df)
        # Plotten
        plot_correlation(df, r_blocked, r_allowed)
    else:
        print("Keine Daten gefunden.")

if __name__ == "__main__":
    main()