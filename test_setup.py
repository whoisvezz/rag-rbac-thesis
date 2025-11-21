import openai
import chromadb
import casbin
import streamlit
import dotenv
import os

# Lade Umgebungsvariablen
dotenv.load_dotenv()

print("✅ Alle Bibliotheken wurden gefunden.")
if os.getenv("OPENAI_API_KEY"):
    print("✅ API Key wurde geladen.")
else:
    print("❌ WARNUNG: Kein API Key in .env gefunden.")

print("Bereit für Schritt 2!")
