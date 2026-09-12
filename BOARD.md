# BOARD.md — kolejka przekazań CC ↔ Codex

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
| ROTA-T065 | CC | Architekt | — (finding, brak briefu) | `3d9600f` (finding) | OWNER_DECISION_NEEDED | **OWNER_CONFIRMED 2026-09-10 — NIE ODŁOŻONE: podjąć po ustabilizowaniu modułu Ochrona.** Pełny finding: `arch/FINDING_2026-09-03_STANDARDOWY_EMPLOYEE_CATEGORIES.md` (istniał lokalnie od 2026-09-03, dopiero teraz scommitowany — architekt nigdy wcześniej go nie widział). Sedno: `planning_regime=ORDINARY` ("Standardowy") to dziś dosłownie skopiowana logika Ochrony, bez własnej tożsamości. Realny cel: sklep żony Pawła — zmiany 5-12 i 12-19 pon-pt, 5-14 w sobotę, z TRZEMA niezależnie rotującymi warstwami załogi: kierownicy, załoga, uczniowie (czwarta, "ekipa sprzątająca", jawnie niepewna). Zweryfikowane dwuprzebiegowo (agent czytający pełne pliki + spot-check CC przez `where.py` i bezpośredni odczyt `fairness.py`/`constraints.py`): (1) dowolne godziny zmian per dzień tygodnia — JUŻ DZIAŁA, `StandardShift` ma wolne `start_time`/`end_time`, zero zmian kodu; (2) zamknięta niedziela — JUŻ DZIAŁA innym mechanizmem (brak dnia 7 w `active_weekdays`, nie przez `CalendarDay.holiday`); (3) niezależne, nie-zamienne kategorie pracowników — POTWIERDZONE BRAKUJĄCE, brak jakiegokolwiek częściowego mechanizmu w `rota/`. Mapa dotknięcia (faktyczna, nie projekt): `rota/domain.py` (wartość kategorii na `SiteMembership`), `rota/planning/shift_catalog.py` (przeniesienie kategorii z `StandardShift` do `ShiftDemand`), `rota/planning/eligibility.py` (nowa twarda brama kategorii, analogiczna do istniejących), `rota/planning/solver.py` (prawdopodobnie bez zmian strukturalnych — jedna brama eligibility może wystarczyć). Dodatkowo, z późniejszej uwagi Pawła: potrzebny NOWY WYDRUK z grupowaniem po kategorii (`schedule_export.py::_build_rows` dziś czysto alfabetyczne, jedna płaska tabela) — to osobny kawałek zakresu, nie automatycznie pokryty zmianą backendu. Skala: architektoniczna (dotyka modelu domeny, bramy eligibility i generowania katalogu — trzy pliki), ale węższa niż przebudowa solvera; nowe pola addytywne, wzorowane na istniejących (`can_work_24h`, `membership_kind`, `catalog_kind`). Otwarte, nierozstrzygnięte w findingu: czy kategoria żyje na `Employee` czy `SiteMembership`; czy "ekipa sprzątająca" wchodzi w zakres teraz; interakcja kategorii z `EXTERNAL_SUPPORT`/`can_work_24h`/`SiteRule`; dokładny układ wydruku; czy to jeden Task czy dwa (backend+solver vs. wydruk). CC nie projektuje rozwiązania — architekt przygotowuje brief, gdy Paweł da sygnał (po ustabilizowaniu Ochrony). |
