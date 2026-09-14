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
| ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT | Codex | Architekt | — (finding, brief do napisania) | `backend.py` baseline `03e5353`; OWNER ruling 2026-09-14 | CODEX_REPORTED | **OWNER_ACCEPTED: potrzebny osobny Task naprawczy backend.py.** Bramka ma fail-closed zatrzymywać Task przy braku lub błędnym formacie `TASK_SCOPE:` zamiast przekazywać pustą listę i milczeć. Kontrola rozmiaru plików/funkcji ma objąć także źródła frontendu `.ts` i `.tsx`, żeby duży plik nie pozostawał niewidoczny tylko dlatego, że nie jest Pythonem. Architekt ma wrócić we wszystkich nowych briefach do kanonicznego formatu już rozumianego przez backend: literalna linia `TASK_SCOPE:` i elementy `- plik`; parser nie ma legalizować kolejnych dowolnych formatów. Brief powinien dodać testy: poprawny scope jest czytany; brak/malformed scope kończy gate błędem; `.py`, `.ts` i `.tsx` podlegają limitom; DIFF_SCOPE nie działa na pustym scope; komunikat wskazuje plik i przekroczony limit. Bez refaktoryzacji istniejących dużych plików w tym samym Tasku. |
| ROTA-T065-PRINT-GAP | Codex | Architekt/CC | `task/ROTA-T065-PRINT-GAP` | audit `eda3b0a` (brief B `8bf47a21484277ffecf0ae7a6223b28fe970c971`) | CODEX_REPORTED | **PASS — architektura CHECKPOINT B zamknięta.** Raport: `tasks/ROTA-T065-PRINT-GAP/round_01/tests/tests_r5.txt`. 11 decyzji jest w briefie jako PRODUCT_TRUTH; stary kontrakt roli przy godzinach usunięto; jedna historyczna etykieta stanowiska ma jawnego ownera/dependency w `ROTA-T065-CONFIGURABLE-ROLES`; PRINT-GAP nie tworzy modelu ról. Jeden export lifecycle i scope pozostają zachowane. Implementacja produkcyjna nadal czeka wyłącznie na techniczną dostępność historycznego stanowiska z dependency. Nie powtarzano audytu prototypu ani nie uruchamiano testów produktu/regresji. |
| ROTA-T065-MANUAL-MIDDLE-SHIFT | Codex | CC | `task/ROTA-T065-MANUAL-MIDDLE-SHIFT` | audit `78b7255` (brief `8ab0d94ca40fc99b10dfc1eecc3581cadee1fa8b`) | CODEX_REPORTED | **PASS PREIMPLEMENTATION; IMPLEMENTATION HOLD DO ZALEŻNOŚCI.** Raport `tasks/ROTA-T065-MANUAL-MIDDLE-SHIFT/round_01/tests/tests_r2.txt`. Fail-closed marker legalnego PRIMARY bez demandu, jeden RoleCoverageAuthorization, wspólny hourly oracle, normalne HARD-y bez S1 i zgodność z PDF są zamknięte. Implementować dopiero po produkcyjnym domknięciu CONFIGURABLE-ROLES i ORDINARY-TIME-AVAILABILITY. |
| ROTA-EMPLOYEE-DETAIL-SIZE-LIMIT | CC | Architekt | — (finding, brak briefu) | `frontend/src/screens/EmployeeDetail.tsx` @ `task/ROTA-T065-ORDINARY-TIME-AVAILABILITY@9f3c86d`, 1055 linii | OWNER_DECISION_NEEDED | **Plik przekracza limit 600 linii (był 988 na `main` już przed dzisiejszą sesją, teraz 1055).** Wielokrotne kolejne Taski (T021 audyty, T053, T062, T064, CONFIGURABLE-ROLES, teraz ORDINARY-TIME-AVAILABILITY) dokładały tu funkcjonalność wymienioną wprost w swoich WHERE_MAP, każdy przyrost osobno mały i uzasadniony, ale plik nigdy nie był dzielony. Paweł zauważył to w trakcie dzisiejszej sesji przy ORDINARY-TIME-AVAILABILITY; owner decision: dokończyć bieżący brief minimalnie (zrobione), zgłosić przekroczenie osobno zamiast łączyć z bieżącym Taskiem. Potrzebna decyzja architekta/właściciela: osobny Task refaktoryzujący podział na mniejsze komponenty (np. macierz dostępności, formularz nieobecności, log historii jako osobne pliki), zanim kolejny Task znowu tu doda funkcjonalność. |
