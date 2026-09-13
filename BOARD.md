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
| ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT | CC | Architekt | — (finding, brak briefu) | `backend.py` niezmieniony od `03e5353` (jeden commit w całej historii); brief `tasks/ROTA-T065/brief.md` | OWNER_DECISION_NEEDED | **`backend.py` nie był nieautoryzowanie zmieniony — sprawdzone `git log --oneline -- backend.py`, dokładnie jeden commit w historii, baseline projektu. Przyczyna jest odwrotna: format brief.md architekta odjechał od kontraktu, którego `backend.py` mechanicznie wymaga, i nikt tego nie złapał, bo mechaniczna bramka nie jest już uruchamiana w bieżącym procesie CC↔Codex/BOARD.md (ostatni realny przebieg: `tasks/ROTA-T055/round_01/tests/backend_output_r4.txt`, 4 września).** `backend.py::read_task_scope()` wymaga LITERALNEJ linii `TASK_SCOPE:` (dwukropek, bez nagłówka markdown) z listą plików jako myślniki (`- plik.py`) — dokładnie tak wyglądał `tasks/ROTA-T055/brief.md` (`TASK_SCOPE:` + myślniki), i wtedy `SIZE_FILE`/`SIZE_FUNC`/`RUFF`/`DIFF_SCOPE` realnie działały. `tasks/ROTA-T065/brief.md` sekcję nazywa `## 19. Literalny TASK_SCOPE` (nagłówek markdown, nie literalne `TASK_SCOPE:`) i wypisuje pliki jako listę numerowaną (`1. `, `2. `...), nie myślnikami. Zweryfikowane bezpośrednim uruchomieniem `read_task_scope()` na tym pliku: `ValueError: TASK_SCOPE missing in brief` — parser nie znajduje sekcji wcale, więc `check_sizes`/`check_ruff`/`check_scope_and_files`/`find_importers` dostają pustą listę i milczą, zamiast wyrzucić błąd na przekroczenie limitu linii pliku/funkcji. **Prośba do architekta: pisząc TASK_SCOPE w każdym brief.md, używać dokładnie formatu `backend.py` już umie parsować — literalna linia `TASK_SCOPE:` (nie nagłówek), pliki jako myślniki, nie lista numerowana** — to jedyna mechaniczna bramka pilnująca limitu wielkości plików/funkcji niezależnie od implementatora; jej ciche wyłączenie zwiększa ryzyko rozrostu kodu (spaghetti) bez sygnału. CC nie zmienia formatu briefów samodzielnie — to decyzja architekta/właściciela co do konwencji pisania briefów. |
| ROTA-T065-PRINT-GAP | Codex | Architekt/CC | `task/ROTA-T065-PRINT-GAP` | audit `eda3b0a` (brief B `8bf47a21484277ffecf0ae7a6223b28fe970c971`) | CODEX_REPORTED | **PASS — architektura CHECKPOINT B zamknięta.** Raport: `tasks/ROTA-T065-PRINT-GAP/round_01/tests/tests_r5.txt`. 11 decyzji jest w briefie jako PRODUCT_TRUTH; stary kontrakt roli przy godzinach usunięto; jedna historyczna etykieta stanowiska ma jawnego ownera/dependency w `ROTA-T065-CONFIGURABLE-ROLES`; PRINT-GAP nie tworzy modelu ról. Jeden export lifecycle i scope pozostają zachowane. Implementacja produkcyjna nadal czeka wyłącznie na techniczną dostępność historycznego stanowiska z dependency. Nie powtarzano audytu prototypu ani nie uruchamiano testów produktu/regresji. |
| ROTA-T065-CONFIGURABLE-ROLES | Codex | Architekt | `task/ROTA-T065-CONFIGURABLE-ROLES` | owner ruling `3836d5c`, audit R1 `8859b77` (brief `98226a792b24a293bba24bb67365b741b8403234`) | CODEX_REPORTED | **OWNER_DECISION zamknięta; poprawić brief technicznie.** Solver nigdy sam nie zastępuje roli: przy braku obsady zgłasza niemożność ułożenia grafiku, a koordynator rozwiązuje konkretny brak przez external support albo jawne użycie kierownika jako sprzedawcy. Nie powstaje globalna hierarchia, stałe automatyczne uprawnienie ani zmiana stanowiska. Pozostają R1-01/R1-02/R1-04: konkretny owner i historia stanowiska, pełny TASK_SCOPE oraz `WHERE_MAP: REQUIRED`. |
| ROTA-T065-ORDINARY-TIME-AVAILABILITY | Codex | Architekt | `task/ROTA-T065-ORDINARY-TIME-AVAILABILITY` | owner ruling `4f59a4e`, audit R1 `b9f3a5d` (brief `087c228fbea02964cc9e916a1a93637beffc1112`) | CODEX_REPORTED | **OWNER_DECISION zamknięta; poprawić brief technicznie.** V1 obsługuje wyłącznie okna w obrębie jednej doby; overnight jest poza scope i ma być jawnie odrzucany. Dla `00:00–12:00` praca od `12:00` jest dozwolona. Pozostają: poprawny scope (`db.py`, roster API, availability owner), jednoznaczne wyłączenie `can_work_24h` w ORDINARY, zachowanie ogólnych kontrolek, zawężenie testów i `WHERE_MAP: REQUIRED`. |
| ROTA-T065-MANUAL-MIDDLE-SHIFT | Codex | Architekt | `task/ROTA-T065-MANUAL-MIDDLE-SHIFT` | audit `cf0c8f6` (brief `41f2e4c84fc8498dd87eae7b069b9ac0a659b317`) | CODEX_REPORTED | **WYMAGA_KOREKTY; decyzja o zastępstwie jest zamknięta w `CONFIGURABLE-ROLES@3836d5c`.** Ręczny child ScheduleVersion, brak solvera i brak zwolnień S1 są poprawne. Dostępność godzinowa musi być twardą zależnością; PDF ma zachować tylko godziny zgodnie z PRINT-GAP; zdefiniować fail-closed inwariant legalnego PRIMARY bez demandu, poprawić `schema.py` na `db.py`, zawęzić testy i dodać `WHERE_MAP`. |
| ROTA-T065-DECISION-GUIDANCE-GAP | CC | Architekt | — (finding, brak briefu) | `rota/planning/decision_guidance.py` niezmieniony od T062 (owner decisions 2026-09-10, przed T065) | OWNER_DECISION_NEEDED | **Właściciel podejrzewał, że komunikaty koordynatora z T062 są ochroniarskie — sprawdzone w kodzie, trafne, ale wynik ma dwie różne wagi.** T062 (`decision_guidance.py`) powstał dzień przed T065 i w całości zakłada słownictwo Ochrony dla trzech warunków blokujących.

**Martwe dziś dla ORDINARY (zablokowane przez `dn_semantics_apply()`, nigdy się nie odpalą — potwierdzone w kodzie):**
- `DAY_ONLY-01` → "Koliduje z ustawieniem: Nocka" / "Zmień Nocka" (`eligibility.py:200`);
- `NIGHT-STREAK-01` → "limit dwóch nocek pod rząd" (`validator.py:377`).

**Żywy błąd, nie martwy kod:** `SHIFT-24-01` → "Koliduje z ustawieniem: 24" / "Zmień 24: {names}" (`eligibility.py:193`) **nie ma żadnej bramki regime** — sprawdza wyłącznie `demand.catalog_kind == H24`, więc jeśli obiekt ORDINARY zdefiniuje 24-godzinną zmianę w katalogu, koordynator dostanie czysto ochroniarski komunikat odsyłający do przełącznika "24h" w Obsadzie — którego `ROTA-T065-ORDINARY-TIME-AVAILABILITY` (już `CODEX_REPORTED`, "jednoznaczne wyłączenie `can_work_24h` w ORDINARY") ma jawnie wyłączyć dla tego reżimu. Bez korekty tego wpisu koordynator dostanie instrukcję wskazującą na kontrolkę, która przestanie mieć znaczenie.

**Prawdziwa luka: żaden z trzech już zaakceptowanych briefów (`CONFIGURABLE-ROLES`, `ORDINARY-TIME-AVAILABILITY`, `MANUAL-MIDDLE-SHIFT`) nie wspomina `decision_guidance.py` w swoim `WHERE_MAP`.** Gdy nowe godzinowe ograniczenie ORDINARY z `ORDINARY-TIME-AVAILABILITY` zacznie faktycznie blokować planowanie, nie będzie miało żadnego dedykowanego komunikatu koordynatorowego — spadnie do domyślnego `_GENERIC_SITE_RULE_TEXT` ("Koliduje z zapisaną regułą obiektu") albo w ogóle nie da czytelnej podpowiedzi, w zależności od tego jak nowy warunek zostanie zaimplementowany.

**Do rozstrzygnięcia przez architekta:** (a) czy SHIFT-24-01 dostaje bramkę regime analogiczną do DAY_ONLY-01/NIGHT-STREAK-01, czy inny komunikat dla ORDINARY; (b) `decision_guidance.py` powinien trafić do `WHERE_MAP` `ORDINARY-TIME-AVAILABILITY` (albo dostać własny mały finding), żeby nowy warunek godzinowy miał czytelną, nie-ochroniarską podpowiedź działania zamiast generycznego tekstu. CC nie projektuje tego samodzielnie. |
