import time
import threading

# Wir importieren NUR die RateLimiter-Klasse aus deinem Handler-Skript
from riot_api_handler import RateLimiter

def worker(limiter: RateLimiter, worker_id: int):
    """
    Diese Funktion simuliert einen Worker, der versucht, API-Anfragen zu senden.
    """
    for i in range(5): # Jeder Worker versucht, 5 Anfragen zu senden
        print(f"[Worker {worker_id}] Versucht Anfrage {i+1}/5 zu senden...")
        
        start_time = time.time()
        limiter.acquire() # Hier wird auf einen freien Slot gewartet
        end_time = time.time()
        
        wait_time = end_time - start_time
        
        print(f"[Worker {worker_id}] ANFRAGE {i+1}/5 GESENDET um {time.strftime('%H:%M:%S')}. (Wartezeit: {wait_time:.2f}s)")
        
        # Simuliert eine kurze Bearbeitungszeit nach der Anfrage
        time.sleep(0.1)

def main():
    """
    Hauptfunktion zum Testen des Rate Limiters.
    """
    print("--- Starte Rate Limiter Test ---")
    
    # Test-Limits: 5 Anfragen pro 2 Sekunden UND 10 Anfragen pro 5 Sekunden
    # Das zwingt den Limiter, beide Regeln zu beachten.
    test_limits = [(5, 2), (10, 5)]
    print(f"Test-Limits konfiguriert: {test_limits}\n")
    
    # Erstelle eine Instanz des Rate Limiters
    rate_limiter = RateLimiter(test_limits)
    
    # Erstelle mehrere Threads, um gleichzeitige Anfragen zu simulieren
    # Dies testet auch die Thread-Sicherheit (den Lock) deines Limiters
    threads = []
    num_workers = 4 # 4 Worker senden gleichzeitig Anfragen (insgesamt 20)
    
    print(f"Starte {num_workers} Worker, die versuchen, insgesamt {num_workers * 5} Anfragen zu senden...\n")
    
    for i in range(num_workers):
        thread = threading.Thread(target=worker, args=(rate_limiter, i + 1))
        threads.append(thread)
        thread.start()
        
    # Warte, bis alle Threads ihre Arbeit beendet haben
    for thread in threads:
        thread.join()
        
    print("\n--- Rate Limiter Test beendet ---")

if __name__ == "__main__":
    main()