# ROTA-OCHRONA-EDIT-7D-LIMIT — minimalny brief implementacyjny

## Cel / decyzja OWNERA (2026-09-21)
Koordynator może po uruchomieniu konkretnego obiektu OCHRONA zmienić istniejący próg obciążenia w ruchomych 7 dniach. Dotyczy tylko okienka ustawień i zapisu istniejącego parametru; nie zmienia pozostałych zasad planowania. W ORDINARY edycja zabroniona. Po wpisaniu wartości **powyżej 72 godzin** pokaż ostrzeżenie i wymagaj świadomego potwierdzenia przed zapisem; do 72 h włącznie bez tego dodatkowego komunikatu. Domyślna istniejąca wartość 40 h pozostaje bez zmian.

## Zachowanie koordynatora
W istniejącym panelu ustawień konkretnego obiektu OCHRONA: przycisk „Zmień limit godzin” otwiera małe okno z aktualnym progiem i polem „Nowy limit godzin w ruchomych 7 dniach” (dodatnia liczba całkowita). „Anuluj” nie zapisuje. „Zapisz” aktualizuje istniejące `SiteProfile.rolling_7d_decision_threshold_hours` dla bieżącego obiektu, przez istniejący autoryzowany zapis profilu i jego rejestr zmian w pamięci programu. Nie przeliczaj automatycznie istniejących grafików; zmiana działa przy kolejnych obliczeniach i walidacji według obecnej logiki.

Przy wartości >72 h pokaż komunikat: „Uwaga: bardzo wysoki limit godzin. Ustawiasz próg obciążenia przekraczający 72 godziny w ruchomych 7 dniach. Taka wartość może dopuścić grafik naruszający przepisy o czasie pracy i odpoczynku. Koordynator musi sprawdzić zgodność grafiku z obowiązującymi zasadami.” Dodaj niezaznaczone domyślnie pole „Rozumiem ostrzeżenie i potwierdzam zmianę”. Bez potwierdzenia nie zapisuj, również przy bezpośrednim wywołaniu API; potwierdzenie dotyczy tego konkretnego zapisu i musi być zapisane w istniejącej pamięci decyzji razem z poprzednią/nową wartością. Do 72 h włącznie nie wymagaj pola potwierdzenia. Nie nazywaj 72 h ustawowym limitem ani nie obiecuj zgodności dowolnego grafiku z prawem.

Dla ORDINARY: brak kontrolki; serwer odrzuca zmianę progu niezależnie od interfejsu. Nie zmieniaj istniejącego progu ORDINARY ani jego zasad stosowania.

## Istniejący owner / minimalny szew
Parametr już istnieje w `rota/domain` / `rota/persistence/site_profile_repository.py`; solver i walidator już go czytają. Istniejący autoryzowany zapis: `rota/application/durable_inputs.py::update_site_profile`. Istniejący panel obiektu: `frontend/src/screens/ControlPanel.tsx` (zweryfikuj miejsce osadzenia; nie twórz nowego ekranu). API ustawień obiektu: `api/routers/site_profile.py`. Nie dodawaj nowego pola DB ani nowego silnika reguł. Sprawdź, czy profile_id nie jest współdzielony pomiędzy różnymi obiektami; zapis nie może niejawnie zmienić limitu innego obiektu.

## TASK_SCOPE
Wyłącznie minimalna kontrolka/modal w istniejącym panelu, odczyt i zapis wartości przez istniejącą ścieżkę profilu z walidacją zakresu/reżimu/potwierdzenia po stronie serwera, oraz istniejący audit trail decyzji. Jeżeli do zachowania atomowego rejestru potwierdzenia potrzebny jest jeden mały szew w `rota/application/durable_inputs.py`, użyj go bez tworzenia równoległego zapisu; nie używaj niesprawdzonego obejścia przez zwykły PUT całego katalogu zmian. Jeśli zidentyfikujesz konflikt z istniejącym kontraktem API, przekaż najwęższą proponowaną korektę przed implementacją zamiast rozbudowy.

## OUT_OF_SCOPE
Zero zmian solvera, wag, reguł odpoczynku, innych HARD, zasad ORDINARY, historycznych grafików, sposobu liczenia siedmiodniowego okna i mechanizmu sobót. Nie twórz nowych uprawnień ani osobnego systemu wyjątków. Nie podwyższaj automatycznie progu obecnych obiektów.

## Testy akceptacyjne
1. OCHRONA: odczyt istniejącego 40 h, zapis 48/60/72 h, ponowny odczyt i użycie istniejącego pola; anulowanie bez zapisu.
2. OCHRONA: 73 h oraz 100 h bez potwierdzenia -> odmowa także przez API; z potwierdzeniem -> zapis i odnotowanie decyzji.
3. ORDINARY: brak edycji w UI i odmowa zmiany z API; istniejąca wartość pozostaje taka sama.
4. Zmiana dotyczy tylko wskazanego obiektu; nie zmienia katalogu zmian i nie przelicza aktualnego grafiku.
5. Dotychczasowe kontrole odpoczynków i pozostałe reguły nie są modyfikowane.

Codex aktualnie niedostępny: CC wykonuje najpierw krótki precheck sensu i zakresu tego briefu, zgłasza jedynie rzeczywiste luki, a następnie — na polecenie OWNERA — może implementować jako tryb wyjątkowy. CC self-test i moja kontrola statyczna nie są niezależnym audytem; merge wyłącznie po decyzji OWNERA.
