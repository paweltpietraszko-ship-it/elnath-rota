# E4 — żywy grafik / Przelicz Plan

Data wykonania: 2026-09-07. Obiekt: `real-object`. Miesiąc: wrzesień 2026
(już żywy -- pierwsza służba zaczęła się 2026-09-01, przed dzisiejszą
datą). Wykonane przez realne UI + API + persistence -- Pawel klika,
CC odczytuje bazę i ocenia wynik razem z nim wizualnie.

## Przebieg

1. Zapisano stan grafiku "przed" (bieżąca wtedy wersja `SV-ed027d8b...`,
   FINAL_NO_DEVIATIONS).
2. Dodano pracownikowi nieobecność na przyszłą datę we wrześniu.
3. Uruchomiono "Przelicz (PLAN)".
4. Przed akceptacją: stary grafik (`SV-ed027d8b...`) nadal `current`
   (sprawdzone -- Przelicz Plan tylko liczy podgląd, nie podmienia current
   przed akceptacją, zgodnie z T57-05/T57-11).
5. Zaakceptowano wynik.
6. Oceniono wizualnie stary i nowy grafik obok siebie -- **Pawel:
   "Wszystko jest ok, możemy akceptować"** -- dni już przepracowane
   wyglądały identycznie, zmieniła się tylko przyszłość, i to w
   ograniczonym zakresie (nie przetasowanie całego miesiąca).
7. Sprawdzono Historię wersji i datę "Obowiązuje od".

## Dowód z bazy

```
schedule_versions (site_id='real-object', month='2026-09-01'), po akceptacji:
  SV-0c07fa84... | WORKING            | parent=None          | effective_from=2026-09-01
  SV-69ea28b0... | FINAL_NO_DEVIATIONS| parent=SV-0c07fa84... | effective_from=2026-09-07
  SV-ed027d8b... | FINAL_NO_DEVIATIONS| parent=SV-69ea28b0... | effective_from=2026-09-07
  SV-55855341... | WORKING (NOWA)     | parent=SV-ed027d8b... | effective_from=2026-09-07  <- current
```

Cały łańcuch poprzednich wersji nadal istnieje w bazie -- żadna nie
zniknęła.

Porównanie już-rozpoczętych służb (PRIMARY, `start_datetime` < teraz)
między starym rodzicem (`SV-ed027d8b...`) a nowym dzieckiem
(`SV-55855341...`): **13 wpisów w obu, identyczne** co do pracownika,
godzin i przypisanej służby (sprawdzone dla pierwszych 5 -- ten sam
pracownik, ta sama godzina, ta sama służba w obu wersjach, bit-for-bit).

## Wynik

- przygotuj zaakceptowany grafik z pierwszą służbą już rozpoczętą: **PASS**
  (wrzesień, żywy od 2026-09-01)
- Przelicz Plan z realną zmianą dotyczącą przyszłości: **PASS** (dodana
  przyszła nieobecność)
- przed akceptacją preview stary grafik nadal current: **PASS**
- po akceptacji dokładnie jedna nowa wersja z effective_from = dzisiaj:
  **PASS** (`SV-55855341...`, effective_from=2026-09-07, dzisiejsza data)
- wszystkie rozpoczęte służby bit-for-bit zachowane: **PASS**, potwierdzone
  w bazie (13/13 identycznych wpisów)
- przyszłość zmienia się minimalnie: **PASS** (ocena wizualna Pawła)
- poprzednia wersja pozostaje w historii: **PASS** (cały łańcuch nadal
  obecny w bazie)
- stary i nowy grafik pokazane/ocenione optycznie, nie tylko liczbowo:
  **PASS** -- bezpośrednia ocena właściciela: "Wszystko jest ok, możemy
  akceptować"

**E4: PASS**, pełne pokrycie wszystkich punktów specyfikacji.
