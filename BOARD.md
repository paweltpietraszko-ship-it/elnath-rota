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
| ROTA-RARE-WEEKLY-SLOT-PINNED | Architekt | CC | — (weryfikacja findingu, bez implementacji) | `arch/FINDING_2026-09-21_RARE_WEEKLY_SLOT_PINNED_TO_ONE_EMPLOYEE.md` | READY_FOR_CODEX | **PRECHECK ARCHITEKTA: diagnoza dla Bolf JESZCZE NIEUDOWODNIONA; bez zmiany seed, globalnych wag ani dodawania historii.** Finding opisuje dwa RÓŻNE przypadki: w repro jest JEDNA sobota na MIESIĄC i rotacja między miesiącami; realny objaw zgłoszony przez OWNERA brzmi „jeden pracownik pracuje WSZYSTKIE soboty, drugi żadną” — może chodzić o 4–5 sobót W JEDNYM miesiącu. Dla 4–5 sobót istniejące `add_weekend_fairness` już powinno odróżniać nierówny przydział od równomiernego, jeśli nie blokują go pozostałe HARD/SOFT/cele. Jedna sobota miesięcznie jest z definicji niepodzielna, więc 6-miesięczne syntetyczne repro dowodzi powtarzalnego tie-breaku w tym uproszczeniu, NIE przyczyny rzeczywistego Bolf. **CC: skoryguj finding i najpierw wykonaj read-only odtworzenie faktycznego układu Bolf na tym samym snapshotcie wejść:** liczba sobotnich D w miesiącu, wszystkie wymagane demandy/role/eligibility pracowników, inne dyżury, targety, weekend hours, historia fixed i status/gap. Porównaj faktyczny PLAN z izolowanym kontrwariantem rozdzielającym soboty między dwóch pracowników: czy HARD-feasible, czy ich suma/cel i wszystkie inne SOFT jednakowe, a jeśli nie — dokładnie który składnik je różnicuje. Oddziel problem nierówności W MIESIĄCU od rotacji MIĘDZY MIESIĄCAMI; jeżeli rzeczywiście tylko jedna rzadko występująca zmiana miesięcznie, sprawdź istniejące historyczne mechanizmy (`holiday_history` dotyczy świąt, nie wszystkich sobót) i przedstaw najmniejszy wariant oraz jawne ograniczenie jego gwarancji. Nie dodawaj arbitralnej randomizacji jako „gwarantowanej rotacji”; nie zmieniaj produkcji i nie zapisuj danych obiektu do repo. Wynik: krótki raport z konkretnym mechanizmem i minimalną propozycją rozwiązania faktycznego objawu, z testem reprodukującym realną liczbę sobót, przez BOARD do Architekta. Codex niedostępny: moja weryfikacja statyczna + self-tests CC nie zastąpią niezależnego audytu przed merge. |
