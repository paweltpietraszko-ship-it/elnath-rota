# ROTA-T030 — Panel sterowania → Obiekt: katalog zmian

Status: **READY FOR IMPLEMENTATION**

Base implementation SHA: `f2ba515d701ee41f325a58a7711169a640d49ade`
(`task/ROTA-T029`). T030 musi zachować całe zachowanie T029.

Owner decisions: Paweł, 2026-08-24. Konsolidacja zamyka audyt
`round_01/tests/tests_r1.txt`.

## 1. Wynik dla właściciela

Zakładka „Obiekt” w Panelu sterowania przestaje być wyszarzonym placeholderem.
Koordynator może w niej utworzyć i później poprawić katalog zmian danego
obiektu: D/N, godziny, liczbę potrzebnych osób i dni tygodnia.

Po zapisaniu pierwszej poprawnej zmiany Workspace nie zgłasza już braku
standardowej zmiany. Zrealizowane grafiki nie są przepisywane.

## 2. Istniejący backend jest właścicielem

T030 używa bez zmian:

- `get_site_profile` — aktualny profil i `standard_shifts`;
- `update_site_profile` — atomowy zapis pełnego profilu, audyt i invalidacja;
- `validate_standard_shift` — pełna walidacja wiersza;
- `shift_duration_hours` i `normalized_catalog_kind` — czas trwania oraz
  klasyfikacja 12h/24h/INNY;
- `coordinator_context_completeness` — informacja o brakującym katalogu.

Nie wolno zmieniać `rota/**`, tworzyć drugiego repozytorium, walidatora,
wersjonowania profilu ani identyfikatora wiersza zmiany.

## 3. Zamknięte decyzje formularza

1. Wiersz można dodać, edytować i usunąć. Usunięcie wymaga potwierdzenia.
   Ostatniego wiersza nie można usunąć; błędny ostatni wiersz należy edytować.
2. `active_weekdays` jest widoczne i edytowalne jako Pon–Nd. Co najmniej jeden
   dzień musi pozostać zaznaczony.
3. `required_rest_hours` nie jest polem UI. Każdy wiersz zapisany przez T030
   otrzymuje `11`.
4. Godziny wybiera się z pełnych godzin `00:00`–`23:00`; minuty nie istnieją
   w formularzu.
5. `end_next_day` jest wyliczane: `end_time <= start_time` oznacza następny
   dzień. Równe godziny oznaczają 24h, nie zmianę zerową.
6. `catalog_kind` nie jest przełącznikiem. UI pokazuje wyliczone
   `12h`, `24h` albo `INNY` oraz liczbę godzin.
7. `required_primary_count` jest dodatnią liczbą całkowitą widoczną jako
   „Potrzebnych osób”.

Reguły ochrony po 24h i odpoczynek tygodniowy pozostają automatycznymi HARD z
T023b. T030 nie daje koordynatorowi przełącznika do ich wyłączenia.

## 4. Jeden kontrakt API

### Odczyt

`GET /workspace/sites/{site_id}/shift-catalog`

Zwraca `site_id`, `profile_id` oraz uporządkowaną listę:

```json
{
  "kind": "D",
  "start_time": "06:00",
  "end_time": "18:00",
  "required_primary_count": 1,
  "active_weekdays": [1, 2, 3, 4, 5, 6, 7],
  "duration_hours": 12,
  "catalog_kind": "12h"
}
```

Pusty katalog jest poprawną odpowiedzią GET dla nowego, jeszcze niepełnego
obiektu.

### Zapis

`PUT /workspace/sites/{site_id}/shift-catalog`

Request zawiera tylko `shifts`. Każdy wiersz przyjmuje pięć pól wejściowych:
`kind`, `start_time`, `end_time`, `required_primary_count`, `active_weekdays`.
Nie przyjmuje `profile_id`, pól polityki profilu, `required_rest_hours`,
`end_next_day` ani `catalog_kind`.

Lista musi zawierać co najmniej jeden wiersz. Kolejność requestu jest trwałą
kolejnością katalogu.

Router dla każdego wiersza:

1. parsuje wyłącznie pełne godziny;
2. wylicza `end_next_day`;
3. ustawia `required_rest_hours=11` i `catalog_kind=None`;
4. buduje `StandardShift` i wywołuje istniejące `validate_standard_shift`.

Dopiero gdy wszystkie wiersze są poprawne, router pobiera najnowszy
`SiteProfile`, podmienia wyłącznie `standard_shifts` i raz wywołuje
`update_site_profile`. Request nie może nadpisać żadnego ukrytego pola, także
gdy zmieniło się ono po wcześniejszym GET w przeglądarce.

Odpowiedź `200` ma ten sam kształt co GET i pochodzi ze świeżego odczytu po
zapisie. Nie ma osobnych endpointów POST/PATCH/DELETE dla pojedynczego wiersza.

## 5. Granice zachowania

- Dozwolone są mnogie wiersze, INNY i nakładające się wystąpienia, bo obecna
  domena je dopuszcza. T030 nie dodaje nowego zakazu duplikatów/overlapów.
- PUT pustej listy jest odrzucany również przez API, nie tylko przez disabled
  button w UI.
- Błąd któregokolwiek wiersza oznacza brak zapisu całej listy.
- Materialna zmiana korzysta z istniejącego `SITE_PROFILE_CHANGED`, audytu i
  invalidacji. Identyczny zapis nie tworzy sztucznej akcji.
- Istniejące ScheduleVersion, ShiftDemand oraz REALIZED/CANCELLED Assignment
  nie są modyfikowane. Nowy katalog jest bieżącą konfiguracją dla następnego
  generowania/replanowania zgodnie z istniejącym pipeline.
- `planning_regime` pozostaje tylko do odczytu poza tym ekranem. T030 nie
  dodaje drogi jego zmiany.
- Pola `training_s_*`, `external_support_enabled` i `day_only_blocks_n` nie są
  zwracane do formularza ani przyjmowane w request.

## 6. UI zakładki „Obiekt”

- Dwie aktywne zakładki: „Obiekt” i istniejąca „Obsada (n)”. Przełączenie nie
  zmienia ekranu ani nie gubi stanu zapisanej Obsady.
- „Obiekt” pokazuje listę wierszy, przycisk „+ Dodaj zmianę” i jeden przycisk
  „Zapisz katalog”. Edycje są lokalnym draftem do jednego atomowego PUT.
- Nowy pusty profil od razu pokazuje formularz pierwszego wiersza; anulowanie
  pozostawia pusty stan bez requestu.
- Wiersz zawiera: D/N, Początek, Koniec, Potrzebnych osób, Pon–Nd oraz
  wyliczony opis czasu/katalogu.
- „Usuń” wymaga potwierdzenia. Przy jednym wierszu jest disabled z informacją
  „Ostatnią zmianę popraw przez edycję”.
- Podczas zapisu przycisk jest disabled. Sukces zastępuje draft odpowiedzią
  serwera. Błąd pokazuje komunikat, zachowuje cały draft i nie pokazuje
  fałszywego sukcesu.
- Wszystkie akcje korzystają z istniejącego `data-diag-action` i klienta
  `req()`; bez drugiej diagnostyki i bez bezpośredniego `fetch` w komponencie.

UI nie eksponuje: minut, `end_next_day`, `catalog_kind`, odpoczynku, toggle'i
profilu ani zmiany rodzaju Site.

## 7. Dozwolony zakres plików

Produkt:

- `api/main.py`, `api/errors.py`;
- nowy `api/routers/site_profile.py`;
- `frontend/src/api/client.ts`, `frontend/src/screens/ControlPanel.tsx`,
  `frontend/src/App.css`;
- opcjonalnie jeden nowy komponent
  `frontend/src/screens/SiteShiftCatalog.tsx`.

Testy/delivery:

- nowy `tests/test_t030_shift_catalog_api.py`;
- nowy `frontend/e2e/shift-catalog.spec.ts` i tylko konieczna adaptacja
  istniejącego seeda E2E;
- `tasks/ROTA-T030/round_01/implementation/**`.

Brak nowych zależności. Nie modyfikować istniejących testów ani plików poza
listą; w plikach współdzielonych zachować całe zachowanie T029 poza koniecznym
osadzeniem zakładki. Jeżeli implementacja wymaga szerszego zakresu, zgłosić
blocker zamiast tworzyć connector lub nową warstwę.

## 8. Minimalna macierz odbioru

T30-01 — branch zawiera exact base T029 i jego zachowanie nadal przechodzi.

T30-02 — GET zwraca pusty oraz istniejący katalog w trwałej kolejności.

T30-03 — parametry: D/N 12h dzienna/nocna, 24h (równe godziny) i INNY mają
poprawne `end_next_day`, duration i wyliczony catalog kind po reconnect.

T30-04 — odrzucane są: minuty, count <=0, puste/powtórzone dni, dzień poza
1–7 i pusty PUT; stan sprzed requestu pozostaje bez zmian.

T30-05 — zapis wielu wierszy jest atomowy; błąd ostatniego nie zapisuje
wcześniejszych.

T30-06 — symulowana zmiana ukrytych pól po GET nie zostaje cofnięta przez PUT
katalogu; request z dodatkowym ukrytym polem jest odrzucany.

T30-07 — materialny PUT tworzy istniejący audyt/invalidację, identyczny PUT
nie tworzy fałszywej akcji; żaden utrwalony historyczny grafik nie zmienia się.

T30-08 — po pierwszym poprawnym PUT completeness nie zawiera komunikatu o
braku standardowej zmiany (inne braki mogą pozostać).

T30-09 — E2E: wejście w „Obiekt”, pusty stan, dodanie, zapis, reload i ten sam
katalog.

T30-10 — E2E: edycja godzin/liczby/dni oraz usunięcie jednego z dwóch wierszy;
ostatni wiersz jest chroniony w UI i API.

T30-11 — E2E: błąd zapisu zachowuje draft, pokazuje błąd i jest widoczny w
istniejącym raporcie diagnostycznym.

T30-12 — build frontendu, pełna regresja Pythona, diff-scope z §7 i zero
zmian w `rota/**`.

## 9. DELIVERY

Wykonawca przekazuje exact HEAD, diff od base SHA, raw `backend.py` stdout,
wynik `npm run build`, wynik E2E T030 oraz listę zmienionych plików.

Jeżeli istniejący backend nie pozwala spełnić kontraktu bez zmiany `rota/**`,
wykonawca zatrzymuje się i wskazuje dokładną lukę. Nie naprawia solvera,
assemblera ani domeny w T030.
