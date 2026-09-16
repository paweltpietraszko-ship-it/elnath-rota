# ELNATH_ROTA_TEMPLATE.xlsx — zamrożony kontrakt danych

Ten dokument jest literalną kopią kontraktu z `tasks/ROTA-EXCEL-VBA-ENGINE-ADAPTER/brief.md`
sekcja 3. Nazwy zakresów/tabel poniżej są zamrożone — dodatek VBA
(`src/elnath_rota_addin.bas`) czyta i pisze wyłącznie po tych nazwach.
Wygląd, kolory i grupowanie wierszy są prezentacją i mogą być dowolnie
dostosowane; nazwy zakresów/tabel i ich kolumny — nie.

## Stabilne nazwy zakresów / tabel

- `ROTA_SITE_ID` — jedna komórka, tylko odczyt dla użytkownika (arkusz `Panel`).
- `ROTA_MONTH` — jedna komórka w formacie `YYYY-MM-01` (arkusz `Panel`).
- `ROTA_SELECTED_CANDIDATE_ID` — jedna komórka, wybrany `candidate_id` (arkusz `Panel`).
- Tabela `ROTA_EMPLOYEES` (arkusz `Pracownicy`).
- Tabela `ROTA_AVAILABILITY` (arkusz `Dostepnosc`).
- Tabela `ROTA_CANDIDATES` (arkusz `Kandydaci`).
- Tabela `ROTA_SCHEDULE_OUTPUT` (arkusz `Grafik`).

## `ROTA_EMPLOYEES`

Jeden wiersz na aktywnego LOCAL pracownika istniejącego już w rosterze Roty.

| Kolumna | Znaczenie |
|---|---|
| `employee_id` | stabilne ID, nieedytowalne przez zwykłego użytkownika |
| `pseudonym` | lokalna czytelna nazwa; request do Rota wysyła tylko `employee_id` |
| `target_hours` | liczba całkowita >= 0; jedyne edytowalne pole tego wiersza |

`employee_id` musi odpowiadać istniejącemu pracownikowi aktywnego rosteru
Site. Dodatek nie tworzy pracownika i nie zmienia rosteru.

## `ROTA_AVAILABILITY`

Jeden wiersz = jeden trwały rekord availability dla istniejącego `employee_id`.

| Kolumna | Znaczenie |
|---|---|
| `availability_id` | stabilne ID; dla nowego wiersza generowane raz i zachowywane przy retry |
| `employee_id` | |
| `kind` | istniejąca wartość `AvailabilityKind` (np. `LEAVE_GRANTED`, `SICK_LEAVE`, `DELEGACJA`) |
| `start_date` | ISO `YYYY-MM-DD` |
| `end_date` | ISO `YYYY-MM-DD` |
| `start_time` | opcjonalne `HH:00` |
| `end_time` | opcjonalne `HH:00` |
| `delegation_hours` | opcjonalna liczba całkowita |
| `active` | TRUE/FALSE |

Walidacja semantyki kombinacji pól pozostaje w istniejącym ownerze
persistence/application; dodatek nie implementuje własnych reguł availability.

## `ROTA_CANDIDATES`

Tabela techniczno-prezentacyjna po każdym PLAN/REPLAN. Jeden kandydat
zajmuje po jednym wierszu na pracownika.

| Kolumna | Znaczenie |
|---|---|
| `candidate_id` | identyczny dla wszystkich wierszy tego kandydata, tylko odczyt |
| `candidate_no` | kolejny numer prezentacyjny 1..N, tylko odczyt |
| `employee_id` | stabilne ID, tylko odczyt |
| `pseudonym` | czytelna lokalna nazwa pracownika |
| `day_01` … `day_31` | wartość projekcji danego dnia (`D`, `N`, `DEL`, inny kod pracy albo puste); dni nieistniejące w miesiącu pozostają puste |
| `total_hours` | suma godzin z projekcji dla pracownika w tym kandydacie |

Wybór użytkownika trafia do `ROTA_SELECTED_CANDIDATE_ID` (komórka na
arkuszu `Panel`) — wklej tam wartość `candidate_id` wybranego kandydata,
a następnie uruchom „Użyj tego grafiku”.

## `ROTA_SCHEDULE_OUTPUT`

Jeden zaakceptowany/bieżący grafik. Jeden wiersz = jeden pracownik.

| Kolumna | Znaczenie |
|---|---|
| `employee_id` | |
| `pseudonym` | |
| `day_01` … `day_31` | ta sama semantyka co w `ROTA_CANDIDATES` |
| `total_hours` | |

Dane pochodzą wyłącznie z odpowiedzi serwera. Dodatek buduje kompletny
nowy zestaw wierszy w pamięci i dopiero po pełnym sukcesie zastępuje
zawartość tabeli — nigdy częściowej aktualizacji.
