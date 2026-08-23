# Brief dla architekta — czy "Ogólna dostępność" ma być jednym blokiem na pracownika

## Kontekst

Ekran per-pracownik (T021 §5.1) ma checkbox "Ogólna dostępność" —
odznaczenie = zakres dat, w którym solver nie może użyć pracownika
(`AvailabilityKind.UNAVAILABLE_24H`). Zamrożona zasada właściciela
(`arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md` §5): stan
bazowy (zaznaczone) wraca sam po dacie "do", bez dodatkowej akcji.

Codex (audyt T021 round 9, R9-2) odrzucił moją próbę zaimplementowania
tego jako logikę "sprawdź czy istnieje aktualny blok, koryguj go albo
stwórz nowy" bezpośrednio w warstwie API — słusznie: to jest realna
logika biznesowa (wybór rodziny, wymuszanie unikalności), nie zwykłe
opakowanie istniejącej funkcji, a T021 nie może jej wymyślać w `api/`
ani w `rota/`. Ten dokument jest wyłącznie faktograficzny.

## Fakty zweryfikowane w kodzie

- `durable_inputs.append_availability(conn, *, coordinator_id, site_id,
  availability_id, employee_id, kind, start_date, end_date, active,
  note=None, responds_to_decision_required_id=None)` — zapisuje JEDNĄ
  wskazaną rodzinę (`availability_id`). Nie wybiera rodziny, nie
  wymusza unikalności między rodzinami.
- `availability_repository.get_current_availability_for_employee(conn,
  employee_id) -> list[AvailabilityRecord]` — jeden wiersz PER rodzina
  (`availability_id`), niezależnie od `active`. Nic nie ogranicza liczby
  rodzin `UNAVAILABLE_24H` per pracownik — teoretycznie może ich być
  wiele naraz.
- `AvailabilityRecord.active` znaczy "aktualny koniec łańcucha tej
  rodziny, nie zastąpiony" — NIE "dziś mieści się w zakresie dat".
  Rekord z `end_date` w przeszłości pozostaje `active=True` na zawsze,
  dopóki ktoś jawnie nie ustawi `active=False`.
- `availability_repository.list_active_overlapping(conn, employee_id,
  range_start, range_end) -> list[AvailabilityRecord]` — istniejący
  odczyt: aktualne końce łańcuchów, `active=True`, których zakres dat
  nachodzi na podany przedział. Może zwrócić WIĘCEJ NIŻ JEDEN wiersz.
  To już filtruje po dacie, ale nie rozstrzyga, która rodzina jest "tą"
  dla checkboxa, ani nie daje żadnej gwarancji atomowości zapisu.
- Brak jakiegokolwiek pola "pochodzenia" (provenance) odróżniającego
  rodzinę utworzoną przez macierz od innych `UNAVAILABLE_24H` (np.
  utworzonych przez "Zgłoś nieobecność" albo migrację danych).

## Problem, który znalazł Codex

Moja wcześniejsza propozycja (API najpierw odczytuje, czy istnieje
aktualny/przyszły blok, i albo go koryguje, albo tworzy nowy) ma dwie
wady:
1. To jest decyzja projektowa (czy w ogóle ma istnieć reguła "jeden
   blok na raz"), nie techniczne mapowanie — T021 nie ma mandatu jej
   podejmować.
2. Nawet gdyby była dozwolona, odczyt-potem-zapis w dwóch krokach nie
   jest atomowy (dwa równoległe żądania mogą oba nie zobaczyć istniejącej
   rodziny i stworzyć dwie różne) — a "sprawdź i napraw" w FastAPI to
   dokładnie ten rodzaj logiki biznesowej, którą architektura T021
   zastrzega dla `rota/application`.

## Pytania do rozstrzygnięcia przez architekta

1. Czy "Ogólna dostępność" ma być rzeczywiście ograniczona do jednego
   aktualnego/przyszłego bloku na pracownika (zgodnie z tym, jak
   wygląda w makiecie — jeden checkbox, jeden zakres), czy backend ma
   pozwalać na wiele niezależnych, równoległych bloków
   `UNAVAILABLE_24H`, a UI tylko pokazuje "czy JAKIŚ blok obejmuje
   dziś"?
2. Jeśli ma być jeden blok: potrzebna jest prawdziwa, atomowa funkcja w
   `rota/application` (nazwa przykładowa: `set_general_unavailability`)
   — sama odnajdująca/tworząca/korygująca właściwą rodzinę pod jedną
   transakcją, tak jak `set_calendar_day`/`set_target_hours` już to
   robią dla swoich odpowiedników.
3. Jak ma się zachować "przywrócenie wcześniej" (`active=False`) wobec
   rekordu, którego `end_date` już minął, a nikt go nie dezaktywował —
   czy to w ogóle powinno być możliwe, czy backend ma automatycznie
   "wygaszać" przeterminowane bloki gdzieś (i gdzie)?

## Zakres

Wyłącznie `rota/application/` (nazwa modułu wg uznania architekta) +
testy. Nie dotyczy frontu ani API T021 — osobne zadanie, własny audyt,
zanim ekran per-pracownika może zbudować checkbox "Ogólna dostępność".
Reszta ekranu (lista pracowników, dodawanie osoby, 24h, "Zgłoś
nieobecność" dla pozostałych 4 rodzajów, godziny docelowe, day_only) nie
jest tym zablokowana.
