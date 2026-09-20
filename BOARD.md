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
| ROTA-OCHRONA-EQUITY-SURGICAL-FIX | Architekt | CC | `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX` | static audit of impl `75037594113a2b619f40e04fbed5a4e4ee5c57d4` | READY_FOR_CODEX | **STATIC AUDIT ARCHITEKTA: HOLD (bez uruchamiania kodu), nie PASS dla całego Tasku.** Potwierdzone w diffie: rozdział OCHRONA/ORDINARY; ORDINARY zachowuje dotychczasową gałąź TARGET-01 i gate; OCHRONA nie wymaga kompletnych targetów, liczy committed=worked+absence+delegation i przywraca preferencję LOCAL nad EXTERNAL. **Problem A, do skorygowania albo formalnego udowodnienia:** OCHRONA `ceiling_weight = TARGET_DEVIATION_WEIGHT + dominant_weight`, gdzie `dominant_weight = ochrona_fairness_weight*(MAX_MONTHLY_HOURS+1)`, ale preferencja LOCAL nad EXTERNAL jest naliczana OSOBNO za każdy slot. Waga sufitu przewyższa jeden taki składnik, NIE gwarantuje dominacji nad SUMĄ wszystkich, wbrew komentarzowi 'never trades away a stated ceiling'; przedstaw legalny kontrprzykład lub ścisły bound i skoryguj najmniejszym sposobem, bez zmiany ORDINARY. **Problem B, test dowodowy:** commit zmienia reguły objective/assembler, ale diff testów obejmuje głównie zmianę istniejącej macierzy gate oraz jeden test zwolnienia OCHRONA; brak dedykowanego regresyjnego dowodu w repo dla absencji/delegacji przy brakującym target, mieszanym wektorze, zachowania sufitu i REPLAN z fixed hours. Raport self-test 674 z 15 istniejącymi failures i pojedyncze realne przykłady nie zastępują tych testów. **Dodatkowo sprawdź:** dla OCHRONA bez targetów `_assemble_work_balances` nadal zwraca ostrzeżenie nakazujące 'ustaw godziny docelowe', chociaż planowanie działa; rozstrzygnij minimalną korektę tekstu tylko dla OCHRONA albo uzasadnij świadomy warning, bez rozszerzania UI. Potrzebny wąski fix/kontrdowód na osobnym exact SHA i przekazanie przez BOARD; bez merge przed niezależnym audytem/wyraźną decyzją OWNERA. |
