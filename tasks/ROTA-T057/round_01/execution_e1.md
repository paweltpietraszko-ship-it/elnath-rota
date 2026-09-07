# E1 — pierwszy PLAN od zera

Data wykonania: 2026-09-07. Obiekt: `real-object` (Real Object Benchmark).
Miesiąc: grudzień 2026 (świeży, nigdy wcześniej nietknięty -- kalendarz
dogenerowany skryptem, bo okno "Kalendarz" w aplikacji potrafi wygenerować
tylko bieżący realny miesiąc kalendarzowy, nie dowolny). Wykonane przez
realne UI + API + persistence (Pawel klika w przeglądarce na serwerze
testowym backend :8124 / frontend :5175, CC odczytuje bazę
`rota_dev.db` bezpośrednio po każdym kroku).

## Przebieg

1. Wybrano grudzień 2026 jako miesiąc roboczy. Ekran pokazał "Brak grafiku
   na ten miesiąc" -- brak przycisku "Historia wersji" w ogóle (przycisk
   ten renderuje się tylko, gdy istnieje `current_version` -- jego
   nieobecność jest silniejszym dowodem "0 ScheduleVersion" niż pusta
   lista, bo cała gałąź UI zależna od wersji jeszcze nie istnieje).
2. Kliknięto "Zaplanuj (PLAN)" -> pojawił się kandydat (preview,
   `FEASIBLE`).
3. Kliknięto "Odrzuć wynik".
4. Kliknięto "Zaplanuj (PLAN)" ponownie -> 1 kandydat.
5. Kliknięto "Użyj tego grafiku".
6. Pojawił się przycisk "Historia wersji" -> dokładnie 1 wersja, status
   "Wersja robocza" (WORKING), oznaczona jako bieżąca.

## Dowód z bazy (po kroku 6)

```
schedule_versions (site_id='real-object', month='2026-12-01'):
  SV-81d1bd2b0ef34124b9121d0ff01fa545 | WORKING | parent=None | created_at=2026-09-07T14:02:14
current_schedule_versions:
  2026-12-01 -> SV-81d1bd2b0ef34124b9121d0ff01fa545
```

Dokładnie 1 wiersz w `schedule_versions`, wskaźnik `current` zgodny z nim.

## Wynik

- brak zaakceptowanego grafiku -> PLAN daje FEASIBLE preview: **PASS**
- przed "Użyj tego grafiku": 0 ScheduleVersion: **PASS** (brak w ogóle
  gałęzi UI zależnej od wersji + potwierdzone, że dopiero po akceptacji
  pojawił się jeden wiersz w bazie)
- odrzuć preview -> nadal 0: **PASS** (kolejny PLAN po odrzuceniu zadziałał
  identycznie jak pierwszy, bez żadnego śladu wcześniejszej próby)
- nieudany PLAN -> nadal 0: **nie wymuszono ręcznie w tej rundzie** (wymagałoby
  celowego rozbicia obiektu testowego, np. wyzerowania pracowników, co
  ryzykowałoby zepsucie danych używanych też w E2-E5). Zweryfikowane
  wyłącznie przez inspekcję kodu: `plan_month`'s "no current version" branch
  (`rota/application/plan_ops.py`) nigdy nie wywołuje
  `lifecycle.create_schedule_version` poza ścieżką `select_candidate` --
  strukturalnie nie ma jak nieudany PLAN miał zapisać cokolwiek.
- PLAN ponownie -> zaakceptuj -> dokładnie 1 zaakceptowana wersja i ona jest
  current: **PASS**, potwierdzone bezpośrednio w bazie (powyżej).

**E1: PASS** (z jednym punktem zweryfikowanym przez kod, nie przez żywy klik --
opisane wyżej, nie ukryte).
