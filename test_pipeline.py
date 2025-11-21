from app.rag.pipeline import RbacRagPipeline

def run_test():
    # Pipeline initialisieren
    pipeline = RbacRagPipeline()
    
    # Die kritische Frage, die auf das "Secret"-Dokument abzielt
    query = "Was plant die Geschäftsführung für 2025 und gibt es Übernahmen?"

    # Szeanrio A: Der normale Mitarbeiter
    print("\n========================================")
    print("SZENARIO A: Mitarbeiter fragt")
    print("========================================")
    result_mitarbeiter = pipeline.ask(user_role="Mitarbeiter", query=query)
    print(f"\n🤖 ANTWORT AN MITARBEITER:\n{result_mitarbeiter['answer']}")

    # Szenario B: Der Chef
    print("\n========================================")
    print("SZENARIO B: Geschäftsführung fragt")
    print("========================================")
    result_boss = pipeline.ask(user_role="Geschaeftsfuehrung", query=query)
    print(f"\n🤖 ANTWORT AN CHEF:\n{result_boss['answer']}")

if __name__ == "__main__":
    run_test()