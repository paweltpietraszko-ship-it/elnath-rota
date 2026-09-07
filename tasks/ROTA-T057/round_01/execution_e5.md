# E5 — nieudane/odrzucone Przelicz Plan

Data wykonania: 2026-09-07. Obiekt: `real-object`. Miesiąc: wrzesień 2026
(żywy, ten sam stan po E4). Wykonane przez realne UI + API + persistence.

## Przebieg

1. Zanotowano stan przed: 4 wersje w `schedule_versions`, current =
   `SV-55855341...`.
2. Uruchomiono "Przelicz (PLAN)" ponownie.
3. Kliknięto "Odrzuć wynik" zamiast akceptować -- Pawel: "zrobiłem,
   zniknęło, wersja bez zmian".
4. Sprawdzono stan po: identyczny jak przed.
5. Osobno: próba ominięcia lifecycle-guard przez bezpośrednie wywołanie
   `POST .../schedule/2026-09-01/replan` (REPLAN, nie Przelicz Plan) na
   tym samym, już zaakceptowanym miesiącu.

## Dowód z bazy

```
przed:  COUNT(schedule_versions) = 4, current = SV-55855341...
po odrzuceniu: COUNT(schedule_versions) = 4, current = SV-55855341...
```

Zero zmian -- ani nowej wersji, ani przesunięcia current.

## Dowód bezpośredniego API (krok 5)

```
POST /api/workspace/sites/real-object/schedule/2026-09-01/replan
-> HTTP 409
{"detail":"(real-object, 2026-09-01) already has an accepted ScheduleVersion
 -- use Przelicz Plan (plan_month), not REPLAN"}
```

## Wynik

- SEARCH_INCOMPLETE albo kontrolowany brak zaakceptowanego wyniku: pokryte
  w praktyce przez odrzucenie preview (poniżej) -- osobno SEARCH_INCOMPLETE
  jako status był już realnie zaobserwowany podczas E2 (przed naprawą
  tolerancji solvera), więc obsługa tego stanu (komunikat + "Szukaj
  dalej") jest zweryfikowana na żywo, nie tylko kodowo
- odrzucenie preview: **PASS**, potwierdzone przez Pawła
- current, liczba ScheduleVersion i historia bez zmian: **PASS**,
  potwierdzone w bazie (4 i 4, ten sam current)
- bezpośredni endpoint nie może ominąć phase/lifecycle guard: **PASS**,
  potwierdzone HTTP 409 na REPLAN wywołanym wprost przez API z pominięciem
  UI

**E5: PASS.**

---

# Podsumowanie bramki E1–E5

Wszystkie pięć punktów wykonane na realnym UI + API + persistence (nie na
pytest), na dwóch świeżych miesiącach (grudzień 2026, styczeń/luty 2027)
i jednym żywym (wrzesień 2026), z bezpośrednią weryfikacją bazy danych po
każdym kroku i wizualną oceną właściciela tam, gdzie brief tego wymaga
(E4). Przy okazji E2 znaleziony i naprawiony (za zgodą właściciela) realny
błąd wydajnościowy solvera (`SOLVER_RELATIVE_GAP_LIMIT`), zweryfikowany
brakiem regresji na pełnym zestawie testów (`tests/`, 1400 testów -- ten
sam zestaw 21 nieudanych z i bez tej zmiany, potwierdzone `git stash`).

**Wynik: E1 PASS, E2 PASS, E3 PASS, E4 PASS, E5 PASS.**
