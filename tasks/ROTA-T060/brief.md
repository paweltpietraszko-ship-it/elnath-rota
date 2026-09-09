# ROTA-T060 — techniczne identyfikatory nie mogą trafiać do koordynatora

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD

SOURCE_FINDING: BOARD.md / ROTA-DEVIATION-RAW-ASSIGNMENT-ID
OWNER_DECISION_2026-09-09: hash weryfikacyjny PDF z T051 pozostaje świadomym wyjątkiem i NIE jest usuwany w T060.
PREIMPLEMENTATION_AUDIT_R1: `tasks/ROTA-T060/round_01/tests/tests_r1.txt` @ `43bea8b`
OWNER_ACCEPTED_2026-09-09: T060 pokazuje neutralne „Koordynator”, ale nie usuwa ani nie zmienia `coordinator_id` w persistence, DTO, API, action trailu ani wewnętrznym filtrowaniu. Surowe ID i pole wymagające wpisania ID nie są renderowane w UI.

## 1. Cel

Usunąć z powierzchni koordynatora techniczne identyfikatory i surowe techniczne komunikaty, bez utraty informacji potrzebnej do działania produktu i bez tworzenia równoległego systemu błędów.

Problem jest systemowy, nie ekranowy: backend `api/errors.py` obecnie publikuje `str(exc)` jako `HTTPException.detail`, wspólny frontend `client.ts` przekazuje `body.detail` bez kontraktu do ekranów, a `api/routers/roster.py` ma bezpośrednią ścieżkę `HTTPException` omijającą centralny mapper. Równolegle istnieją jawne rendery pól technicznych w History/Decisions/Overview/Export oraz warning solvera omijający friendly-label flow.

## 2. Zamrożony kontrakt OWNERA

1. Koordynator nie może zobaczyć surowego `employee_id`, `site_id`, `schedule_version_id`, `action_id`, `decision_required_id`, `source_id`, `requested_by`, `linked_action_ids`, `coordinator_id` ani podobnego technicznego identyfikatora jako treści UI/komunikatu błędu/warningu.
2. Backend pozostaje ownerem bezpieczeństwa błędów. Frontend nie może być jedyną barierą chroniącą przed wyciekiem identyfikatora.
3. Publiczny błąd HTTP ma zachować właściwy status i użyteczną treść operacyjną, ale nie może kopiować surowego `str(exc)`, repr obiektu ani arbitralnego tekstu wyjątku do odpowiedzi użytkownika.
4. `api/errors.py` ma zwracać kontrolowane publiczne komunikaty dla obsługiwanych klas błędów. To jest kontrakt publiczny, nie regex-sanitizer technicznych ID.
5. Nie wolno naprawić problemu przez globalne ukrycie wszystkiego jako „Wystąpił błąd”. Dla znanych klas komunikat ma mówić koordynatorowi operacyjnie, co się stało / co zrobić, bez technicznych identyfikatorów.
6. Dla nieznanego, niekontrolowanego 500 backend nie publikuje treści wyjątku. Publiczna odpowiedź jest neutralna i bezpieczna.
7. Frontend działa fail-closed względem odpowiedzi spoza kontrolowanego kontraktu. Nie próbuje rozpoznawać UUID/ID regexem i nie utrzymuje drugiego pełnego słownika błędów. Jeśli odpowiedź błędu nie ma oczekiwanego bezpiecznego publicznego formatu, klient NIE renderuje surowego `detail`, tylko pokazuje neutralny polski fallback, np. „Nie udało się wykonać operacji. Spróbuj ponownie.”
8. Pola techniczne mogą nadal istnieć w DTO, persistence, logice backendowej, telemetryce i action trailu, jeżeli nie są renderowane koordynatorowi. T060 nie zmienia modelu danych tylko po to, aby ukryć UI.
9. W miejscach, gdzie UI potrzebuje wskazać pracownika/obiekt, używa nazwy czytelnej dla człowieka. Brak resolvowalnej nazwy nie upoważnia do fallbacku na surowe ID.
10. Dla koordynatora obowiązuje jawna decyzja OWNERA: do czasu osobnego Tasku identyfikacji/nazw UI pokazuje neutralne „Koordynator”. Nie pokazuje `coordinator_id`, nie wymaga wpisywania ID w filtrze i nie usuwa wewnętrznego `coordinator_id` z danych/history/plumbingu.
11. Warningi solvera podlegają tej samej zasadzie co błędy HTTP. `DAY_SHIFT_OFF-01` nie może ujawniać surowego employee_id; należy wykorzystać istniejący friendly-label flow zamiast tworzyć nowy subsystem.
12. Wyjątek: hash weryfikacyjny PDF zamrożony w T051 pozostaje. T060 nie usuwa ani nie maskuje tego hasha i nie rozszerza wyjątku na inne identyfikatory/hash-e.
13. T060 nie zmienia semantyki planowania, solvera, lifecycle, Deviation ani zasad eksportu poza prezentacją identyfikatorów/komunikatów.
14. `Analytics` pozostaje poza zakresem, dopóki nie ma dowodu rzeczywistego renderu technicznego ID. Samo użycie jako React key/param nie jest naruszeniem.

## 3. Powierzchnie objęte zadaniem

1. `api/errors.py`
   - centralny mapper nie może zwracać `detail=str(exc)` ani `unexpected error: {exc}` do użytkownika;
   - statusy HTTP pozostają zgodne z istniejącą klasyfikacją;
   - kontrolowane publiczne komunikaty są jawnie testowalne.
2. `api/routers/roster.py`
   - bezpośredni `HTTPException` omijający mapper nie może ujawniać employee_id/site_id;
   - nie tworzyć drugiego ad-hoc systemu błędów, jeśli da się użyć wspólnego kontraktu.
3. `frontend/src/api/client.ts`
   - nie renderuje arbitralnego `body.detail` bez rozpoznania kontrolowanego publicznego formatu;
   - odpowiedź spoza kontraktu -> neutralny fallback; żadnego regexowego „sanitizowania ID”.
4. `frontend/src/screens/Overview.tsx`
   - brak renderu `employee_id` jako treści użytkownika.
5. `frontend/src/screens/Decisions.tsx`
   - brak `requested_by`, `linked_action_ids` i podobnych ID w prezentacji;
   - koordynator -> neutralne „Koordynator”.
6. `frontend/src/screens/History.tsx`
   - objąć CAŁĄ powierzchnię, nie tylko `source_id`/`responds_to`;
   - usunąć render `coordinator_id`, `source_id`, `decision_required_id`, `requested_by`, `linked_action_ids`;
   - usunąć filtr wymagający wpisania „id koordynatora”; ewentualna prezentacja koordynatora = neutralne „Koordynator”;
   - rekursywne before_state/after_state nie może ujawniać technicznych wartości tylko dlatego, że są zagnieżdżone.
7. `frontend/src/screens/Export.tsx`
   - usunąć `siteId` z nazwy pliku widocznej użytkownikowi;
   - usunąć ekranowy skrót `document_revision`;
   - NIE zmieniać hasha weryfikacyjnego wewnątrz PDF z T051.
8. `rota/planning/solver.py::_collect_warnings`
   - `DAY_SHIFT_OFF-01` ma przejść przez istniejący mechanizm friendly-label, bez zmiany semantyki warningu.

## 4. Acceptance

T60-01: reprezentatywne wyjątki `EmployeeNotFound`, `SiteNotFound`, `ScheduleVersionNotFound`, `InvalidCoordinatorContext`, `NoCurrentScheduleVersion`, live delete/restore oraz bezpośrednia ścieżka `api/routers/roster.py` nie ujawniają surowych ID w publicznej odpowiedzi.

T60-02: status HTTP dla znanych klas pozostaje poprawny; T060 nie zamienia wszystkich błędów na 500 ani jeden ogólny tekst.

T60-03: fallback 500 nie zawiera `str(exc)`, repr ani technicznego szczegółu wyjątku.

T60-04: wspólny klient frontendowy renderuje kontrolowany bezpieczny publiczny komunikat, a odpowiedź spoza kontraktu zamienia na neutralny polski fallback. Nie stosuje regexów UUID/ID ani drugiego pełnego słownika błędów.

T60-05: `Overview`, `Decisions`, `History`, `Export` nie renderują technicznych identyfikatorów jako treści dla koordynatora.

T60-06: Historia obejmuje także nested `before_state`/`after_state`; techniczne wartości nie mogą wydostać się przez generyczny renderer obiektu.

T60-07: Historia/Decisions pokazują neutralne „Koordynator”; nie pokazują `coordinator_id` i nie wymagają wpisania ID koordynatora w UI. Wewnętrzny `coordinator_id` pozostaje bez zmian.

T60-08: brak friendly label dla pracownika/obiektu nie powoduje fallbacku na techniczne ID.

T60-09: `DAY_SHIFT_OFF-01 SOFT` nie pokazuje surowego employee_id i pozostaje operacyjnie czytelny.

T60-10: `siteId` znika z użytkowej nazwy pliku eksportu i ekranowy `document_revision` nie jest pokazywany.

T60-11: hash weryfikacyjny PDF T051 pozostaje bez zmian.

T60-12: nie ma zmian semantyki solvera/lifecycle/Deviation, nowych tabel ani przebudowy DTO/persistence tylko dla sanitizacji.

T60-13: targeted vertical od reprezentatywnego backend exception do komunikatu widocznego w UI potwierdza brak ID oraz zachowanie użytecznego tekstu.

T60-14: targeted vertical dla niekontrolowanego błędu potwierdza fail-closed frontend: arbitralny `detail` nie jest pokazany użytkownikowi.

T60-15: targeted vertical warningu planera potwierdza czytelny komunikat bez employee_id.

T60-16: Analytics pozostaje funkcjonalnie bez zmian i nie wchodzi do tasku bez reprodukcji renderu technicznego ID.

## 5. EXACT TASK_SCOPE — FROZEN po R1

READ_ONLY_EVIDENCE:
- `BOARD.md`
- `tasks/ROTA-T060/round_01/tests/tests_r1.txt`

TASK_SCOPE:
- `api/errors.py`
- `api/routers/roster.py`
- `frontend/src/api/client.ts`
- `frontend/src/screens/Overview.tsx`
- `frontend/src/screens/Decisions.tsx`
- `frontend/src/screens/History.tsx`
- `frontend/src/screens/Export.tsx`
- `rota/planning/solver.py`
- wąskie testy mappera/API dla T060
- wąskie testy frontendowe dla Overview/Decisions/History/Export/client
- wąski test/pion `DAY_SHIFT_OFF-01` warningu

`rota/planning/solver.py` wolno zmieniać wyłącznie w `_collect_warnings` i tylko dla prezentacji/friendly-label compatibility; żadnej zmiany constraints/objective/semantyki planowania.

`api/routers/roster.py` wolno zmieniać wyłącznie dla zamknięcia bezpośredniego publicznego wycieku błędu/ID.

Frontend screens wolno zmieniać wyłącznie w prezentacji/filtrach technicznych identyfikatorów i friendly labels; bez redesignu ekranów.

Jeżeli implementacja wymaga zmiany DTO/persistence/modelu coordinator identity albo innego istniejącego pliku produkcyjnego, STOP i powrót do Architekta przed edycją.

## 6. Handoff

Po tej korekcie Codex ma wykonać wyłącznie literalny re-check kontraktu i TASK_SCOPE względem R1. Nie powtarzać pełnego inventory repo.

IMPLEMENTATION HOLD pozostaje do PASS preimplementation na skorygowanym briefie.
