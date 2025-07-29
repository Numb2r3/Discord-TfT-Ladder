# test_data_manager.py

import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Wichtig: Da unsere Funktion asynchron ist, brauchen wir diesen speziellen Test-Typ
from unittest import IsolatedAsyncioTestCase

# Die zu testende Funktion importieren
from data_manager import handle_riot_account_registration

# Importiere die Klasse, die wir fälschen wollen
from ORM_models import RiotAccount

class TestDataManager(IsolatedAsyncioTestCase):
    
    # Der @patch-Decorator fängt die Aufrufe an die echten Funktionen ab
    # und ersetzt sie durch "Mocks". Die Reihenfolge ist von unten nach oben.
    @patch('data_manager.crud.add_account_to_server')
    @patch('data_manager.api.get_account_by_riot_id') # Wir mocken die API-Funktion
    async def test_register_new_account_success(self, mock_get_account_by_riot_id, mock_add_account_to_server):
        """
        Testet den erfolgreichen Ablauf der Registrierung eines neuen Accounts.
        """
        # --- 1. Arrange (Vorbereiten) ---
        # Definiere, was die gemockten Funktionen zurückgeben sollen, wenn sie aufgerufen werden.

        # Wenn `api.get_account_by_riot_id` aufgerufen wird, soll es ein fiktives Wörterbuch zurückgeben.
        mock_get_account_by_riot_id.return_value = {
            'puuid': 'TEST_PUUID_123',
            'gameName': 'TestUser',
            'tagLine': 'EUW'
        }

        # Wir müssen auch den Return-Wert von sync_riot_account_by_riot_id fälschen.
        # Da diese Funktion ein DB-Objekt zurückgibt, erstellen wir ein gefälschtes "RiotAccount"-Objekt.
        # Wir können das mit einem weiteren Patch machen oder die Logik vereinfachen, aber für ein
        # vollständiges Beispiel patchen wir die unterliegende CRUD-Funktion.
        # Lassen Sie uns für die Einfachheit sync_riot_account_by_riot_id direkt patchen.
        
        # Korrektur: Wir sollten die Funktion mocken, die direkt in handle_riot_account_registration
        # verwendet wird. Das ist sync_riot_account_by_riot_id.
        
        # Um das Beispiel einfach zu halten, passen wir den Test an
        # und patchen sync_riot_account_by_riot_id
        pass # Dieser Pass ist nur Platzhalter, siehe den korrigierten Test unten.

# Da der obige Test komplex wird, hier eine einfachere und korrektere Version:
class TestDataManagerSimplified(IsolatedAsyncioTestCase):

    @patch('data_manager.crud.add_account_to_server', return_value='ADDED')
    @patch('data_manager.sync_riot_account_by_riot_id') # Wir mocken die ganze Sync-Funktion
    async def test_register_new_account_success_simplified(self, mock_sync_riot_account, mock_add_to_server):
        """
        Testet den erfolgreichen Ablauf der Registrierung eines neuen Accounts.
        """
        # --- 1. Arrange (Vorbereiten) ---
        # Erstelle ein gefälschtes RiotAccount-Objekt, das von der sync-Funktion zurückgegeben wird.
        fake_riot_account = MagicMock(spec=RiotAccount)
        fake_riot_account.riot_account_id = 'FAKE_RIOT_ID_456'
        fake_riot_account.game_name = 'TestUser'
        fake_riot_account.tag_line = 'EUW'
        
        # Weise den Rückgabewert dem Mock zu. Da es eine async Funktion ist, nutzen wir AsyncMock.
        mock_sync_riot_account.return_value = fake_riot_account
        
        # Der Rückgabewert von mock_add_to_server ist bereits im Decorator definiert ('ADDED').

        # --- 2. Act (Ausführen) ---
        # Rufe die eigentliche Funktion mit Testdaten auf.
        riot_account, status = await handle_riot_account_registration(
            server_id='TEST_SERVER_ID',
            game_name='TestUser',
            tag_line='EUW',
            region='euw1'
        )

        # --- 3. Assert (Überprüfen) ---
        # Stelle sicher, dass unsere Logik das Richtige getan hat.

        # Wurde die sync-Funktion genau einmal mit den richtigen Daten aufgerufen?
        mock_sync_riot_account.assert_called_once_with('TestUser', 'EUW', 'euw1')

        # Wurde die CRUD-Funktion zum Hinzufügen zum Server genau einmal aufgerufen?
        mock_add_to_server.assert_called_once_with(
            server_id='TEST_SERVER_ID', 
            riot_account_id='FAKE_RIOT_ID_456'
        )

        # Ist das Ergebnis der Funktion das, was wir erwarten?
        self.assertEqual(status, 'ADDED')
        self.assertEqual(riot_account, fake_riot_account)

# Diese Zeile erlaubt es, den Test direkt von der Kommandozeile auszuführen
if __name__ == '__main__':
    unittest.main()