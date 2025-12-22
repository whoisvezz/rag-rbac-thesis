import streamlit as st
import sys
import os

# --- SYSTEM-KOMPATIBILITÄT (Cloud Deployment Fix) ---
# Streamlit Cloud und einige Linux-Container verwenden veraltete SQLite-Versionen,
# die nicht mit ChromaDB kompatibel sind. Dieser Patch erzwingt die Nutzung
# der neueren 'pysqlite3'-Bibliothek, falls notwendig.
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass 

# Hinzufügen des Projekt-Root-Verzeichnisses zum Python-Pfad,
# um Module wie 'app.rag.pipeline' importieren zu können.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.pipeline import RbacRagPipeline

# --- KONFIGURATION DER BENUTZEROBERFLÄCHE ---
st.set_page_config(
    page_title="RAG RBAC Prototyp",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mapping: Anzeige im UI -> Technischer Wert für Backend (muss mit rbac_policy.csv übereinstimmen)
ROLE_MAPPING = {
    "Mitarbeiter": "Mitarbeiter",
    "Vorgesetzter": "Vorgesetzter",
    "Geschäftsführung": "Geschaeftsfuehrung" # Mapping auf ASCII für Casbin
}

# --- INITIALISIERUNG (Singleton Pattern via Caching) ---
@st.cache_resource
def get_pipeline():
    """
    Initialisiert die RAG-Pipeline einmalig und hält sie im Speicher (Cache).
    Dies verhindert das zeitaufwendige Neuladen der Vektordatenbank bei jeder Interaktion.
    """
    return RbacRagPipeline()

try:
    pipeline = get_pipeline()
except Exception as e:
    st.error(f"Kritischer Systemfehler: Pipeline konnte nicht gestartet werden.\nDetails: {e}")
    st.stop()

# --- SESSION STATE MANAGEMENT ---
# Speicherung des Zustands über Re-Runs hinweg (Rolle, Chat-Historie)
if "role" not in st.session_state:
    st.session_state["role"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ==========================================
# SEITENLEISTE (Steuerung & Datenexport)
# ==========================================
with st.sidebar:
    st.header("⚙️ Systemsteuerung")
    
    # Anzeige des aktuellen Status
    if st.session_state["role"]:
        # Rückwärts-Suche für schönen Anzeigenamen
        display_name = next((k for k, v in ROLE_MAPPING.items() if v == st.session_state["role"]), st.session_state["role"])
        st.info(f"Angemeldet als:\n**{display_name}**")
        
        if st.button("Sitzung beenden (Logout)", type="secondary"):
            st.session_state["role"] = None
            st.session_state["messages"] = []
            st.rerun()
    
    st.markdown("---")
    st.subheader("Forschungsdaten")
    
    # Download-Funktionalität für die Audit-Logs
    log_file_path = os.getenv("LOG_FILE", "audit_log.jsonl")
    
    if os.path.exists(log_file_path):
        with open(log_file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
        
        st.download_button(
            label="📥 Audit-Log exportieren (.jsonl)",
            data=file_content,
            file_name="audit_log.jsonl",
            mime="application/json",
            help="Lädt die gesammelten Interaktionsdaten für die quantitative Auswertung herunter."
        )
    else:
        st.caption("Keine Protokolldaten verfügbar.")

# ==========================================
# SCREEN 1: AUTHENTIFIZIERUNG / ROLLENWAHL
# ==========================================
if st.session_state["role"] is None:
    st.title("RAG-System mit Zugriffskontrolle")
    st.markdown("### Prototyp zur Evaluation von RBAC in LLM-Architekturen")
    
    st.info(
        "**Instruktionen für die Testperson:**\n\n"
        "Bitte wählen Sie eine Rolle und versuchen Sie, durch gezielte Fragen an das System "
        "Informationen zu erhalten. Ziel ist die Verifikation der Informationssperren.\n\n"
        "**Fokus-Szenarien:**\n"
        "1. Geplante Unternehmensübernahmen (M&A)\n"
        "2. Standortschließungen und Restrukturierungen"
    )

    # Auswahlbox mit den Schlüsseln aus dem Mapping (schöne Namen)
    selected_display_name = st.selectbox(
        "Bitte wählen Sie Ihre Rolle für dieses Szenario:",
        list(ROLE_MAPPING.keys())
    )

    if st.button("Simulation starten", type="primary"):
        # Speichern des technischen Werts (z.B. 'Geschaeftsfuehrung')
        st.session_state["role"] = ROLE_MAPPING[selected_display_name]
        st.rerun()

# ==========================================
# SCREEN 2: INTERAKTIONS-INTERFACE (Chat)
# ==========================================
else:
    st.title("💬 Unternehmens-Chatbot")
    # Anzeige der aktuellen Rolle im Titel zur Orientierung
    # display_name wiederholen
    current_display = next((k for k, v in ROLE_MAPPING.items() if v == st.session_state["role"]), "Unbekannt")
    st.caption(f"Kontext: Sie interagieren in der Rolle '{current_display}'.")

    # 1. Historie rendern
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Falls technische Metadaten vorhanden sind, diese in einem Expander anzeigen
            if "debug_info" in msg:
                with st.expander("System-Interna (Traceability)"):
                    st.text(msg["debug_info"])

    # 2. Neue Eingabe verarbeiten
    if prompt := st.chat_input("Geben Sie Ihre Suchanfrage ein..."):
        # User-Nachricht anzeigen
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["messages"].append({"role": "user", "content": prompt})

        # Antwort generieren
        with st.chat_message("assistant"):
            with st.spinner("Analyse der Zugriffsberechtigungen und Generierung..."):
                try:
                    # Aufruf der Pipeline-Logik
                    result = pipeline.ask(
                        user_role=st.session_state["role"], 
                        query=prompt
                    )
                    
                    response_text = result["answer"]
                    
                    # Aufbereitung der Debug-Informationen für die Transparenz
                    # Dies hilft bei der qualitativen Analyse des Tests
                    blocked = result['blocked_count']
                    allowed = len(result['allowed_docs'])
                    total = blocked + allowed
                    
                    debug_info = (
                        f"Latenz: {result.get('latency', 0):.2f}s\n"
                        f"Dokumente (Retrieval): {total}\n"
                        f"Zugriff erlaubt: {allowed}\n"
                        f"Durch RBAC gefiltert: {blocked}"
                    )

                    st.markdown(response_text)
                    
                    with st.expander("System-Interna (Traceability)"):
                        st.text(debug_info)
                        if blocked > 0:
                            st.warning(f"Hinweis: {blocked} Dokumente wurden aufgrund fehlender Berechtigungen ausgeblendet.")

                    # Antwort zur Historie hinzufügen
                    st.session_state["messages"].append({
                        "role": "assistant", 
                        "content": response_text,
                        "debug_info": debug_info
                    })
                    
                except Exception as e:
                    st.error(f"Fehler bei der Verarbeitung: {e}")