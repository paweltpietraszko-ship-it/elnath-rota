# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalzem pracy; ten plik tylko rejestruje
przekazanie, żeby nie trzeba było ręcznie przeklejać wiadomości między CC a
Codexem.

Statusy (dokładnie cztery, nic więcej):

- `READY_FOR_CODEX` — CC skończył, czeka na audyt.
- `CODEX_IN_PROGRESS` — Codex audytuje.
- `CODEX_REPORTED` — raport gotowy pod wskazaną ścieżką.
- `OWNER_DECISION_NEEDED` — audyt utknął na decyzji właściciela.

Nowy wiersz dopisuje autor przekazania; zmianę statusu na kolejny etap
wpisuje ten, kto ten etap kończy. Zamknięty wiersz (merge/decyzja, ostatni
status rozstrzygnięty) usuwa z tego pliku ten, kto go zamyka — pełna
historia i tak zostaje w `git log -p BOARD.md`, więc nic nie ginie, tylko
plik nie rośnie w nieskończoność (2026-08-29, OWNER_CORRECTED: wcześniejsza
wersja tej reguły mówiła "nie kasować wierszy" — celowo zmienione).

| ID | Autor | Odbiorca | Branch | Exact SHA | Status | Wiadomość |
|---|---|---|---|---|---|---|
| ROTA-OCHRONA-EQUITY-SURGICAL-FIX | CC | Architekt | `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX` | fix `b68c615` (odpowiedź na static audit `7503759`) | READY_FOR_CODEX | **Oba problemy ze statycznego audytu naprawione, na osobnym exact SHA `b68c615`.** **Problem A (realny błąd, nie tylko brak dowodu):** owner potwierdził wprost, że "zaproponowanie koordynatorowi zewnętrznego wsparcia jest możliwe gdy wszystkie inne możliwości polegną" — priorytet miał być odwrotny niż napisałem. Poprawka: `dominant_weight` (preferencja LOCAL nad EXTERNAL) jest teraz SZCZYTEM hierarchii OCHRONA, liczony żeby ściśle przewyższać sufit's WORST-CASE SUMĘ (`ceiling_weight * MAX_MONTHLY_HOURS * liczba_osob_z_targetem`), nie jeden jego składnik — solver nigdy nie użyje EXTERNAL_SUPPORT tylko po to, by chronić czyjś sufit. Nowy test dowodowy: 1 lokalny pracownik z sufitem 12h, 2 zmiany (24h), realna alternatywa EXTERNAL_SUPPORT — solver musi wybrać przekroczenie sufitu (24h), zero godzin dla EXTERNAL. **Problem B:** dodany `tests/test_ochrona_equity_surgical_fix.py`, 4 testy na gołym solverze (bez DB): (1) absencja/delegacja bez wpisanego targetu — dokładnie oryginalny błąd T041/FF, bezpośrednio strzeżony; (2) mieszany wektor — sufit jako górna granica, nigdy podłoga; (3) REPLAN z fixed hours — dobrane liczby tak, żeby błędne i poprawne zachowanie dawały RÓŻNY wynik (rozstrzał 0 vs 24h), nie przypadkową zbieżność; (4) dowód z problemu A. **Dodatkowo:** poprawiony tekst ostrzeżenia dla OCHRONA bez targetu — już nie sugeruje blokady, informuje że planowanie działa, ale sufit nie będzie egzekwowany bez wpisanego limitu; ORDINARY bez zmian. Samodzielna weryfikacja: 678 testów (674+4 nowe), te same 15 pre-existing failures co czysty baseline, zero nowych regresji, ruff czysty; Royal i drugi obiekt OCHRONA ponownie sprawdzone na żywych danych — bez zmian wyników po przeważeniu. Proszę o ponowny przegląd na SHA `b68c615`; merge nadal wyłącznie na decyzję OWNERA. |
