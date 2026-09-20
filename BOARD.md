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
| ROTA-OCHRONA-EQUITY-SURGICAL-FIX | Architekt | CC | `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX` | brief do korekty `dc08f83` | READY_FOR_CODEX | **PRECHECK ARCHITEKTA: HOLD, korekta briefu przed implementacją; Codex bez limitu do jutra, niezależny precheck skierować do Antigravity po korekcie.** Kierunek A (OCHRONA-only) odpowiada decyzji OWNERA: przywrócić dawny równy podział i możliwość PLAN/REPLAN bez wszystkich targetów, ORDINARY nietknięty; nie wdrażać pos-only B (Royal D/N 23→11, 90s). Jednak `brief.md` nie jest jeszcze implementowalnym kontraktem: (1) fallback historycznie minimalizuje rozstrzał **surowych worked_hours**, więc zdanie „liczony na `_effective_targets`” bez zdefiniowania metryki jest niespójne; (2) `_effective_targets` istnieje tylko dla osób z target_hours; przy braku targetu nie wiadomo, jak uwzględnić absence/delegation i nie dopuścić 80h urlopu + pełnego przydziału; (3) nie określono zachowania gdy OCHRONA ma mieszany wektor targetów, częściowo absencje albo fixed/REALIZED w REPLAN, oraz czy wpisany limit pozostaje chroniony; (4) kryterium „bez regresji rytmu” wymaga jawnego pomiaru: historyczny wynik 12h spread nie dokumentuje liczby dopasowań D/N, nie należy deklarować równocześnie gwarancji 12h i niepogorszenia rytmu bez dowodu; (5) zakres i testy muszą objąć istniejący precheck oraz wszystkie wejścia PLAN/REPLAN, ale nie nowy system ani UI. CC: popraw MINIMALNIE brief dla A, wskaż dokładny szew i semantykę brakujących targetów/absencji/istniejącej pracy, bez wymyślania progu godzin, nowych wag czy HARD capu; oddziel zatwierdzone zasady OWNERA od nieuzgodnionej decyzji o granicach celu i rywalizacji równy podział vs D/N. W razie konieczności decyzji zmieniającej zachowanie koordynatora wskaż JEDNO precyzyjne pytanie do OWNERA w BOARD. Po korekcie przekieruj wiersz do Antigravity na niezależny precheck EXACT SHA; nie implementuj przed rozstrzygnięciem. Żadnego merge. |
