# OWNER APPROVED ROADMAP — ROTA-T008 do ROTA-T012

STATUS: OWNER_APPROVED_ROADMAP
DATE: 2026-08-12
BASE_MAIN_SHA: e010f004e90a1e4f426bb72298e7307045d32b56
AUDIT_REPORTS:
- tasks/ROTA-ROADMAP-T008-T012/round_01/tests/tests_r1.txt (runda 1: WYMAGA KOREKTY PRZED ZAMROŻENIEM TASK CONTRACTS)
- tasks/ROTA-ROADMAP-T008-T012/round_01/tests/tests_r2.txt (runda 2: PASS — ROADMAP READY FOR TASK CONTRACT AUTHORING)

## STATUS TEGO DOKUMENTU

To jest baza do pisania Task Contracts dla T008–T012, **nie zgoda na
implementację** żadnego z nich. Implementacja każdego zadania wymaga
osobnego, zamrożonego Task Contract i przechodzi przez ten sam proces
audytu co T004–T007.

Ten dokument zastępuje wcześniejszą kolejność i nazwy roadmapy ocenione w
`tests_r1.txt`. Nie zmienia:
- `arch/spec.md`;
- istniejących zamrożonych addendów (`arch/FROZEN_ADDENDUM_REPLAN_MIN_01.md`,
  `arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md` + R1 clarification);
- zaakceptowanych kontraktów T004–T007.

Ten commit **nie tworzy** `tasks/ROTA-T008/brief.md` i **nie zmienia kodu
produkcyjnego**.

## IDENTYFIKATOR AUDYTU VS. NUMER ZADANIA

Raporty audytowe roadmapy używają osobnego identyfikatora
`ROTA-ROADMAP-T008-T012` (przegląd zakresu i kolejności pięciu przyszłych
zadań, nie audyt implementacji). Właściwy numer `ROTA-T008` pozostaje wolny
i zarezerwowany dla pierwszego z nich: LocalStore + ScheduleVersion
lifecycle.

## ZATWIERDZONA KOLEJNOŚĆ

```
T008 LocalStore + ScheduleVersion lifecycle
  -> T009 Application Layer
  -> T010 Natural Language Rule Intake
  -> T011 Backend/Application E2E
  -> T012 Desktop + Desktop E2E
```

## APROBATA WŁAŚCICIELA

Właściciel zatwierdził tę kolejność i ten zakres 2026-08-12, po zamknięciu
wszystkich findingów rundy 1 (RMAP-1 do RMAP-5, `tests_r1.txt`),
potwierdzonym w rundzie 2 (`tests_r2.txt`): **PASS — ROADMAP READY FOR TASK
CONTRACT AUTHORING**.

## KOREKTA WŁAŚCICIELA — HARD

Świadome zatwierdzenie statusu HARD reguły **nie oznacza** obowiązkowego
dodatkowego okna UI ani drugiego, osobnego działania koordynatora.

Jedno normalne działanie koordynatora może jednocześnie stanowić świadome
zatwierdzenie, pod warunkiem że przyszły zamrożony Task Contract T010
jednoznacznie określi:
- skąd wynika `category`/`enforcement`;
- jakie wartości domyślne są jawnie komunikowane koordynatorowi;
- jaki zakres dat (`effective_from`/`effective_to`) obowiązuje;
- co dokładnie zostaje zapisane po wykonaniu tego działania.

Ta korekta nie nakazuje dodatkowej ceremonii UI bez literalnej podstawy w
przyszłym frozen addendum/Task Contract T010.

## CO ZAMKNIĘTO W RUNDZIE 2 (streszczenie, nie nowa treść kontraktowa)

Poniższe punkty streszczają zamknięcia z `tests_r2.txt`; nie dodają nowych
decyzji projektowych ponad to, co tam już zapisano. Szczegóły operacji,
macierze testów i dokładny zakres każdego zadania pozostają do ustalenia w
osobnych Task Contracts.

- **RMAP-1 (kolejność T008 vs T009/T010)** — zamknięte zmianą kolejności na
  powyższą; natural-language intake (T010) nie tworzy własnej orchestration,
  nie zna repository/SQLite i korzysta z gotowego kontekstu oraz
  application command T009.
- **RMAP-2 (niepełny LocalStore)** — zamknięte na poziomie roadmapy: T008
  obejmuje pełny wymagany zakres A17, z zachowaniem istniejących źródeł
  prawdy T004/T005, oraz literalne invarianty ScheduleVersion, current
  reference, Deviation, boundary context, WorkBalance i atomowego zapisu.
- **RMAP-3 (brak testowalnego kontraktu T010)** — zamknięte na poziomie
  roadmapy: T010 otrzyma osobny frozen addendum przed briefem, bounded do
  katalogu T007, fail-closed, bez rozszerzania katalogu i bez uniwersalnego
  DSL lub LLM runtime dependency.
- **RMAP-4 (T011 nazwany "pełną walidacją produktu")** — zamknięte zmianą
  nazwy na Backend/Application E2E; jego PASS oznacza gotowy rdzeń
  aplikacji, nie gotowy desktop.
- **RMAP-5 (T012 pomijał literalne operacje UI)** — zamknięte na poziomie
  roadmapy: T012 wskazuje dokładne, już zamrożone źródło Continuity AI
  (repo `paweltpietraszko-ship-it/continuity-ai`, branch
  `ui/project-report-polish-v0.4`, SHA
  `709cf6a1ff829725e5d6572d286963809c990c4a`) i obejmuje pełną macierz A16,
  desktop bridge oraz E2E przez rzeczywisty bridge/UI.

## NASTĘPNY DOZWOLONY KROK

Przygotowanie zamrożonego Task Contract dla:

**ROTA-T008 — LocalStore + ScheduleVersion lifecycle**

Nie parsera (T010). Nie UI (T012). Implementacja dopiero po osobnym
audycie gotowego briefu, tym samym trybem co T004–T007.
