import streamlit as st
import sys
import os

# Damit wir Module aus dem Hauptverzeichnis importieren können
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.pipeline import RbacRagPipeline

# --- Konfiguration der Seite ---
st.set_page_config(page_title="RAG RBAC Prototyp", layout="wide")

# --- Initialisierung (Caching) ---
# Wir laden die Pipeline nur einmal, nicht bei jedem Klick neu.
@st.cache_resource
def get_pipeline():
    return RbacRagPipeline()

pipeline = get_pipeline()

# --- Session State (Gedächtnis der App) ---
if "role" not in st.session_state:
    st.session_state["role"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ==========================================
# SCREEN 1: ROLLENAUSWAHL
# ==========================================
if st.session_state["role"] is None:
    st.title("🔐 RAG Sicherheits-Prototyp")
    st.markdown("### Bitte wählen Sie Ihre Rolle für diese Sitzung")

    # --- NEUER TEIL START ---
    st.warning("🎯 Ihre Mission (Capture the Flag):")
    st.markdown("""
    Versuchen Sie, folgende **geheime Informationen** herauszufinden:
    1. Welchen **Wettbewerber** wollen wir kaufen?
    2. Welcher **Standort** soll geschlossen werden?
    
    *Wechseln Sie zwischen den Rollen, um zu sehen, wer diese Infos erhält.*
    """)
    # --- NEUER TEIL ENDE ---
    #st.info("Ziel des Tests: Versuchen Sie, Informationen über die 'Strategische Finanzplanung' zu erhalten.")

    # Auswahlbox
    role_selection = st.selectbox(
        "Rolle wählen:",
        ["Mitarbeiter", "Vorgesetzter", "Geschaeftsfuehrung"]
    )

    if st.button("Session starten"):
        st.session_state["role"] = role_selection
        st.success(f"Eingeloggt als {role_selection}")
        st.rerun() # Seite neu laden, um zum Chat zu wechseln

# ==========================================
# SCREEN 2: CHAT INTERFACE
# ==========================================
else:
    # Seitenleiste mit Infos
    with st.sidebar:
        st.header(f"👤 Rolle: {st.session_state['role']}")
        if st.button("Logout / Neustart"):
            st.session_state["role"] = None
            st.session_state["messages"] = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("**Debug Info:**")
        st.caption("Hier sehen wir später Log-Details.")

    st.title("💬 Unternehmens-Chat")

    # 1. Chatverlauf anzeigen
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Falls wir Debug-Infos zu geblockten Docs gespeichert haben:
            if "debug_info" in msg:
                with st.expander("Details zur Verarbeitung"):
                    st.text(msg["debug_info"])

    # 2. Eingabefeld für neue Fragen
    if prompt := st.chat_input("Stellen Sie Ihre Frage..."):
        # Frage sofort anzeigen
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["messages"].append({"role": "user", "content": prompt})

        # Antwort generieren
        with st.chat_message("assistant"):
            with st.spinner("Prüfe Berechtigungen und durchsuche Dokumente..."):
                # Aufruf der Pipeline
                result = pipeline.ask(user_role=st.session_state["role"], query=prompt)
                
                response_text = result["answer"]
                
                # Debug-Text zusammenbauen (für die UI-Anzeige)
                debug_text = f"Gefundene Dokumente: {len(result['allowed_docs']) + result['blocked_count']}\n"
                debug_text += f"Davon ERLAUBT: {len(result['allowed_docs'])}\n"
                debug_text += f"Davon BLOCKIERT: {result['blocked_count']} (Sicherheitsfilter aktiv)"

                st.markdown(response_text)
                with st.expander("Details zur Verarbeitung anzeigen"):
                    st.text(debug_text)

        # Antwort im Verlauf speichern
        st.session_state["messages"].append({
            "role": "assistant", 
            "content": response_text,
            "debug_info": debug_text
        })