from __future__ import annotations

REST_MIN_HOURS: int = 11
# aktualne przepisy prawa pracy (art. 132 KP)
# importowac wszedzie zamiast magic number 11

LOAD_WINDOW_DAYS: int = 7
# LOAD-01: rozmiar ruchomego okna kontroli obciazenia

if __name__ == "__main__":
    print(f"REST_MIN_HOURS = {REST_MIN_HOURS}")
    print(f"LOAD_WINDOW_DAYS = {LOAD_WINDOW_DAYS}")
