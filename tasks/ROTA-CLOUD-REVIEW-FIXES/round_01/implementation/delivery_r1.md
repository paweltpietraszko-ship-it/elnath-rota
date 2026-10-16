# ROTA-CLOUD-REVIEW-FIXES — dostawa CC, runda 1

BRANCH: task/ROTA-CLOUD-REVIEW-FIXES · BASE: 8512553 (brief zamrożony na main) · HEAD: 530f0d7
Brief: tasks/ROTA-CLOUD-REVIEW-FIXES/brief.md (precheck Codexa r1 PASS + r2 po ocenie CC).

## Bramka (backend.py, dosłownie: round_01/implementation/backend_r2.txt)
STATUS: FAIL. Klasyfikacja każdej pozycji (decyzja należy do Ownera/architekta, nie CC):
- NEW_FILES 8 (max 2): wszystkie 8 nazwane wprost w TASK_SCOPE briefu (formatter F6, 2 testy,
  e2e, .railway/railway.ts, README, package.json, package-lock.json). Twardy limit 2 jest
  domyślną kalibracją drobnych poprawek; brief nie ma pola do jego podniesienia.
- SIZE_FILE (wszystkie pięć plików było >600 PRZED zmianą): plan_ops.py 826→845,
  schedule.py 758→784, test_t012 1744→1746, test_t017 612→625, test_t022 651→664.
- SIZE_FUNC bez zmiany rozmiaru (plik dotknięty gdzie indziej): apply_manual_correction 85,
  _check_third_consecutive_shift 82, test_m29 54. Urosły, ale były >50 już przed:
  plan_month 132→135, get_month 78→92 (okablowanie F6). Dwie funkcje testowe, które
  przekroczyły 50 przez CC, skrócono w 530f0d7.
- RATIO / TOTAL_LINES (WYMAGA_DECYZJI): blok 7 poprawek + IaC + testy, zgodnie z briefem.

## Dowody (uruchomione)
- Pełna suita raz na końcu (A9): `.venv\Scripts\python.exe -m pytest tests -q` →
  **1516 passed, 1 skipped, 0 failed** (przed blokiem: 34 failed / 1465 passed).
- Nowe testy: tests/test_cloud_review_schedule_fixes.py (15), tests/test_cloud_review_password_change.py (3),
  frontend/e2e/cloud-review-fixes.spec.ts (1, Playwright, prawdziwa przeglądarka) — wszystkie zielone.
- Mutacje (cofnięcie poprawki → test pada): F1, F3, F4, F6 (pytest i e2e), F7 (oba strażniki),
  F2 (cofnięcie obu połówek; każda połówka osobno wystarcza do odcięcia starej trójki).
- Frontend: `tsc -b` + `vite build` czyste. ruff czysty na zmienionych plikach.
- test_t024 404/405 sprawdzony z obecnym i bez `frontend/dist`.

## NOT_CHECKED / PARTIAL
- A2/F5 w kontenerze: brak Dockera na tej maszynie → NOT_CHECKED. Do sprawdzenia po wdrożeniu:
  `railway ssh date` (czas polski), ręczna korekta trwającej służby o 06:30.
- A8/R: przygotowane i sprawdzone `railway config plan` (tylko odczyt): `0 to add, 1 to change,
  0 to destroy` (build.builder → DOCKERFILE). `apply` NIE uruchomiony (wymaga zgody Ownera).
- A7 UI zmiany hasła: formularz istnieje tylko w trybie z logowaniem; e2e działa w trybie
  lokalnym → UI sprawdzone kompilacją, zachowanie API testami w trybie CENTRAL_SERVICE.

## Kluczowe ustalenie R (Railway)
Builder samego serwisu to RAILPACK; Dockerfile wymusza tylko railway.json. Plik z
`railway config migrate` (a) zostawia Dockerfile jako komentarz, (b) pomija zmienne/dysk/repo —
plan takiego pliku: usuń 6 zmiennych (w tym ROTA_CENTRAL_KEK), odepnij /data, odepnij repo.
Gotowy plik = `config pull` + jawny DOCKERFILE. railway.json celowo NIE usunięty w tym branchu.
Kolejność przejścia: deploy/RAILWAY.md „Migracja z railway.json”.

## Testy zmienione (klasa T): test → obowiązujący kontrakt → powód
- r15, r25, t010_r5_b, replan_minimal_reshuffle, t010_day_only_n_exception, t013, t017, t022:
  lokalny wrapper base_state z OCHRONA → T065 brief §8 / dn_semantics_apply (D/N i DAY_ONLY
  tylko OCHRONA) → domyślny obiekt minimal_state to ORDINARY. Wzór z test_site_rules_execution.
- t010_r3, t012 (po jednym teście), rota_generic_month, manual_audits: przypięcie OCHRONA
  tylko w testach DAY_ONLY (globalny wrapper w t012 psuł inny test → wycofany).
- t009_r4 [day-only]: korekta reżimu przez audytowaną durable_inputs.correct_site_planning_regime.
- site_memory_decision_ledger, site_profile_persistence, site_rules_execution: kontrola importów
  przez ast zamiast szukania tekstu (availability.py ma ścieżkę tylko w komentarzu).
- t021_screen2_r12/r13: log absencji przeniesiony do EmployeeAvailability.tsx.
- t026_18: kanoniczny właściciel absencji w schedule_projection; brak _winning_days w obu modułach.
- t023_54: usunięty jednorazowy, zużyty dowód git-diff (brief T).
- t024 no_wide_users: ROTA_FRONTEND_DIST na nieistniejący katalog (wynik niezależny od dist).
- t024 password_change: kontrakt F7 (current_password).
- excel_external_api target_hours: bramka tylko ORDINARY (OWNER 2026-09-20) → korekta reżimu.

## Zgłoszenie poza zakresem (nie naprawiane)
`deviation_mapping._BUILTIN_RULE_CATEGORY` nie ma też ROLE-01, WORK_PERIOD-01, FULL_HOUR-01,
SITE_RULE-01, ASSIGN (walidator je emituje) → ręczna korekta łamiąca np. wymaganą rolę w sklepie
prawdopodobnie kończy się tym samym 500 co F1. Ustalone z kodu, nie uruchomione. W BOARD.md.
