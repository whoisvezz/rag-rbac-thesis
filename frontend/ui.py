import streamlit as st
import sys
import os

# --- CLOUD FIX START (Wichtig für Streamlit Cloud!) ---
# ChromaDB braucht ein neueres SQLite als auf manchen Servern installiert ist.
# Dieser Trick tauscht das System-SQLite gegen das installierte pysqlite3-binary aus.
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass # Lokal auf dem Mac passiert nichts, da ist alles ok.
# --- CLOUD FIX ENDE ---

# Damit wir Module aus dem Hauptverzeichnis importieren können
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.pipeline import RbacRagPipeline

# --- Konfiguration der Seite ---
st.set_page_config(page_title="RAG RBAC Prototyp", layout="wide")

# --- Initialisierung (Caching) ---
@st.cache_resource
def get_pipeline():
    return RbacRagPipeline()

try:
    pipeline = get_pipeline()
except Exception as e:
    st.error(f"Fehler beim Starten der Pipeline: {e}")
    st.stop()

# --- Session State ---
if "role" not in st.session_state:
    st.session_state["role"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ==========================================
# SEITENLEISTE (Admin & Download)
# ==========================================
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    if st.session_state["role"]:
        st.info(f"Aktive Rolle: **{st.session_state['role']}**")
        if st.button("Logout / Rolle wechseln"):
            st.session_state["role"] = None
            st.session_state["messages"] = []
            st.rerun()
    
    st.markdown("---")
    st.subheader("Daten-Export")
    
    # --- DOWNLOAD BUTTON ---
    log_file_path = "audit_log.jsonl"
    if os.path.exists(log_file_path):
        with open(log_file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
        
        st.download_button(
            label="📥 Audit-Log herunterladen",
            data=file_content,
            file_name="audit_log.jsonl",
            mime="application/json"
        )
    else:
        st.caption("Noch keine Log-Daten vorhanden.")

# ==========================================
# SCREEN 1: ROLLENAUSWAHL
# ==========================================
if st.session_state["role"] is None:
    st.title("RAG Prototyp: Unternehmens-Chatbot")
    st.markdown("### Bitte wählen Sie Ihre Rolle für diese Sitzung")
    
    st.warning("Ihre Mission:")
    st.markdown("""
    Versuchen Sie, folgende **geheime Informationen** herauszufinden:
    1. Welchen **Wettbewerber** wollen wir kaufen?
    2. Welcher **Standort** soll geschlossen werden?
    
    *Wechseln Sie zwischen den Rollen, um zu sehen, wer diese Infos erhält.*
    """)

    role_selection = st.selectbox(
        "Rolle wählen:",
        ["Mitarbeiter", "Vorgesetzter", "Geschaeftsfuehrung"]
    )

    if st.button("Session starten"):
        st.session_state["role"] = role_selection
        st.success(f"Eingeloggt als {role_selection}")
        st.rerun()

# ==========================================
# SCREEN 2: CHAT INTERFACE
# ==========================================
else:
    st.title("💬 Unternehmens-Chat")

    # Chatverlauf anzeigen
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "debug_info" in msg:
                with st.expander("Details zur Verarbeitung"):
                    st.text(msg["debug_info"])

    # Eingabe
    if prompt := st.chat_input("Stellen Sie Ihre Frage..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["messages"].append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Prüfe Berechtigungen und durchsuche Dokumente..."):
                result = pipeline.ask(user_role=st.session_state["role"], query=prompt)
                
                response_text = result["answer"]
                
                debug_text = f"Gefundene Dokumente: {len(result['allowed_docs']) + result['blocked_count']}\n"
                debug_text += f"Davon ERLAUBT: {len(result['allowed_docs'])}\n"
                debug_text += f"Davon BLOCKIERT: {result['blocked_count']} (Sicherheitsfilter aktiv)"

                st.markdown(response_text)
                with st.expander("Details zur Verarbeitung anzeigen"):
                    st.text(debug_text)

        st.session_state["messages"].append({
            "role": "assistant", 
            "content": response_text,
            "debug_info": debug_text
        })