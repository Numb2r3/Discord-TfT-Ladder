import data_manager as dm
import database_crud as crud

def test_sync_riot_account():
    """Testet die Synchronisierung eines Riot Accounts."""
    print("\n--- Test: Riot Account Synchronisieren ---")
    game_name = input("Gib den Game-Namen ein: ")
    tag_line = input("Gib die Tag-Line ein (ohne #): ")
    region = input("Gib die Region ein (z.B. euw1): ")

    if not all([game_name, tag_line, region]):
        print("Fehler: Alle Felder werden benötigt.")
        return

    print(f"Synchronisiere {game_name}#{tag_line}...")
    riot_account = dm.sync_riot_account_by_riot_id(game_name, tag_line, region)

    if riot_account:
        print("\n--- ERGEBNIS ---")
        print(f"Erfolg! Account in DB gefunden/erstellt:")
        print(f"  ID: {riot_account.riot_account_id}")
        print(f"  PUUID: {riot_account.puuid}")
        print(f"  Name: {riot_account.game_name}#{riot_account.tag_line}")
        print("----------------\n")
    else:
        print("\n--- ERGEBNIS ---")
        print("Fehler bei der Synchronisierung. Siehe Logs für Details.")
        print("----------------\n")

def test_sync_rank():
    """Testet die Synchronisierung der Ranglisten-Daten."""
    print("\n--- Test: Ranglisten-Daten Synchronisieren ---")
    puuid = input("Gib die PUUID des Riot Accounts ein, der bereits in der DB ist: ")
    
    if not puuid:
        print("Fehler: PUUID wird benötigt.")
        return

    # Hol den Account zuerst aus der DB
    riot_account = crud.get_riot_account_by_puuid(puuid)
    if not riot_account:
        print(f"Fehler: Kein Riot Account mit der PUUID {puuid} in der Datenbank gefunden.")
        print("Bitte synchronisiere den Account zuerst mit Option 1.")
        return

    print(f"Synchronisiere Rang für {riot_account.game_name}...")
    lp_history_entry = dm.sync_tft_rank_for_account(riot_account)

    if lp_history_entry:
        print("\n--- ERGEBNIS ---")
        print("Erfolg! Neuer LP-History-Eintrag erstellt:")
        print(f"  Tier: {lp_history_entry.tier} {lp_history_entry.division}")
        print(f"  LP: {lp_history_entry.league_points}")
        print(f"  Wins/Losses: {lp_history_entry.wins}/{lp_history_entry.losses}")
        print("----------------\n")
    else:
        print("\n--- ERGEBNIS ---")
        print("Fehler bei der Ranglisten-Synchronisierung. Account ist evtl. unranked oder API-Fehler.")
        print("----------------\n")


def main_menu():
    """Zeigt das Hauptmenü an und steuert den Testablauf."""
    while True:
        print("\n===== API Test-Konsole =====")
        print("1. Riot Account synchronisieren")
        print("2. TFT-Rangliste für einen Account synchronisieren")
        print("0. Beenden")
        choice = input("Deine Wahl: ")

        if choice == '1':
            test_sync_riot_account()
        elif choice == '2':
            test_sync_rank()
        elif choice == '0':
            print("Test-Konsole wird beendet.")
            break
        else:
            print("Ungültige Eingabe, bitte versuche es erneut.")

if __name__ == "__main__":
    # Bevor wir starten, stellen wir sicher, dass die DB-Tabellen existieren.
    # Du kannst hier create_db.py importieren und die Funktion aufrufen,
    # oder sicherstellen, dass du es manuell ausgeführt hast.
    print("Willkommen in der API Test-Konsole.")
    print("Stelle sicher, dass deine .env-Datei mit der GIST-URL korrekt konfiguriert ist.")
    
    main_menu()