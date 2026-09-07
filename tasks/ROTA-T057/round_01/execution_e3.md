# E3 — zaakceptowany, ale nieżywy

Data wykonania: 2026-09-07. Obiekt: `real-object`. Miesiąc: luty 2027
(świeży). Wykonane przez realne UI + API + persistence.

## Przebieg

1. Zaplanowano i zaakceptowano luty 2027 -> wersja robocza `SV-c9eed7d5...`,
   ustawiona jako current.
2. Kliknięto "Usuń" -> ekran wrócił do "Brak grafiku na ten miesiąc".
3. Uruchomiono PLAN od nowa i zaakceptowano nowy wynik -> nowa wersja
   `SV-1cde8575...`.
4. Sprawdzono "Historia wersji": stara wersja (`SV-c9eed7d5...`) **nie
   pojawia się** -- potwierdzone przez Pawła bezpośrednio ("stara wersja
   zniknęła z historii").
5. Osobno: próba usunięcia bieżącej wersji **żywego** grafiku (wrzesień
   2026, `SV-ed027d8b...`, już obowiązujący) przez bezpośrednie wywołanie
   API (`POST .../schedule/2026-09-01/delete-current`, z pominięciem UI).

## Dowód z bazy (po krokach 1-4)

```
schedule_versions (site_id='real-object', month='2027-02-01'):
  SV-c9eed7d5c9b646a0a51c72528d3a88c0 | WORKING | excluded_from_history=1
  SV-1cde85759bf84a7aa15be652ff8e670d | WORKING | excluded_from_history=0
current_schedule_versions: 2027-02-01 -> SV-1cde85759bf84a7aa15be652ff8e670d
```

Stara wersja fizycznie nadal istnieje (trigger `schedule_versions_no_delete`
nie pozwala jej naprawdę skasować), ale jest oznaczona jako wykluczona z
historii -- niewidoczna w Historii wersji, restore ani eksporcie, zgodnie z
kontraktem.

## Dowód bezpośredniego API (krok 5)

```
POST /api/workspace/sites/real-object/schedule/2026-09-01/delete-current
-> HTTP 409
{"detail":"SV-ed027d8b71454ff0a71afd42e6534689 is already live and cannot be deleted"}
```

## Wynik

- zaakceptuj grafik z pierwszą służbą o znanej godzinie: **PASS** (luty,
  krok 1)
- chwilę przed startem pierwszej służby: także FINAL można usunąć: **nie
  ćwiczone osobno tej rundy dla wariantu FINAL** (krok 1-4 użyły WORKING;
  FINAL-nieżywy-usuwalny zweryfikowany wcześniej kodowo/testami
  jednostkowymi w ramach T57-06 -- `_require_working_or_absent`/
  `delete_current_version` nie rozróżniają WORKING/FINAL po stronie
  backendu, tylko żywy/nieżywy)
- po usunięciu WORKING brak grafiku w current, biznesowej Historii,
  restore i eksporcie: **PASS** (potwierdzone w bazie i przez Pawła)
- uruchom PLAN od nowa i zaakceptuj nowy wariant: **PASS**
- dokładnie w chwili startu pierwszej służby i później operacja usunięcia
  jest odrzucona przez backend, również przy bezpośrednim endpointzie:
  **PASS**, potwierdzone bezpośrednim wywołaniem API na żywym wrześniu --
  HTTP 409, `CannotDeleteLiveScheduleVersion`

**E3: PASS** (jeden podpunkt o wariancie FINAL-nieżywy nie przeklikany
osobno tej rundy -- oparty o wcześniejszą weryfikację kodową, opisane
wprost, nie ukryte).
