# BRIEF DLA ARCHITEKTA — SICK_LEAVE ZNANE Z WYPRZEDZENIEM POTRZEBUJE ŚCIEŻKI PRE_PLAN

**Stan:** ZGŁOSZENIE ZNALEZISKA — CC READ-ONLY, NIE READY FOR IMPLEMENTATION.
**Źródło:** Symulator Koordynatora (ROTA-T038), znalezisko z realnego
uruchomienia, nie z inspekcji kodu na sucho.
**BASE_MAIN_SHA:** `37e32da6244e4e43f504ef44b9b5a290f05a21b7`.

## 1. Zamrożone założenie, które właściciel dziś koryguje

`tasks/ROTA-T023/round_01/OWNER_DECISION_ABSENCE_TIMING_PLAN_WYK.md`,
sekcja 3 (decyzja z 2026-08-22, ACCEPTED OWNER DECISION):

> "Sickness is not planned in advance."

To założenie zostało wprost zakodowane w
`arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md` sekcja 2:
`PRE_PLAN_LEAVE` (brak zaakceptowanego planu nie jest błędem, dekompozycja
na godziny robocze) istnieje wyłącznie dla `LEAVE_GRANTED`; `SICK_LEAVE`
ma tylko `POST_PLAN_REFERENCE`, które wymaga już zaakceptowanego planu.

**Owner correction, 2026-08-28** (rozmowa, werbatim): koordynator, który
wie że pracownik jest np. na 3-miesięcznym zwolnieniu lekarskim, zaznacza
to chorobowe na cały okres PRZED zrobieniem planu na dany miesiąc —
dokładnie tak samo jak zna urlop z wyprzedzeniem. Różnica między
`LEAVE_GRANTED` a `SICK_LEAVE` istnieje tylko dla PRAWDZIWIE nagłej
sytuacji: kto zachoruje W TRAKCIE, gdy plan na ten miesiąc już istnieje —
to zostaje `POST_PLAN_REFERENCE`, bez zmian. Sam fakt, że coś nazywa się
"chorobowe" a nie "urlop", nie implikuje, że jest nieznane z wyprzedzeniem.

## 2. Dokładne miejsce w kodzie

`rota/persistence/absence_reference_repository.py:308-326`, funkcja
`_resolve_no_accepted_plan_day`:

```python
def _resolve_no_accepted_plan_day(
    conn: sqlite3.Connection, kind: AvailabilityKind, the_date: date, month_cache: dict[date, dict[date, bool]],
) -> DayReference:
    """... Frozen addendum section 2.1: this is legitimate PRE_PLAN
    territory for LEAVE_GRANTED, never MISSING. SICK_LEAVE has no pre-PLAN
    path (frozen addendum section 2): with no accepted plan anywhere in
    scope, the reference is incomplete."""
    if kind == AvailabilityKind.LEAVE_GRANTED:
        month_start = date(the_date.year, the_date.month, 1)
        holiday_by_date = _month_holiday_map(conn, month_start, month_cache)
        is_workday = the_date.isoweekday() <= 5 and not holiday_by_date.get(the_date, False)
        hours = _PRE_PLAN_HOURS_PER_WORKDAY if is_workday else 0
        return DayReference(the_date, SOURCE_PRE_PLAN_LEAVE, STATUS_BOUND, hours, ())
    return DayReference(the_date, SOURCE_POST_PLAN_REFERENCE, STATUS_MISSING, None, ())
```

To jedyna, jawna, świadoma rozgałęź decyzyjna między dwoma rodzajami
absencji dla przypadku "brak zaakceptowanego planu w ogóle". Dalej ta
`MISSING` referencja trafia do `rota/planning/absence.py::_require_bound`
(linia ~166), które fail-closed rzuca `IncompleteAbsenceReferenceError` —
nigdzie po drodze złapane w warstwie API, więc kończy jako goły HTTP 500
(`api/errors.py`'s `to_http_exception` fallback: "unexpected error: ...").

## 3. Dowód z realnego uruchomienia

Symulator (`tests/property/`) zaznaczył `SICK_LEAVE` dla pracownika PRZED
pierwszym `PLAN` dla obiektu, bez żadnej wcześniejszej wersji harmonogramu:

```
POST /api/workspace/employees/{id}/availability {"kind": "SICK_LEAVE", ...}
POST /api/workspace/sites/{id}/schedule/2026-09-01/plan {"effective_from": "2026-09-01"}
→ 500 {"detail":"unexpected error: 2026-09-12: MISSING accepted reference for SICK_LEAVE (POST_PLAN_REFERENCE)"}
```

Kontrast — ten sam mechanizm, `SICK_LEAVE` dodane PO `select-candidate`
(plan już zaakceptowany), potem `REPLAN`: zwraca poprawnie `FEASIBLE`, bez
błędu. To potwierdza, że `POST_PLAN_REFERENCE` ścieżka działa poprawnie
tam, gdzie jest zamierzona — luka jest wyłącznie w przypadku "brak planu
w ogóle" dla `SICK_LEAVE`.

## 4. Zakres wpływu (do oceny architekta, nie rozstrzygnięte tutaj)

- `_resolve_no_accepted_plan_day` — czy `SICK_LEAVE` ma dostać tę samą
  gałąź co `LEAVE_GRANTED` (te same `_PRE_PLAN_HOURS_PER_WORKDAY`), czy
  osobną stałą/rachunek.
- `arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md` sekcja 2 —
  wymaga aktualizacji (rozszerzenie `PRE_PLAN_LEAVE` na `SICK_LEAVE`
  "znane z wyprzedzeniem", pozostawienie `POST_PLAN_REFERENCE` tylko dla
  faktycznie nagłej sytuacji w trakcie trwającego planu).
- T020 (`schedule_export.py`) — czy prezentacja WYK dla pre-PLAN
  `SICK_LEAVE` ma być identyczna z `LEAVE_GRANTED` (`U1/U1/U2` wzorzec) czy
  własny symbol (koordynator w tej sesji wspomniał "D/C, N/C" jako
  intuicję, niepotwierdzoną w żadnym istniejącym dokumencie legend — do
  ustalenia z architektem, nie założone tutaj).
- Solver TARGET/fairness (SICK-only SOFT ranking, `rota/planning/absence.py`
  komentarz o `ROTA-REG-001` exact-hours oracle) — czy pre-PLAN SICK_LEAVE
  ma wejść do tego samego mechanizmu co pre-PLAN LEAVE_GRANTED, czy zostać
  wyłączone jak dziś.
- `api/errors.py` — niezależnie od powyższego, `IncompleteAbsenceReferenceError`
  nie jest dziś zmapowany na żaden kod HTTP (spada do 500 fallback) — nawet
  dla ścieżek, gdzie MISSING jest legalnym, oczekiwanym stanem, koordynator
  dostaje nieczytelną awarię zamiast jasnego komunikatu. Wart osobnego
  rozważenia niezależnie od tego, czy zakres pre-PLAN SICK_LEAVE zostanie
  rozszerzony.

## 5. Poza zakresem tego zgłoszenia

- CC nie proponuje konkretnego rozwiązania (stała vs formuła, symbol WYK,
  dokładna treść komunikatu błędu) — to decyzja architekta.
- Symulator T038 na razie NIE testuje pre-PLAN `SICK_LEAVE` (ograniczony
  do już wspieranej ścieżki post-PLAN), z jawną notatką w swoim raporcie
  odsyłającą do tego briefu — nie omija problemu cicho.

## 6. Warunek przekazania

Ten brief jest zgłoszeniem faktów i owner-correction, nie gotowym
TASK_SCOPE. Wymaga: (1) architekt projektuje dokładną zmianę
`_resolve_no_accepted_plan_day` + aktualizację zamrożonego dodatku,
(2) Paweł potwierdza zaprojektowane zachowanie, (3) dopiero wtedy Task ID
i implementacja.
