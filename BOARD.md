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
| ROTA-T065-PRINT-GAP | Codex | CC | `task/ROTA-T065-PRINT-GAP` | audit `18665e3` (brief `5e1a1f27543f50d5fc09f2be1809942df67a5d72`) | CODEX_REPORTED | **PASS preimplementation.** R2-01 i R2-02 zamknięte bez zmiany koncepcji; raport `tasks/ROTA-T065-PRINT-GAP/round_01/tests/tests_r3.txt`. Następny dozwolony krok to wyłącznie syntetyczny, izolowany prototyp PDF w `tasks/ROTA-T065-PRINT-GAP/prototype/**` dla CHECKPOINT A. Produkcja nadal HOLD do jawnego `OWNER_ACCEPTED CHECKPOINT A`; PASS nie zatwierdza wyglądu. Nie uruchamiano testów produktu ani regresji. |
| ROTA-T065-PANEL-CLEANUP | CC | Architekt | — (finding, brak briefu, do podjęcia po ROTA-T065-PRINT-GAP) | `frontend/src/screens/ControlPanel.tsx`, `EmployeeDetail.tsx`, `PrintSettings.tsx` niezmienione przez T065 poza dwiema kolumnami ról w Obsadzie i katalogiem zmian | OWNER_DECISION_NEEDED | **Panel sterowania i ekran pracownika nadal mieszają widoki OCHRONA/ORDINARY — właściciel poprosił o pełny przegląd (zrobiony) i podjął decyzje produktowe, które architekt ma teraz zaprojektować technicznie.** Zakres NASTĘPUJE PO `ROTA-T065-PRINT-GAP` (ten sam ekran, ten sam model danych — sensowne razem, nie równolegle).

**Zweryfikowane w kodzie (nie tylko UI — prześledzone aż do backendu):**
1. `ControlPanel.tsx` (zakładka Obsada): kolumna "24h" (`can_work_24h`) pokazuje się bez warunku dla każdego obiektu.
2. `ControlPanel.tsx` (dodawanie wsparcia zewnętrznego): dropdown "Ograniczenie zmiany" (Dniówka/Nocka) bez warunku niezależnie od reżimu.
3. `EmployeeDetail.tsx`: "Macierz dostępności" (kolumny Dniówka/Nocka/24h) i "Tylko dniówka" — **funkcjonalnie martwe dla ORDINARY, ale w pełni klikalne**. Prześledzone do `rota/application/rule_decisions.py::create_employee_shift_unavailability` → tworzy `SiteRule` kind `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`, który `dn_semantics_apply()` (rota/planning/shift_catalog.py) jawnie pomija dla `SitePlanningRegime.ORDINARY`. Koordynator sklepu klika "zablokuj Nockę" i solver to ignoruje bez żadnego sygnału.
4. `PrintSettings.tsx`: już objęte przez `ROTA-T065-PRINT-GAP` sekcja 12.

**Decyzje właściciela (potwierdzone wprost w rozmowie, do wzięcia 1:1, nie do reinterpretacji):**
- Kolumna "24h" w konfiguracji obsady znika całkowicie dla ORDINARY (nie ukryta warunkowo z zachowaniem pola — sama koncepcja nie ma zastosowania).
- Macierz Dniówka/Nocka dla ORDINARY zastąpiona kolumnami **per realnie zdefiniowana zmiana z Katalogu zmian tego obiektu**, z etykietą = rzeczywiste godziny tej zmiany (nie numer "1/2/3 zmiana" — właściciel to odrzucił jako mylące, skoro ustaliliśmy że druk i tak pokazuje realne godziny, nie kody). Przykład właściciela: "kierowniczka A ma tylko poranną zmianę w danym tygodniu" → odblokowana tylko kolumna odpowiadająca zmianie porannej z katalogu.
- "Zablokuj nockę" jako koncepcja zostaje — to po prostu jedna z kolumn per-zmiana (ta najpóźniejsza), nie osobny hardcoded przełącznik.
- Nowa koncepcja: **"zmiana ruchoma"** — sezonowe/eventowe pokrycie (właściciel: "koszmar, bo zależą od potrzeb"), wprowadzane ad-hoc (wzorzec UI identyczny z dzisiejszym S1 w `MonthlyPlanning.tsx` — dowolne godziny, ręcznie, bez stałej pozycji w Katalogu zmian) **ale BEZ zwolnień prawnych S1** (S1/PERIODIC_TRAINING jest dziś zwolnione z REST-01/WEEKLY-REST-01 i nie pokrywa demandu — "zmiana ruchoma" to prawdziwa płatna obsługa klienta i ma podlegać wszystkim regułom — odpoczynek, rola, eligibility — dokładnie jak każda inna zmiana pokrywająca realny demand). Różni się od zwykłej zmiany katalogowej WYŁĄCZNIE sposobem wprowadzania, nie statusem prawnym.

**Do zaprojektowania przez architekta:**
(a) mechanizm ograniczenia per-zmiana-z-katalogu dla ORDINARY — dzisiejszy `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` jest keyowany na `ShiftKind` (D/N), nie na tożsamość konkretnego wiersza katalogu; potrzebny nowy `SiteRule` kind albo inny mechanizm kluczowany na definicję zmiany (godziny/interwał), plus jawna decyzja co się dzieje z istniejącym ograniczeniem gdy koordynator zmieni godziny tej zmiany w katalogu (przenieść? unieważnić jawnie?);
(b) mechanizm "zmiana ruchoma" — czy to nowy, ad-hoc `ShiftDemand` tworzony w locie (nie z Katalogu zmian) pokrywany normalnym Assignment, czy inny kształt — z zachowaniem że przechodzi przez pełny eligibility/rest/role pipeline, nie przez S1's exemption path;
(c) czy usunięcie "24h" dla ORDINARY dotyka tylko UI (pole nadal istnieje w modelu, po prostu nieedytowalne/ukryte) czy też samego `SiteMembership.can_work_24h` dla tego reżimu.

CC nie projektuje tego samodzielnie — zmiana modelu danych (nowy SiteRule kind, nowy sposób tworzenia ShiftDemand) wymaga pełnego briefu i audytu Codex jak T065/T065-PRINT-GAP. |
