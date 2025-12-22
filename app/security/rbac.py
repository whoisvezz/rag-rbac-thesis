import os
import casbin

# Bestimmung der absoluten Pfade relativ zur aktuellen Datei.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")

MODEL_PATH = os.path.join(CONFIG_DIR, "rbac_model.conf")
POLICY_PATH = os.path.join(CONFIG_DIR, "rbac_policy.csv")

# Validierung der Konfigurationsdateien vor der Initialisierung
if not os.path.exists(MODEL_PATH) or not os.path.exists(POLICY_PATH):
    raise FileNotFoundError(
        f"Kritischer Fehler: RBAC-Konfiguration fehlt.\n"
        f"Erwartet: {MODEL_PATH} und {POLICY_PATH}"
    )

# Initialisierung des Casbin-Enforcers.
try:
    enforcer = casbin.Enforcer(MODEL_PATH, POLICY_PATH)
except Exception as e:
    raise RuntimeError(f"Fehler bei der Initialisierung des Casbin-Enforcers: {e}")

def check_access(role: str, classification: str) -> bool:
    """
    Überprüft die Zugriffsberechtigung einer Rolle auf eine bestimmte Datenklassifizierung.
    
    Diese Funktion wertet die definierten Regeln gegen die Anfrage aus. 
    Die angeforderte Aktion ist in diesem Retrieval-Kontext implizit immer "read".

    Args:
        role (str): Die Rolle des anfragenden Subjekts (z. B. 'Mitarbeiter').
        classification (str): Die Sicherheitsklassifizierung des Objekts (z. B. 'secret').

    Returns:
        bool: True, wenn der Zugriff gestattet ist, andernfalls False.
    """
    
    # Implementierung des 'Fail-Secure' Prinzips (Default Deny):
    if not classification:
        return False
        
    # Durchsetzung der Richtlinie (Enforcement)
    # Parameter: (Subjekt, Objekt, Aktion)
    decision = enforcer.enforce(role, classification, "read")
    
    return decision

# --- Integrations-Test (Ausführung bei direktem Aufruf) ---
if __name__ == "__main__":
    print(f"Lade Sicherheitsrichtlinien aus: {POLICY_PATH}")
    
    # Definition von Testfällen zur Verifizierung der Korrektheit der Policy.
    # Format: (Rolle, Klassifizierung, Erwartetes Ergebnis)
    test_cases = [
        ("Mitarbeiter", "public", True),
        ("Mitarbeiter", "internal", True),
        ("Mitarbeiter", "secret", False),       # Negativ-Test: Zugriffsschutz
        ("Vorgesetzter", "confidential", True),
        ("Vorgesetzter", "secret", False),      # Negativ-Test: Hierarchische Abgrenzung
        ("Geschäftsführung", "secret", True),   # Positiv-Test: Vollzugriff
        ("Geschäftsführung", "unknown", False)  # Robustheits-Test: Unbekannte Label
    ]

    print("\n--- Start RBAC Validierung ---")
    all_tests_passed = True
    
    for role, doc_class, expected in test_cases:
        result = check_access(role, doc_class)
        
        # Visuelles Feedback
        status_icon = "✅" if result == expected else "❌ FEHLER"
        if result != expected:
            all_tests_passed = False
            
        print(f"Rolle: {role:<18} | Dok: {doc_class:<12} | Erwartet: {str(expected):<5} -> Ist: {str(result):<5} {status_icon}")

    if all_tests_passed:
        print("\n Alle Sicherheits-Checks erfolgreich verifiziert.")
    else:
        print("\n Warnung: Es traten Abweichungen in der Policy-Prüfung auf.")