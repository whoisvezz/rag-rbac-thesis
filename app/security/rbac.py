import casbin
import os

# Pfade zu den Konfigurationsdateien ermitteln
# Wir nutzen absolute Pfade relativ zu dieser Datei, damit es von überall ausführbar ist
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")

MODEL_PATH = os.path.join(CONFIG_DIR, "rbac_model.conf")
POLICY_PATH = os.path.join(CONFIG_DIR, "rbac_policy.csv")

# Den Enforcer einmalig global initialisieren (spart Zeit beim Laden)
enforcer = casbin.Enforcer(MODEL_PATH, POLICY_PATH)

def check_access(role: str, classification: str) -> bool:
    """
    Prüft, ob eine Rolle auf eine Klassifizierung zugreifen darf.
    Aktion ist immer implizit "read".
    """
    if not classification:
        # Falls ein Dokument keine Klassifizierung hat, blocken wir sicherheitshalber (Fail-Safe)
        return False
        
    decision = enforcer.enforce(role, classification, "read")
    return decision

# --- Kleiner Testbereich, wenn man die Datei direkt ausführt ---
if __name__ == "__main__":
    print(f"Lade Regeln aus: {POLICY_PATH}")
    
    # Testfälle aus der Masterarbeit
    tests = [
        ("Mitarbeiter", "public", True),
        ("Mitarbeiter", "secret", False), # Das hier ist der wichtigste Test!
        ("Vorgesetzter", "confidential", True),
        ("Vorgesetzter", "secret", False),
        ("Geschaeftsfuehrung", "secret", True)
    ]

    print("\n--- Starte RBAC Tests ---")
    all_passed = True
    for role, doc_class, expected in tests:
        result = check_access(role, doc_class)
        status = "✅" if result == expected else "❌ FEHLER"
        if result != expected: all_passed = False
        print(f"Rolle: {role:18} | Dok: {doc_class:12} | Erwartet: {expected} -> Ist: {result} {status}")

    if all_passed:
        print("\n✅ Alle Sicherheits-Checks bestanden!")
    else:
        print("\n❌ Es gab Fehler in der Policy.")