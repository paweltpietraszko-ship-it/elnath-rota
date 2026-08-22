# Cursor audit — coverage UI vs `rota/application`

DATE: 2026-08-22  
ROLE: Cursor (contract review). Not CC. No T021/T023 implementation.  
SHA: `e05dfb7` (`origin/main` at audit time)  
SCOPE: every public function in `rota/application/*.py` (name not starting with `_`).

## 0. Wejścia, których nie ma w tym środowisku

`REQUEST.md` jest w tym folderze (wgrany 2026-08-22). Siedem już znalezionych punktów z REQUEST jest potwierdzone jako przeczytane w `FINDINGS.md` — nie są ponownie zgłaszane.

W repozytorium, na `origin/main` i na pozostałych zdalnych gałęziach **nadal nie ma** `arch/T021_spec.md`. A/B/C z REQUEST są w `FINDINGS.md` oznaczone jako zablokowane.

Nie zgaduję treści T021. Poniżej jest inwentarz kodu i powiązań po stronie application — nie wynik skanu względem T021.

UI w repo nie istnieje (brak `ui/`, Streamlit, desktop). „Ekran” poniżej = zamrożone wejście, które T021 ma złożyć z application API. Powiązania między ekranami istnieją tylko jako wspólne klucze i różne definicje tych samych pojęć w kodzie.

---

## 1. Inwentarz publicznych funkcji

56 funkcji. Klasy wyjątków/DTO i stałe `PLAN_PRIORITY` / `BLANK` są na końcu, nie w tabeli.

| # | Moduł | Funkcja | Guard kontekstu | Zamrożone wejście (nie T021) |
|---|--------|---------|-----------------|------------------------------|
| 1 | `store` | `open_store(db_path)` | — (producent `conn`) | start / otwarcie magazynu (T011-A) |
| 2 | `bootstrap` | `bootstrap_or_resume_coordinator_context(...)` | odmawia, gdy pełny aktywny kontekst już jest | Panel: pierwsza konfiguracja / resume (T010) |
| 3 | `bootstrap` | `coordinator_context_completeness(conn, *, coordinator_id, site_id)` | nie | Panel: kompletność obiektu |
| 4 | `bootstrap` | `month_plan_readiness(conn, *, coordinator_id, site_id, month)` | nie; `month.day==1` | Panel: gotowość miesiąca do PLAN |
| 5 | `bootstrap` | `current_roster(conn, *, site_id)` | nie | Panel: bieżąca obsada |
| 6 | `bootstrap` | `active_coordinators(conn)` | nie | Ekran startowy: „w co mogę wejść” (T011-B W3) |
| 7 | `bootstrap` | `all_coordinators(conn)` | nie | Panel admin: „co istnieje” |
| 8 | `bootstrap` | `active_sites_for_coordinator(conn, *, coordinator_id)` | nie; nie sprawdza `Coordinator.active` | Ekran startowy: obiekty do wejścia |
| 9 | `bootstrap` | `all_sites_for_coordinator(conn, *, coordinator_id)` | nie | Panel admin: wszystkie powiązania |
| 10 | `context` | `require_active_coordinator_context(...)` | to jest sam guard | nie ekran |
| 11 | `durable_inputs` | `update_employee` | tak | Panel: pracownik |
| 12 | `durable_inputs` | `update_membership` | tak | Panel: obsada / LOCAL vs EXTERNAL |
| 13 | `durable_inputs` | `append_availability` | tak | Panel + matryca: nieobecność / UNAVAILABLE |
| 14 | `durable_inputs` | `set_target_hours` | tak | Panel: norma (SOFT). **Nie** z Analityki (T019 §6) |
| 15 | `durable_inputs` | `set_calendar_day` | tak; kalendarz jest store-global | Panel: dzień kalendarza |
| 16 | `durable_inputs` | `update_site_profile` | tak; profil musi należeć do Site | Panel: zmiany / parametry profilu |
| 17 | `durable_inputs` | `update_site` | tak; **nie** może zmienić `profile_id` | Panel: nazwa / `active` Site |
| 18 | `durable_inputs` | `update_coordinator` | tak; **brak** `note` / `responds_to_*` | Panel: koordynator (T019b: nie materialne) |
| 19 | `durable_inputs` | `update_association` | tak; j.w. brak note/responds_to | Panel: powiązanie (T019b: nie materialne) |
| 20 | `durable_inputs` | `add_external_support_window` | tak | Panel: okno X/Y |
| 21 | `availability_matrix` | `employee_availability_matrix(conn, *, site_id, employee_id, month)` | nie | Panel: jedna matryca (T010 §5) |
| 22 | `availability_matrix` | `availability_history(conn, *, availability_id)` | nie | Panel: łańcuch jednej rodziny |
| 23 | `rule_decisions` | `record_structured_rule_decision(...)` | tak | Panel: datowany zakaz D/N/dzień, wyjątek `day_only` |
| 24 | `open_month` | `open_month(conn, *, site_id, month)` | nie; **brak** `month.day==1` | Ekran miesiąca / grafik |
| 25 | `open_month` | `months_with_schedule(conn, *, site_id)` | nie | Nawigacja: „gdzie jest grafik” |
| 26 | `precheck` | `precheck(state: PlanningState)` | nie; nie bierze `conn` | PRECHECK przed PLAN |
| 27 | `plan_ops` | `plan_month(...)` | tak | PLAN + ewentualnie DECISION_REQUIRED |
| 28 | `plan_ops` | `select_candidate(...)` | tak; `coordinator_id` obowiązkowy | Wybór wariantu T017 |
| 29 | `plan_ops` | `replan(...)` | tak | REPLAN (nowe dziecko WORKING) |
| 30 | `manual_edit` | `apply_manual_correction(...)` | tak | Korekta ręczna |
| 31 | `manual_edit` | `freeze_or_unfreeze(...)` | tak | Pin zmiany |
| 32 | `manual_edit` | `mark_not_worked(...)` | tak | NN (T010 §8) |
| 33 | `training` | `mark_training_realized(...)` | przez manual_edit | Szkolenie S → REALIZED + etykieta readiness |
| 34 | `training` | `save_site_membership(conn, membership)` | **nie** | nie ekran — hak transakcyjny / testy |
| 35 | `lifecycle_ops` | `revalidate(...)` | tak; `coordinator_id` **opcjonalny** | Odświeżenie Deviation |
| 36 | `lifecycle_ops` | `finalize(...)` | tak; zbiór Deviation musi być dokładny | Zamknięcie miesiąca |
| 37 | `lifecycle_ops` | `restore(...)` | tak | Przywrócenie wskaźnika current |
| 38 | `analytics_read` | `analytics_for_site_month(conn, *, site_id, month)` | nie; `month.day==1` | Ekran Analityka (T019) |
| 39 | `balance_read` | `quarter_balance(conn, *, employee_id, quarter_first_month)` | nie | Surowy odczyt kwartału (T011-D); twardszy niż T019 |
| 40 | `memory_read` | `current_decision_required(conn, *, site_id, month)` | nie; `month.day==1` | Otwarte pytanie po restarcie (T019b) |
| 41 | `memory_read` | `material_action_history(...)` | nie | Lista materialnych działań |
| 42 | `memory_read` | `material_action_detail(conn, *, action_id)` | nie | Szczegół + ewentualny link do pytania |
| 43 | `memory_read` | `effective_rules_for_month` | nie | Reguły miesiąca |
| 44 | `memory_read` | `rules_history_for_site` | nie | Historia reguł Site |
| 45 | `memory_read` | `decision_chain_for_rule_family` | nie | Łańcuch jednej rodziny |
| 46 | `memory_read` | `provenance_for_rule_version` | nie | Proweniencja wersji reguły |
| 47 | `memory_read` | `decision_for_rule` | nie | DecisionRecord wersji |
| 48 | `schedule_export` | `generate_schedule_pdf(conn, *, site_id, month, period_label, generated_at=None)` | nie; `month.day==1` | Wydruk (T020) |
| 49 | `backup` | `backup_database(conn, destination)` | nie | Kopia. Odtworzenie **poza** produktem (T011 B-4=W3) |
| 50 | `backup` | `build_diagnostic_zip(conn, destination)` | nie | Diagnostyka |
| 51 | `assembler` | `assemble_planning_state(...)` | nie | nie ekran — skład PlanningState |
| 52 | `assembler` | `generate_profile_demands(profile, month)` | nie | nie ekran |
| 53 | `assembler` | `resolved_rule_version_ids(conn, site_id, month)` | nie | nie ekran |
| 54 | `deviation_mapping` | `category_for_rule(...)` | nie | nie ekran |
| 55 | `deviation_mapping` | `materialize_deviations(...)` | nie | nie ekran |
| 56 | `errors` | `require_real_date(value, *, field_name=...)` | — | nie ekran |

Publiczne typy (nie funkcje): wyjątki w `errors.py` + `MissingCoordinatorActor`, `ExportProblemError`; DTO `OpenMonthView`, `ContextCompleteness`, `MonthPlanReadiness`, `CoordinatorAnalyticsView` / wiersze, `EmployeeAvailabilityMatrix`, `PrecheckResult`, `MaterialActionSummary` / `Detail`, `DecisionRequiredReadback`, `ExportReady` / `ExportProblem` / `ExportModel` / `RowCells`.

---

## 2. Co da się powiedzieć bez T021_spec („pominęliśmy” = luka API vs zamrożone wejścia)

To nie jest werdykt o tekście T021. To jest: **czego przyszły UI nie da się złożyć wyłącznie z `rota.application`, choć briefy T010/T019/T020 tego wymagają.**

### G1 — ustawienia wydruku nie mają API aplikacyjnego

`SitePrintSettings` (`company_print_name`, `site_print_name`, `base_regime`, `work_code_intervals`, `reserve_hours`) żyją tylko w `rota.persistence.site_repository` (`get_site_print_settings` / `save_site_print_settings`).

`generate_schedule_pdf` **czyta** je przez persistence w środku. Publicznego `get_` / `update_` w `rota.application` nie ma. `update_site` rusza `Site.display_name` / `active`, nie nazw druku. `period_label` jest argumentem wywołania PDF, nie stanem Site.

T020: koordynator ustawia te wartości w Rocie, nie w PDF. Bez wrappera T021 albo łamie granicę „UI nie importuje persistence”, albo nie ma ekranu ustawień wydruku.

### G2 — brak odczytu listy `CalendarDay`

Zapis: `set_calendar_day` (jeden dzień). Completeness: `month_plan_readiness.missing` jako stringi `"missing CalendarDay for YYYY-MM-DD"`.

Nie ma `list_calendar_days` po stronie application. `open_month` / `assemble_planning_state` przy braku choć jednego dnia rzucają `IncompleteCalendarData` — **nie da się otworzyć ekranu miesiąca, żeby dokończyć kalendarz**. Panel musi pisać w ciemno albo importować persistence.

Kalendarz jest store-global (klucz = data, nie Site) — to T011-A, nie defekt. Write z Site A widać na Site B.

### G3 — PRECHECK wymusza `PlanningState`

`precheck(state)` nie bierze `conn`. Jedyna publiczna droga to `assemble_planning_state` → typ z `rota.planning.state`. T019b: UI nie importuje `rota.planning`. Albo T021 dostaje cienki wrapper `precheck_month(conn, site_id, month)`, albo granica jest już nieszczelna.

### G4 — `current_decision_required` przecieka typ planning

`DecisionRequiredReadback.payload: DecisionRequiredPayload` (`rota.planning.engine_types`). `EmployeeAvailabilityMatrix.rule_applicability` używa `SiteRuleApplicability` z `rota.planning.state`. T021 nie złoży tych ekranów bez importu planning albo bez dodatkowej warstwy DTO.

### G5 — `save_site_membership` jest publicznym zapisem bez guarda

Dokumentowane jako hak `on_success` / punkt patchowania testów. UI, które to zobaczy, ominie `require_active_coordinator_context` i T019b. To nie jest operacja ekranu.

### G6 — backup bez restore (świadome)

`backup_database` / `build_diagnostic_zip` istnieją. Odtworzenie jest procedurą poza aplikacją (T011 B-4=W3). Luka tylko wtedy, gdy T021 rysuje przycisk „przywróć kopię”.

---

## 3. Niedokładności już w kodzie / briefach (nie w T021)

### I1 — cztery różne „obsady” tego samego Site

| Źródło | Kto wchodzi |
|--------|-------------|
| `current_roster` | `enabled=True`, **LOCAL i EXTERNAL** |
| `coordinator_context_completeness` / `month_plan_readiness` (target warnings) | `enabled=True` **i** `LOCAL` |
| `open_month` / assembler | **wszystkie** memberships Site, także `enabled=False` |
| `analytics_for_site_month` | `enabled=True` **i** `LOCAL` |
| PDF | `enabled LOCAL` **∪** pracownicy, którzy mają komórkę pracy w miesiącu (`seen_employee_ids`) |

EXTERNAL, który przepracował zmianę na Site, może być na PDF i w `open_month`, a nie mieć wiersza Analityki (WINDOW-03). `current_roster` pokaże EXTERNAL enabled, Analityka nie. T019 §2.5 każe to nazwać; kod sam tego nie spina.

### I2 — godziny: Analityka / `open_month` ≠ PDF

- T019: `hours_scope=ALL_SITES`. `planned_hours` / saldo to praca Employee ze **wszystkich** modelowanych Site.
- T020: PLAN/WYK/urlop/L4 na wydruku to godziny **tego** Site.
- `open_month.work_balances` to ten sam globalny `WorkBalance` (brak `site_id`).
- PDF `plan_hours` to kody pracy + litery absencji, nie interwał `WorkBalance.planned_hours`.

Te same etykiety „godziny PLAN” na dwóch ekranach to dwa rachunki. T019 i T020 to już mówią; powiązanie w kodzie **nie** jest 1:1 i nie ma wspólnego DTO.

### I3 — `months_with_schedule` jest węższe niż decyzja B-6=W1

Właściciel (T011): miesiące z wskaźnikiem current.  
Kod: current **oraz** ≥1 Assignment. Pusty root po `plan_month` (przed `select_candidate`) nie wchodzi na listę. Nawigacja „gdzie jest grafik” nie pokaże miesiąca, w którym PLAN utworzył wersję i padł na DECISION_REQUIRED / nie wybrano kandydata. `open_month` taki miesiąc nadal otworzy (jest current).

### I4 — klucz miesiąca nie jest wspólny

Wymagają `month.day == 1`: `month_plan_readiness`, `analytics_for_site_month`, `current_decision_required`, `generate_schedule_pdf`.  
`open_month` / `assemble_planning_state` **nie** sprawdzają dnia: kalendarz liczą z `year/month`, ale lookup wersji idzie po przekazanym `date`. `date(2026,8,15)` na Analityce/PDF pada; na `open_month` może nie trafić w wersję zapisaną jako `2026-08-01`.

### I5 — `quarter_balance` vs Analityka

`balance_read.quarter_balance` jest fail-closed na brak `target_hours` **któregokolwiek** z trzech miesięcy kwartału (w tym przyszłych) — pusta lista + warning.  
T019 degraduje: miesiąc może być `AVAILABLE`, kwartał `MONTH_AVAILABLE_QUARTER_UNAVAILABLE`.  
Ekran miesiąca (`open_month.work_balances`) liczy carry-in tylko do planowanego miesiąca włącznie (T011 B-5). Trzy wejścia, trzy semantyki „salda kwartału”.

### I6 — `revalidate` vs `select_candidate` (aktor)

`select_candidate` wymaga jawnego `coordinator_id` (`MissingCoordinatorActor`).  
`revalidate` ma `coordinator_id=None` i spada na `created_by` wersji. Ten sam ekran „działania na grafiku” nie może założyć jednej reguły aktora.

### I7 — `active_sites_for_coordinator` nie filtruje nieaktywnego koordynatora

T011-B W3: start = `active_coordinators` **potem** `active_sites_for_coordinator`. Druga funkcja sama nie sprawdza `Coordinator.active`. Złożenie w złą stronę pokaże obiekty koordynatora, którego nie ma na liście wejścia.

---

## 4. Czy powiązania między ekranami trzymają się w kodzie?

**Trzymają się** (wspólny magazynek, jawne klucze, świadome rozdzielenie ścieżek):

1. `open_store` → jeden `conn` → wszystkie operacje. Nie ma osobnego stanu sesji UI (T009).
2. Pierwsza konfiguracja vs późniejsza edycja: `bootstrap_or_resume_*` rzuca `CoordinatorContextAlreadyActive`, gdy `require_active_coordinator_context` już przechodzi. Panel nie może „bootstrapować” istniejącego obiektu.
3. `update_site` nie przepina `profile_id` — to zostaje na bootstrapie.
4. PLAN / REPLAN zapisują albo czyszczą bieżące `DECISION_REQUIRED`. `current_decision_required` czyta to po restarcie. `select_candidate` / korekty / finalize / restore **unieważniają** wskaźnik. Powiązanie pytanie → czynność jest tylko gdy UI przekaże `responds_to_decision_required_id`; kod **nie** zgaduje z kolejności (T019b).
5. Korekta / NN / freeze / szkolenie robią dziecko ScheduleVersion, nie REPLAN. PDF składa dzień z lineage `effective_from`, nie z „parent=PLAN, child=WYK”.
6. `finalize` wymaga dokładnego zbioru świeżych Deviation — ekran nie może potwierdzić starej listy z `open_month` bez ponownego odczytu.
7. `mark_not_worked` to NN na PLANNED PRIMARY; readiness po `mark_training_realized` nie zmienia eligibility (T010 §9).
8. Brak `target_hours` nie blokuje `month_plan_readiness.ready`; blokuje pełny kwartał w `quarter_balance` i degraduje T019.
9. Kalendarz i `target_hours` są globalne względem Site: zapis z jednego obiektu widać na Analityce / PLAN innych obiektów. `set_calendar_day` ustawia `affected_site_ids` na wszystkie Site; `set_target_hours` na Site, na których Employee ma membership.

**Nie trzymają się** (ten sam byt, inne znaczenie na sąsiednim wejściu):

1. Obsada — I1. Przejście Panel → miesiąc → Analityka → PDF zmienia skład ludzi bez zmiany `site_id`.
2. Godziny — I2. Przejście Analityka ↔ PDF / `open_month` nie zachowuje liczby.
3. Lista miesięcy — I3. Miesiąc z otwartym DECISION_REQUIRED po pustym PLAN może zniknąć z nawigacji, choć `open_month` i `current_decision_required` go widzą.
4. Klucz `month` — I4.
5. Odczyty bez guarda (`open_month`, Analityka, PDF, matryca, pamięć, roster, miesiące). Zapis wymaga `(coordinator_id, site_id)`. Autoryzacja „ten koordynator widzi ten obiekt” jest po stronie UI, nie API.
6. PRECHECK i payload DECISION_REQUIRED — G3/G4. Ekran miesiąca nie jest zamknięty w application DTO.
7. Wydruk — G1. Ekran ustawień PDF nie ma pary z `generate_schedule_pdf`.
8. Kalendarz — G2. Panel nie ma read modelu dni; ekran miesiąca pada, gdy dni brakuje.

---

## 5. Funkcje publiczne, których T021 raczej nie powinien wołać wprost

Jeśli T021 obiecuje „tylko gotowe application API”:

- `assemble_planning_state`, `generate_profile_demands`, `resolved_rule_version_ids`
- `category_for_rule`, `materialize_deviations`
- `save_site_membership`
- `require_active_coordinator_context`, `require_real_date`
- `PLAN_PRIORITY`, `BLANK` (stałe rendererów PDF)
- `quarter_balance` obok T019 — drugi, ostrzejszy kontrakt salda; nie zamieniać z `analytics_for_site_month`

To nie są luki ekranów. To powierzchnia, którą UI może przypadkiem potraktować jako „publiczne przyciski”.

---

## 6. Werdykt

| Pytanie | Stan |
|---------|------|
| Każda publiczna funkcja `rota/application/*.py` zestawiona? | Tak — §1, SHA `e05dfb7`. |
| Co T021 pominął? | **Zablokowane** — brak `arch/T021_spec.md`. Luki API vs T010/T019/T020: G1–G6. |
| Co T021 opisał niedokładnie? | **Zablokowane**. Niedokładności kodu vs wcześniejsze briefy: I1–I7. |
| Czy powiązania ekranów trzymają się w kodzie? | Wspólne klucze i cykl PLAN→pytanie→czynność **tak**. Obsada, godziny, lista miesięcy, klucz `month`, wydruk i kalendarz **nie** są jednym modelem między wejściami. |
| Lista z `REQUEST.md` odjęta? | Nie — pliku nie było. G1–G6 i I1–I7 do ręcznego odjęcia. |

Żeby domknąć audyt T021: wstawić `arch/T021_spec.md` i `REQUEST.md` do repo (albo wkleić). Wtedy da się oznaczyć każdy ekran specu jako pokryty / pominięty / niedokładny i skreślić to, co Paweł już znalazł.
