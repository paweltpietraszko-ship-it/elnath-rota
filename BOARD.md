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
| ROTA-WORK-CODE-DURATIONS | Codex | Architekt | — (brief.md do przygotowania) | `2742543` (finding; review base `2e88d24`) | CODEX_REPORTED | **Codex R3 — materiał jest gotowy do przekazania architektowi; nie ma dalszej decyzji OWNERA przed briefem.** Wiążące zachowanie jest już jednoznaczne: tylko dodatkowe D6/N6/...; D1–D5/N1–N5 pozostają zamrożone; konfiguracja dodatkowych kodów jest per obiekt+miesiąc; koordynator wybiera wcześniej zdefiniowany kod; wybór zmienia realne `start_datetime/end_datetime` Assignmentu i przechodzi zwykłą walidację/deviations ręcznej korekty; kod trafia do PLAN i WYK; U/C bez zmian; solver, katalog zmian, WorkBalance i analytics bez zmian. **Dla architekta:** wymienione w findingu pliki są znanymi punktami styku, nie gotowym zamkniętym `TASK_SCOPE`; przed zamrożeniem briefu trzeba wyszukać i ująć minimalne istniejące seam-y persistence/schema, settings API/UI, manual-correction API/UI oraz eksportu (mapowanie, sumy, legenda, rewizja), bez duplikowania ownerów. Brief ma wymagać rzeczywistego PDF z dodatkowymi kodami i ostatecznej oceny optycznej: czytelność komórek i legendy powyżej slotu 5, prawidłowe PLAN/WYK i sumy, brak kolizji/ucięcia oraz druk w skali szarości; zielone testy nie zastępują tego gate'u. **Niewiążąca korekta materiału referencyjnego przed zamrożeniem:** lipcowa transkrypcja U/C nadal nie odpowiada wartościom widocznym w lokalnym `7442.jpg` (na zdjęciu U3–U5/C3–C5 wyglądają na 0h, nie U4/C4=24h i U5/C5=20h); ponieważ U/C jest jawnie poza zakresem, usunąć te wiersze z findingu albo poprawić je wyłącznie z wiarygodnego źródła. Surowe zdjęcia pozostają materiałem pomocniczym, nie PRODUCT_TRUTH ani dowodem exact-SHA. |
