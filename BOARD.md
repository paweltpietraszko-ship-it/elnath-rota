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
| ROTA-RARE-WEEKLY-SLOT-PINNED | CC | Architekt | — (finding, nie implementacja) | `arch/FINDING_2026-09-21b_SATURDAY_CONCENTRATION_CONFIRMED_ON_REAL_BOLF.md` | OWNER_DECISION_NEEDED | **Precheck architekta wykonany, hipoteza SKORYGOWANA i POTWIERDZONA na realnym Bolf.** Regime Bolf to OCHRONA (nie ORDINARY jak w pierwszej wersji) -- realny mechanizm to `add_ochrona_hours_fairness` + `add_weekend_fairness` jako tie-break, nie `add_target_equity_fairness`. Realne dane (read-only, za zgodą Pawła, 3 niezależnie planowane miesiące, POTWIERDZONE zero absencji w styczniu bezpośrednio przez Pawła): wrzesień (4 soboty, miesiąc "parzysty") wyszedł idealnie równo 144/156h -- ale październik (5 sobót) i styczeń (5 sobót, 3 niezależne przeliczenia tego samego wejścia) za każdym razem oddały WSZYSTKIE soboty jednej osobie (różnica sumy godzin tylko ~9h, czyli matematyczne minimum przy niepodzielności zmian 12h/9h). Między trzema próbami stycznia zmieniało się KTÓRA osoba dostawała wszystkie soboty (nie stały pin) -- CP-SAT za każdym razem grupuje soboty jednej osobie zamiast je rozdzielić, mimo identycznego kosztu sumarycznego. Potwierdzone NIEZALEŻNIE też czystą syntetyczną rekonstrukcją tego samego kształtu (ten sam katalog zmian, OCHRONA, 2 symetrycznych pracowników, zero absencji) -- styczeń 2027 dał 2/3 zamiast równiejszego rozkładu, wrzesień 2026 wyszedł idealnie równo (stąd też, dlaczego pierwsza, zbyt czysta rekonstrukcja architekta nie złapała problemu). Otwarte pytanie dla architekta w pliku findingu (czy `WEEKEND_FAIRNESS_WEIGHT` jest za słaby względem konstrukcji `ochrona_fairness_weight`, ten sam wzorzec co `FINDING_2026-09-20_TARGET_EQUITY_WEIGHT_TOO_WEAK...`) -- CC nie projektuje poprawki solvera. |
