# BOARD.md — kolejka przekazań CC ↔ Codex

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalaczem pracy; ten plik tylko rejestruje
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
| BOARD-01 | ChatGPT/architekt | OWNER | docs/evaluator-next-steps-request | 96f47f7 | OWNER_DECISION_NEEDED | Opinia architekta zapisana w `arch/ARCHITECT_RESPONSE_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `96f47f7f8af95d4d4b8fcc5f3db303e61e361724`. Architekt rekomenduje potwierdzić wszystkie trzy decyzje Codexa: (1) lokalny, ręczny przepływ Symulator B → packager → jawna ocena w bieżącej sesji Codexa/ChatGPT, bez automatycznego API; (2) v1 wyłącznie dla completed reports Wariantu B; (3) wynik tylko rekomendacyjny `BRAK_UWAG / DO_SPRAWDZENIA / BRAK_DOWODU`, bez automatycznego Tasku. Doprecyzowanie: `BRAK_UWAG` nie oznacza PASS grafiku, uszkodzona/za duża paczka to błąd narzędzia, nie `BRAK_DOWODU`. Nadal nie brief i zero kodu; następny krok dopiero po decyzji OWNERA. |
| BOARD-02 | Codex | CC/architekt | docs/variant-b-shift24-pair-finding | f48a840 | CODEX_REPORTED | Niezależna odpowiedź: `arch/CODEX_RESPONSE_VARIANT_B_SHIFT24_PAIR_2026-08-31.md` @ `f48a840`. Potwierdzony małym reproduktorem defekt produkcyjnego walidatora: solver już wymusza tę samą osobę na obu połówkach 24 h, lecz `validator.py:470-471` błędnie dolicza do pary pracowników z innych, legalnie nakładających się demandów. Nie filtrować generatora Wariantu B; seed 0 zachować jako reproduktor. Zalecany jeden mały Task produktu dotyczący `SHIFT-24-PAIR-01`. Ujawnianie odrzuconego kandydata przy `TECHNICAL_ERROR` to osobna, widoczna dla użytkownika decyzja OWNERA i nie blokuje naprawy walidatora. |
