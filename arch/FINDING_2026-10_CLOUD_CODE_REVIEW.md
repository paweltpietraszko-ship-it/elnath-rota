# FINDING 2026-10 — niezależny przegląd kodu (CC, sesja chmurowa)

STATUS: lista znalezisk z dowodami. Kod NIE był zmieniany. Wejście dla
architekta/Pawła — nie brief, nie decyzja.

## Nagłówek

- **Przejrzany SHA:** `main@4f0ed0d7862f718ae15ecb6fca784364c083f7a3` (2026-10-16).
- **Środowisko:** świeży venv (Linux, Python 3.12), zależności z `pyproject.toml`.
  Zegar kontenera: `Etc/UTC`. Reproduktory to małe skrypty w scratchpadzie
  sesji (nie są w repo); kluczowy kod każdego jest streszczony niżej, żeby dało
  się go odtworzyć. Wszystkie używają istniejących fixtur
  (`tests/support/minimal_state.py`, `tests/test_t019b.py`, `tests/test_t020.py`,
  `tests/test_t032_soft_ranking.py`).
- **Przeczytane:** `CLAUDE.md`, `ODLOZONE.md`, `BOARD.md`,
  `rota/planning/{solver,constraints,eligibility,validator,validator_shared,validator_checks_*,engine (gate/frozen-boundary),availability,timeutil}.py`,
  `rota/application/{plan_ops (plan_month/select_candidate/replan/cutover),manual_edit,assembler,open_month,deviation_mapping,schedule_projection (OCHRONA+ORDINARY assembly, lineage)}.py`,
  `rota/balance.py`, `api/{main,deps,config}.py`, `api/auth/*`,
  `api/routers/{backup,excel_external (select-candidate),manual_edit (mark-not-worked),schedule (GET month)}.py`,
  `frontend/src/api/client.ts` (planMonth/selectCandidate), `Dockerfile`.
- **Uruchomione:** tylko skrypty-reproduktory opisane przy znaleziskach (+ jeden
  scenariusz hostowany CENTRAL_SERVICE przez `TestClient`). Pełnej suity NIE
  uruchamiano.
- **NIE pokryte:** `fairness.py` (cel solvera), `shift_catalog.py`
  (generowanie zapotrzebowania), awaryjne pary 24h w szczegółach
  (`work_periods.check_emergency_pair_structure`), `site_rules.py`,
  `rule_decisions.py`/`decision_guidance.py`, `lifecycle_ops` (finalize),
  `training.py`, `analytics_read.py`, `durable_inputs.py` poza
  `append_availability`, eksport ORDINARY w szczegółach, renderer PDF
  (`schedule_export.py`), dodatek Excel/VBA, frontend poza dwoma wywołaniami
  API. Nie sprawdzano ustawień zmiennych środowiskowych na Railway (brak
  dostępu).

---

## F1 — Ręczna korekta dająca trzecią nockę z rzędu kończy się błędem 500

- **ID:** F1
- **SEVERITY:** HIGH
- **WHERE:** `rota/application/deviation_mapping.py:13-47` (`_BUILTIN_RULE_CATEGORY` nie ma `"NIGHT-STREAK-01"`), wywoływane z `rota/application/manual_edit.py:453`.
- **TRIGGER:** OCHRONA. Pracownik ma N 20.08 i 21.08; koordynator ręczną korektą
  przepisuje N 22.08 na tę samą osobę (świadome obejście, które dla
  THIRD-CONSECUTIVE-SHIFT-01 jest wprost dozwolone i ma stać się Deviation —
  `tests/test_t058.py::test_t58_15`). Walidator zgłasza `NIGHT-STREAK-01`
  razem z `THIRD-CONSECUTIVE-SHIFT-01`; `materialize_deviations` →
  `category_for_rule("NIGHT-STREAK-01")` → `UnknownDeviationSource`.
  `api/errors.py` nie mapuje tego wyjątku → nieznany 500.
- **EFEKT DLA KOORDYNATORA:** nie da się zapisać ręcznej korekty, która daje
  komuś trzecią nockę z rzędu — dostaje ogólny błąd techniczny zamiast
  zapisanego odstępstwa, choć dla trzech zmian dziennych z rzędu ta sama
  operacja przechodzi.
- **EVIDENCE (uruchomione):** baza `:memory:`, `_bootstrap` z `test_t019b`
  (OCHRONA) z profilem D 06-18 + N 18-06, wersja V0 z N 10/20/21/22.08
  (E2, E1, E1, E2), potem
  `manual_edit.apply_manual_correction(..., upsert_assignments=[replace(A-22, employee_id="E1")], note="x")`.
  Wynik: `UnknownDeviationSource no DeviationCategory mapping for rule 'NIGHT-STREAK-01'`.

## F2 — Walidator NIGHT-STREAK-01 bierze historię z dowolnego miesiąca; jedna stara trójka blokuje PLAN każdego innego miesiąca

- **ID:** F2
- **SEVERITY:** MEDIUM (dziś osiągalne tylko przez istniejące dane z trójką N — patrz niżej; po naprawie F1 staje się osiągalne zwykłą ręczną korektą)
- **WHERE:** `rota/planning/validator_checks_patterns.py:48-53` (pętla po `state.boundary_assignments` bez ograniczenia dat); `boundary_assignments` jest celowo nieograniczony (`rota/application/assembler.py:253` `_context_window` → `datetime.min..datetime.max`). Bliźniacza reguła `_check_third_consecutive_shift` ma już to ograniczenie (`relevant_start/relevant_end`, Code audit R4-01) — NIGHT-STREAK-01 go nie dostał. Solver patrzy tylko na okna `[month_start-2, month_end-2]` (`constraints.py:627-629`).
- **TRIGGER:** w jakimkolwiek innym zaakceptowanym miesiącu obiektu istnieje N
  trzy dni z rzędu u jednej osoby (np. czerwiec). PLAN dla października.
  Walidator zgłasza `NIGHT-STREAK-01` z `assignment_ids=()` (żadna data nie
  należy do bieżącego miesiąca), `engine._split_frozen_violations` nie może go
  przypisać → TECHNICAL_ERROR.
- **EFEKT DLA KOORDYNATORA:** jedna historyczna trójka nocek sprzed miesięcy
  sprawia, że „Przelicz/Planuj” każdego innego miesiąca tego obiektu kończy się
  błędem technicznym, bez żadnej możliwości naprawy z poziomu programu.
- **EVIDENCE (uruchomione):** `base_state` (OCHRONA), `boundary_assignments` =
  3× N 10/11/12.06.2026 (wersja `SV-JUNE`, z pasującymi `boundary_shift_demands`),
  październik: jedna D 10.10.
  `validate(state, [D 10.10])` → `False [('NIGHT-STREAK-01', ())]`;
  `plan(state)` → `TECHNICAL_ERROR … NIGHT-STREAK-01: E1 has N on three consecutive dates starting 2026-06-10`.
- **Skąd taka trójka w danych:** reguła istnieje od T032 (2026-08-25), więc
  wcześniejsze wersje mogą ją zawierać; ręczna korekta jest dziś zablokowana
  przez F1. Nie sprawdzałem żywej bazy na Railway.

## F3 — „Nie przepracował” (NN) wpisane po fakcie nie pojawia się na PDF/Excel; godziny WYK zawyżone

- **ID:** F3
- **SEVERITY:** HIGH
- **WHERE:** `rota/application/manual_edit.py:443-444` (dla `ASSIGNMENT_NOT_WORKED` `effective_from = now.date()`), `api/routers/manual_edit.py:103-109` (router nie przekazuje daty); eksport bierze każdy dzień z wersji, której `effective_from <= dzień` — `rota/application/schedule_projection.py:191-197` (`_version_for_date`), używane w `_collect_real_work_cells` i `_collect_ordinary_work_items`. Dla korekty historycznej zamiany pracownika ten sam problem rozwiązano (`effective_from = min(start)`, `manual_edit.py:401-402`), dla NN nie.
- **TRIGGER:** zmiana 10.08 zaplanowana dla EMP-1; 16.10 koordynator oznacza ją
  jako NN. Nowa wersja ma `effective_from=2026-10-16`, więc dla 10.08 eksport
  nadal czyta wersję rodzica, w której zmiana jest PLANNED. To samo w bieżącym
  miesiącu: NN za wczoraj → wczoraj czytane z rodzica.
- **EFEKT DLA KOORDYNATORA:** na wydruku i w eksporcie do Excela pracownik ma
  wpisaną zmianę, której nie przepracował, a suma WYK jest o te godziny za duża;
  ekran i saldo godzin (czytają bieżącą wersję) pokazują coś innego.
- **EVIDENCE (uruchomione):** `tests/test_t020.py` `_seed`/`_settings`/`_create_version`,
  D1 3.08 i 10.08 (PLANNED), potem realny
  `manual_edit.mark_not_worked(..., assignment_id="ASG-10")`:
  ```
  before NN: plan[day10]='D1' wyk[day10]='D1' plan_hours=24 wyk_hours=24
  current version: SV-51ec… effective_from: 2026-10-16 ASG-10 state: CANCELLED NN
  after NN : plan[day10]='D1' wyk[day10]='D1' plan_hours=24 wyk_hours=24
  ```

## F4 — Pierwsza wersja z „Obowiązuje od” w środku miesiąca: PDF pomija dni przed tą datą, choć solver je obsadził

- **ID:** F4
- **SEVERITY:** MEDIUM (być może zamierzone — WYMAGA DECYZJI, czym ma być „Obowiązuje od” dla pierwszej wersji)
- **WHERE:** `rota/application/schedule_projection.py:191-197` (`_version_for_date` zwraca `None` przed `effective_from` korzenia → dzień pusty); solver i tak generuje i obsadza zapotrzebowanie na cały miesiąc (`plan_ops.plan_month`, `generate_profile_demands`), a ekran/saldo (`open_month`, `balance.py`) liczą całą wersję bez patrzenia na `effective_from`.
- **TRIGGER:** pierwszy PLAN miesiąca z `effective_from=10.08` (pole daty w
  `MonthlyPlanning.tsx:1019`); wersja zawiera zmianę 3.08.
- **EFEKT DLA KOORDYNATORA:** ekran pokazuje zmianę 3.08 i wlicza ją w godziny,
  a wydruk ma 3.08 pusty i mniejszą sumę godzin.
- **EVIDENCE (uruchomione):** wersja z D1 3.08 i 12.08, `effective_from=2026-08-10`
  → projekcja: `plan day3: '–' day12: 'D1' plan_hours: 12`.

## F5 — Serwer liczy „teraz” w UTC, a godziny zmian to czas polski: ochrona rozpoczętych zmian przesunięta o 1-2 h

- **ID:** F5
- **SEVERITY:** HIGH (warunek: Railway działa w UTC — patrz evidence)
- **WHERE:** wszystkie godziny w domenie to naiwne `datetime` czasu ściennego
  (brak `zoneinfo`/`tzinfo` w `rota/` i `api/`), porównywane z naiwnym
  `datetime.now()`/`date.today()` serwera: `manual_edit.py` `_now()` +
  `_classify_and_compute_effective_from` (granica „rozpoczęta”),
  `plan_ops.py:416-418` (`is_schedule_version_live` / `cutover_at`),
  `plan_ops.py:679` (cutover przy akceptacji), `effective_from` domyślnie
  `date.today()`. `Dockerfile` nie ustawia `TZ` ani nie instaluje `tzdata`;
  obraz `python:3.12-slim` domyślnie działa w UTC.
- **TRIGGER:** 16.10, 06:30 czasu polskiego (= 04:30 UTC). Zmiana 06:00-18:00
  już trwa. Serwer uważa ją za przyszłą: ręczna korekta może zmienić jej
  godziny/pracownika bez podania powodu, a „Przelicz Plan” może ją przenieść
  (cutover 04:30 < 06:00). Między 00:00 a 02:00 czasu polskiego `date.today()`
  daje wczorajszą datę jako „Obowiązuje od”.
- **EFEKT DLA KOORDYNATORA:** przez pierwsze 1-2 godziny trwającej zmiany
  program pozwala ją przepisać albo przenieść tak, jakby jeszcze się nie
  zaczęła — zabezpieczenie „rozpoczętej służby nie ruszamy” nie działa.
- **EVIDENCE (uruchomione):** ten sam zaakceptowany październik (3 pracowników,
  D 06-18), ta sama korekta (przesunięcie trwającej zmiany 16.10 06:00 o +2 h,
  bez notatki), dwa zegary:
  ```
  server clock = Europe/Warsaw 06:30: rejected -> HistoricalServiceMutationRejected
  server clock = UTC (same instant, 04:30): ACCEPTED rewrite of an already-running shift (no reason required)
  ```
  UNVERIFIED: czy w zmiennych Railway ustawiono `TZ=Europe/Warsaw` — nie mam
  dostępu; w repo (`Dockerfile`, `railway.json`, `deploy/RAILWAY.md`) nie ma
  żadnej wzmianki o strefie.
- **Ten sam korzeń, osobny skutek (nie uruchamiane, wynika wprost z arytmetyki
  naiwnych dat):** nocka 24/25.10.2026 19:00-07:00 (zmiana czasu z letniego na
  zimowy) to realnie 13 h, program liczy 12 h; w nocy 27/28.03.2027 realnie 11 h,
  program liczy 12 h. Dotyczy godzin na PDF, salda i odpoczynku REST-01.

## F6 — L4/urlop wpisany na już zaakceptowaną zmianę nie jest nigdzie sygnalizowany; dopiero PDF odmawia

- **ID:** F6
- **SEVERITY:** HIGH
- **WHERE:** `rota/application/open_month.py:60-62` — walidator jest
  uruchamiany na każdym GET miesiąca, ale do odpowiedzi trafiają tylko
  `report.warnings`; `report.violation_details` są wyrzucane. Odstępstwa
  widoczne na ekranie to `snapshot.deviations`, zamrożone przy tworzeniu
  wersji (`manual_edit.py:453`, `select_candidate`). `append_availability`
  (`durable_inputs.py:201+`) tylko unieważnia DECISION_REQUIRED, niczego nie
  przelicza.
- **TRIGGER:** zaakceptowany październik; potem SICK_LEAVE dla pracownika
  27-30.10, który ma zmianę 28.10. Koordynator otwiera miesiąc.
- **EFEKT DLA KOORDYNATORA:** grafik dalej pokazuje osobę na L4 na służbie, bez
  ostrzeżenia ani odstępstwa; dowiaduje się o tym dopiero, gdy eksport PDF
  odmawia, albo gdy sam pamięta, żeby kliknąć „Przelicz”.
- **EVIDENCE (uruchomione):**
  ```
  E1 on L4 27-30 Oct but still assigned 28 Oct.
  month view warnings: []
  persisted deviations on current version: []
  validator (computed, not shown): ['SICK_LEAVE-01']
  PDF export: ExportProblemError ASSIGNMENT_ABSENCE_CONFLICT: E1/2026-10-28: real Assignment on an active absence day
  ```
  Dotyczy też każdej innej reguły HARD łamanej przez późniejszą zmianę danych
  (DAY_SHIFT_OFF, UNAVAILABLE, DELEGACJA, okno godzinowe, wyłączone członkostwo,
  zmienione reguły obiektu) — mechanizm ten sam, osobno nie uruchamiane.
  Nie znalazłem tego w `ODLOZONE.md` ani w `arch/FINDING_2026-09-04_VALIDATOR_WARNINGS_NEVER_SURFACED.md`
  (tamten dotyczy ostrzeżeń SOFT, nie naruszeń HARD).

## F7 — Zmiana hasła bez podania obecnego hasła i bez minimalnej długości

- **ID:** F7
- **SEVERITY:** MEDIUM
- **WHERE:** `api/auth/backend.py:68-79` (`PATCH /api/auth/me/password`),
  `api/auth/schemas.py:26-36` (`PasswordChangeRequest` = samo `password`),
  `api/auth/manager.py` (brak `validate_password`; domyślny z fastapi-users
  nic nie sprawdza).
- **TRIGGER:** ktoś z dostępem do zalogowanej przeglądarki (sesja 8 h)
  wysyła `{"password": "x"}`.
- **EFEKT DLA KOORDYNATORA:** ktoś przy cudzym otwartym komputerze może w
  sekundę przejąć konto (i dane osobowe pracowników) — wystarczy, że ustawi nowe
  hasło, a prawowity właściciel straci dostęp; hasło jednoznakowe też przejdzie.
- **EVIDENCE (uruchomione):** CENTRAL_SERVICE przez `TestClient` (env jak w
  `tests/test_t024_auth_isolation.py::_run`), konto przez
  `api.provision_account.create_account`:
  ```
  {"login": 204, "change_pw_without_old_pw": 200, "old_pw_login": 400, "new_1char_pw_login": 204}
  ```
  Dodatkowo (z kodu, nie testowane): JWT jest bezstanowy, więc zmiana hasła nie
  unieważnia innych otwartych sesji (do 8 h), a klucze API do Excela przeżywają
  zmianę hasła; brak limitu prób logowania w aplikacji (UNVERIFIED, czy Railway
  coś tu filtruje).

---

## Sprawdzone, odrzucone (żeby nikt nie badał drugi raz)

- **Akceptacja nieaktualnego podglądu po ręcznej korekcie** (Przelicz → ręczna
  korekta → „Użyj tego grafiku” na starym podglądzie): sprawdzone
  reproduktorem — `select_candidate` odrzuca (`CandidateRejected … pre-cutover
  PRIMARY … mutated`), bo porównanie faktów w `_replan_cutover_violations`
  obejmuje `schedule_version_id`. Działa „przypadkiem”, ale działa; komunikat
  dla koordynatora jest nieczytelny (lista technicznych id). Excelowe
  `select-candidate` idzie tą samą ścieżką.

## Obszary przejrzane bez znalezisk

- Bramki dostępności: `eligibility._blocked_by_availability` vs
  `validator_checks_availability` (DAY_SHIFT_OFF HARD po dacie startu / SOFT po
  dacie końca, UNAVAILABLE/SICK/LEAVE/DELEGACJA przez `overlaps_date_range`,
  okno godzinowe przez wspólne `unavailable_time_window_overlaps`, ROLE-01,
  EXTERNAL-01, reguły obiektu z `dn_semantics_apply`) — spójne między solverem
  a walidatorem.
- REST-01 / LOAD-01 / WEEKLY-REST-01: zbiory faktów stałych w solverze
  (`build_fixed_intervals/_periods`, S1 wyłączone z tygodniowego) i w walidatorze
  są te same; próg LOAD (`<=` w solverze, `>` jako naruszenie) spójny.
- THIRD-CONSECUTIVE-SHIFT-01: tylko OCHRONA w obu miejscach; okno walidatora
  ograniczone jak w solverze.
- `fixed_existing_assignments` / `_already_covered_counts` / NN historyczne przy
  cutover; `_coerce_unproven_realized_to_planned` przy akceptacji.
- Saldo godzin `rota/balance.py` (realized + planned, CANCELLED pominięte,
  przypisanie do miesiąca startu zgodne z solverem).
- Izolacja kont CENTRAL_SERVICE: `db_path`/`coordinator_id` wyłącznie z
  serwerowego `AccountMapping`, ochrona przed `../` w `db_filename`, ta sama
  ścieżka dla klucza API Excela; kopia zapasowa per konto; diagnostyka bez
  wspólnego logu w trybie hostowanym; GET miesiąca ukrywa nieaktualny podgląd.
