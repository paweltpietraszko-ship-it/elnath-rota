# BRIEF WYKONAWCZY — AUDYT KODU (WARSTWY A-E)

**Stan:** SKONSOLIDOWANY PO CODEX REVIEW R1-R4 — gotowy do wykonania,
chyba że pojawi się nowe zachowanie widoczne dla właściciela (Codex R4,
sekcja 7). Historia rund: `AUDIT_1_BASELINE_CODEX_REVIEW_2026-08-28.md`
(R1-2, `WYMAGA_KOREKTY`), `AUDIT_1_CODEX_REVIEW_R3_PROPER_CODE_AUDIT_2026-08-28.md`
(R3, metoda wielowarstwowa), `AUDIT_1_CC_COMMENT_ON_R3_2026-08-28.md` (CC:
zakres Warstwy C + priorytet wg dowodu), `AUDIT_1_CODEX_REVIEW_R4_SCOPE_FROM_EVIDENCE_2026-08-28.md`
(R4: rozdzielenie C/D, C-01..C-04 zamknięte, korekta SHA).
**BASE_SHA (poprawiony, R4 finding A1-R2-01):** `d445ee64a0e634c4ca23c2fcc9f6a50b6503d22b`
(`main`, przed `task/ROTA-T040`).

## Podział ról (bez zmian od R3, sekcja 8)

CC zbiera surowe wyniki i kandydatów wywołań mechanicznie. Codex niezależnie
sprawdza TRACE/reachability/reprodukcję/klasyfikację. Architekt projektuje
docelową granicę ownership dopiero na podstawie potwierdzonych faktów.
Właściciel rozstrzyga każdą zmianę widocznego zachowania. Autor kodu (CC)
nie klasyfikuje sam własnych warstw jako potrzebnych.

**Zero napraw, nowych testów i refaktoryzacji w trakcie zbierania dowodów
(wszystkie warstwy A-D). Warstwa E to plan decyzyjny, nie implementacja.**

## Warstwa A — mechaniczny baseline (raz, na BASE_SHA)

Zebrać na dokładnie `BASE_SHA` powyżej:

1. Pełny `pytest` → `tasks/ROTA-AUDIT1/round_01/tests/pytest.txt`.
2. `python -m benchmarks.rota_stress --cases 100 --seed 20260812 --json
   tasks/ROTA-AUDIT1/round_01/tests/rota_stress.json`.
3. `python -m benchmarks.real_object --suite all --json
   tasks/ROTA-AUDIT1/round_01/tests/real_object.json`.

Wynik tej warstwy NIE otrzymuje werdyktu "program poprawny" — oznacza
wyłącznie "tak zachowuje się obecna siatka testowa na tym SHA, przed
zmianami". Benchmark PASS/FAIL to wynik istniejącego narzędzia, nie
PRODUCT_TRUTH.

## Warstwa B — pionowy audyt 11 scenariuszy CM0/CM1

Każdy scenariusz wykonany przez rzeczywisty produkcyjny łańcuch:
`durable input/API → assembler → PLAN/REPLAN → validate → select →
reopen/export/readback` (zakres właściwy dla danego scenariusza) — NIE
przez wyszukanie testu o podobnej nazwie. Wolno dzielić na jawne partie,
zapisując wynik po każdej (Codex R4, sekcja 4) — koszt czasowy (kilka
realnych przebiegów CP-SAT) jest realny i ma zostać nazwany wprost, nie
jest powodem do skrócenia dowodu.

Dla każdego z 10 scenariuszy źródłowych (dosłownie z PR #9 AUDIT-2) — plus
scenariusz 11 poniżej — zapisać: dokładne wejścia koordynatora, źródło
oczekiwania (spec/task/OWNER ruling), produkcyjny entry point, rzeczywisty
status i kandydat/decision payload, wynik niezależnego validate/readback,
komendę i minimalny reproduktor.

1. zwykły realny miesiąc 5 pracowników, D/N, pełne coverage;
2. DAY_ONLY employee nie dostaje N;
3. zgłoszona choroba jednego pracownika w już istniejącym planie → REPLAN
   zachowuje REALIZED/frozen i próbuje naprawić przyszłość;
4. jednocześnie co najmniej jeden dzień wolny/urlop innej osoby;
5. brak personelu → DECISION_REQUIRED, nie TECHNICAL_ERROR i nie fałszywe
   FEASIBLE;
6. rolling 7d > threshold → plan nie kończy jako zwykłe FEASIBLE;
7. REST boundary między miesiącami;
8. restart/reopen → current schedule rekonstruuje się identycznie;
9. manual correction → nowa wersja, poprzedni FINAL nie jest mutowany;
10. invalid model/config → TECHNICAL_ERROR, nie decyzja kadrowa;
11. **Wrzesień 2026, OCHRONA, jedna codzienna zmiana H24 06:00-06:00,
    pięciu aktywnych LOCAL, target 176h, wszyscy dostępni, bez dodatkowych
    reguł i wcześniejszego grafiku → PLAN zwraca FEASIBLE, a kandydat
    przechodzi produkcyjny `validate()`.** Nie rozszerzać do "H24 nigdy
    nie zwraca DECISION_REQUIRED" — przy absencji/regule taki wynik może
    być prawidłowy.

**Zasada baseline'u (Codex R4, sekcja 5): scenariusz 11 na `BASE_SHA`
(przed T040) oczekiwanie zapisuje FAIL/DECISION_REQUIRED jako fakt —
to jest baseline, nie coś do "poprawienia" przed zapisem. Po zamknięciu
i mergu T040 wolno zrobić osobne porównanie before/after, ale nie wolno
uruchomić AUDIT-1 na nowszym kodzie i nadal podpisać go starym BASE_SHA.**

Format: `tasks/ROTA-AUDIT1/round_01/tests/vertical_scenarios.md`, jeden
wpis na scenariusz. Nieudany scenariusz zapisuje się i przechodzi do
następnego — brak pokrycia nie uruchamia automatycznie pisania testu.

## Warstwa C — cztery zamknięte, potwierdzone incydenty (Codex R4, sekcja 3)

Zamknięty zakres. Żadna pozycja SUSPECT z PR #9 bez własnego odtwarzalnego
incydentu nie wchodzi tutaj — idzie do Warstwy D.

**C-01 — H24 fałszywie niewykonalne.** Wejście: zwykły obiekt H24, 5
LOCAL, wrzesień 2026. Objaw: PLAN zwraca DECISION_REQUIRED mimo
istniejącego HARD-valid świadka. Potwierdzona przyczyna:
`fairness.add_dn_rhythm_reward()` używa licznika occupancy `2*x` jak
Boolean, tworząc przypadkowy zakaz HARD. Mylące etykiety
NIGHT-STREAK-01/REST-01 to skutek tego samego UNSAT, nie osobny incydent.
Źródło: `ARCHITECT_BRIEF_NIGHT_STREAK_24H_FALSE_POSITIVE_2026-08-28.md`,
`tasks/ROTA-T040/brief.md`.

**C-02 — SICK_LEAVE znane przed pierwszym PLAN kończy jako HTTP 500.**
Potwierdzony pionowy reproduktor. CLASS nie jest z góry przesądzone jako
przerost `absence_reference_repository.py` — może być defekt, brak
kontraktu lub konieczna złożoność; CLASS wynika dopiero z TRACE/ownership.
Źródło: `ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md`.

**C-03 — legalne nakładające się demandy dają fałszywy COVERAGE-01
excess.** Generator katalogu jawnie dopuszcza niezależne nakładające się
occurrence; validator liczy geometryczne nakładanie assignmentów dla
każdego demandu osobno. Osobny incydent validatora/kontraktu coverage,
niezwiązany z C-01. Źródło: `tasks/ROTA-T039/brief.md`.

**C-04 — zapis katalogu po utworzeniu WORKING nie odświeża readbacku.**
Potwierdzone na produkcyjnym przepływie. PLAN liczy świeżo w pamięci, ale
bieżąca wersja nadal odczytuje stare persisted demands. Oczekiwane
zachowanie wymaga OWNER_DECISION, ale sam rozjazd read/write jest
odrębnym, udokumentowanym incydentem. Źródło:
`ARCHITECT_BRIEF_SHIFT_CATALOG_STALE_WORKING_VERSION_2026-08-28.md`.

Dla każdego C-01..C-04: wypełnić pełną tabelę CLAIM/TRACE/ENTRYPOINT/
REACHABILITY/REPRO/USER EFFECT/OWNER/CLASS (Codex R3, sekcja 5) w
`tasks/ROTA-AUDIT1/round_01/tests/pr9_findings_c01_c04.md`.

## Warstwa D — strukturalny remanent wszystkich pozycji SUSPECT z PR #9

Bez własnego odtwarzalnego incydentu (jeśli Warstwa D ujawni konkretny
błąd, powstaje NOWY wiersz Warstwy C z dowodem, nie wcześniej). Dla
każdej pozycji SUSPECT z `START_HERE_CODE_INVENTORY_AUDIT_2026-08-28.md`
(ok. 15-18 pozycji: `replan_reshuffle.py`, engine.py fallback stages,
multi-alternative search, `durable_inputs.py`, `rule_decisions.py`,
`deviation_mapping.py`, `training.py`, `decision_ledger.py`,
`site_memory.py`, `absence_reference_repository.py` — jeśli nie już
zamknięte jako C-02, `work_balance_repository.py`,
`site_rule_repository.py`+`site_rule_assembly.py`, analytics/history UI):
kto jest jedynym właścicielem reguły, ilu ma konsumentów produkcyjnych,
czy istnieje równoległa implementacja tej samej decyzji, czy kod służy
wyłącznie testom/benchmarkowi, czy usunięcie naruszyłoby safety/recovery/
auditability. Klasyfikacja: `KEEP / DUPLICATE / DEAD / TEST_ONLY / DEFECT /
OWNER_DECISION`.

Format: `tasks/ROTA-AUDIT1/round_01/tests/suspect_inventory.md`.

## Warstwa E — plan redukcji (decyzyjny, bez zmian kodu)

Dopiero po B-D. Kolejność: (1) kod DEAD bez konsumentów/kontraktu, (2)
duplikaty ze wskazanym jednym właścicielem, (3) nieużywane pola/endpointy/
stany UI, (4) zbędne testy historyczne po usunięciu przedmiotu, (5)
większe połączenia odpowiedzialności wyłącznie po decyzji właściciela.
Każda porcja: dokładny zakres plików, zachowanie które ma pozostać
identyczne, pionowe reproduktory przed/po, pełna regresja jako siatka
końcowa (nie dowód architektury), brak jednoczesnego dodawania funkcji.

**Ten brief kończy się na Warstwie D. Warstwa E to osobna decyzja
właściciela po zamknięciu A-D, nie część tego wykonania.**

## Warunek uruchomienia

Ten brief jest gotowy do wykonania (Codex R4: "nie potrzeba kolejnej rundy
projektowania"). `task_init.py ROTA-AUDIT1` przed startem Warstwy A.
`backend.py` nie dotyczy Warstw A-D (brak zmian w kodzie produktowym,
tylko raporty).
