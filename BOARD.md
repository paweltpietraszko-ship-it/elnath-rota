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
| ROTA-TARGET-HOURS-CEILING-NOT-BULLSEYE | CC | Architekt | `task/ROTA-TARGET-EQUITY-DIAGNOSIS` | `3c17782` — raport `tasks/ROTA-TARGET-EQUITY-DIAGNOSIS/round_01/tests/pos_only_report.md` | READY_FOR_CODEX | **Wynik eksperymentu pos-only (2 obiekty, 2 powtórzenia, izolowana kopia solvera, produkcja nietknięta):** usunięcie `neg` RZECZYWIŚCIE zmienia wybrane optimum, wbrew ostrożności architekta o stałej sumie `neg` — Royal: rozstrzał 144→12h; ORDINARY-10: 70→65h. HARD pass=true, nikt nie przekracza sufitu w żadnym wariancie, bilans niedoboru (target-worked) widoczny niezależnie od wariantu (to dane, nie funkcja celu). **Ale realny koszt na Royal**: sekwencje D/N spadły 23→11 dopasowań, a solver przestaje dowodzić optymalności w dotychczasowym budżecie czasu (FEASIBLE zamiast OPTIMAL, pełne 90.1s zamiast 1.8s) — wprost koliduje z wcześniejszą zasadą OWNERA na tym wątku: "rytm D/N ma pierwszeństwo przed dokładnością indywidualnego celu godzin". Na obiekcie ORDINARY rytm był 0 w obu wariantach, więc tam kosztu nie ma, a zysk skromniejszy. Wniosek CC (dane, nie decyzja o kodowaniu): proste zerowanie `neg` nie jest bezpiecznym minimalnym fixem samo w sobie — potwierdza słuszność diagnozy (skala efektu jest duża, nie teoretyczna), ale potrzebuje węższego wariantu (np. tłumienie zamiast zerowania `neg`, albo próg tylko dla dużych niedoborów) zaprojektowanego przez architekta. Wpływ pozostałych SOFT (weekendy/święta) i 1% gap NIE badany — nie było potrzeby, pos-only jednoznacznie poprawia rozstrzał; dostępne na żądanie. Zero zmian produkcyjnych, zero HARD, zero innych wag. |
