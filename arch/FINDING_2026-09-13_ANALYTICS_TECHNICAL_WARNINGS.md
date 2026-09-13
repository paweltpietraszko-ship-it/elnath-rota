# ROTA-ANALYTICS-TECHNICAL-WARNINGS — surowe ID i angielskie symbole w Analityce

STATUS: CONFIRMED — READY FOR CC, NO ARCHITECT DECISION NEEDED

## Problem

Na `main@3e4cad2` ekran **Analityka i bilanse** pokazuje koordynatorowi m.in.:

```text
Piotr: analytics unavailable for employee '<UUID>', month 2026-10-01: missing target_hours
```

To jest rzeczywisty render, nie samo techniczne użycie ID jako React key lub
parametru. Narusza późniejszy zamrożony kontrakt T060:

- brief T060 §2.1: surowy `employee_id` ani podobny identyfikator nie może być
  treścią UI/warningu;
- brief T060 §2.9: UI ma używać nazwy pracownika, bez fallbacku na ID;
- brief T060 §2.14 / T60-16: Analytics pozostawał poza ówczesnym scope tylko
  **dopóki nie było dowodu rzeczywistego renderu technicznego ID**.

Dowód właśnie istnieje. Nie jest potrzebna nowa decyzja OWNERA ani projekt
architekta.

## Przyczyna

`rota/application/analytics_read.py` tworzy cztery warianty surowych warningów
z `employee_id`, angielskimi frazami, ISO-datą oraz nazwami technicznymi takimi
jak `target_hours`. `api/routers/analytics.py` przekazuje je bez zmiany, a
`frontend/src/screens/Analytics.tsx` dokłada czytelny `display_name` i renderuje
tekst warningu 1:1.

Poprzedni Task `ROTA-UI-TARGET-HOURS-IDENTIFIER@31dd43b` poprawił wyłącznie
ostrzeżenie planowania z `rota/application/assembler.py`. Nie obejmował
`analytics_read.py`. T060 również jawnie odłożył Analytics do czasu realnej
reprodukcji. Dlatego trzy wcześniejsze podejścia nie mogły zamknąć tej ścieżki.

## Wąski zakres poprawki CC

1. `rota/application/analytics_read.py` — wszystkie cztery publiczne warianty
   warningu Analityki mają być użytecznym polskim tekstem bez `employee_id`,
   `target_hours`, nazw klas/pól i surowego tekstu wyjątku.
2. `frontend/src/screens/Analytics.tsx` nadal wskazuje osobę przez istniejące
   `row.display_name`; nie wolno rekonstruować lub filtrować UUID regexem.
3. Miesiąc ma być przedstawiony człowiekowi jako miesiąc/rok, a nie techniczny
   pierwszy dzień miesiąca, jeżeli pozostaje częścią komunikatu.
4. Zachować statusy `UNAVAILABLE` / `MONTH_AVAILABLE_QUARTER_UNAVAILABLE`,
   obliczenia, dane i zachowanie przy brakującym celu godzinowym bez zmian.
5. Zaktualizować stare asercje T019, które utrwalają dokładny surowy tekst;
   nie traktować ich jako sprzeczności produktowej, bo późniejszy T060 oraz
   obecna decyzja OWNERA supersedują wyłącznie warstwę prezentacji.

## Wymagane wąskie sprawdzenie

- brak celu dla wybranego miesiąca;
- brak celu dla innego miesiąca kwartału;
- niedostępna analityka miesiąca z kanonicznym błędem danych;
- niedostępna analityka kwartału z kanonicznym błędem danych;
- pion API → rzeczywisty ekran potwierdzający: nazwa pracownika jest widoczna,
  a UUID, `target_hours`, angielskie frazy i surowy wyjątek nie są widoczne.

Bez zmian solvera, persistence, DTO, sposobu liczenia bilansów i bez pełnej
regresji. Symulatory i benchmarki pozostają wyłączone.

## Reprodukcja na exact SHA

Na `main@3e4cad2` istniejące testy:

```text
tests/test_t019.py::test_8_requested_month_missing_target
tests/test_t019.py::test_9_other_quarter_month_missing_target
```

przechodzą 2/2 i wprost potwierdzają, że backend nadal emituje surowe teksty.
`Analytics.tsx:99,183-190` potwierdza ich bezpośredni render obok
`display_name`.

