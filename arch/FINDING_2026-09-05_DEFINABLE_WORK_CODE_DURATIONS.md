# FINDING 2026-09-05 — koniec kwartału potrzebuje dowolnie definiowalnych
długości zmian na wydruku; SOLVER MA ZOSTAĆ NIETKNIĘTY

STATUS: finding + zweryfikowany zakres, NIE jest dokumentem projektowym,
NIE jest zamrożony. Materiał wejściowy dla architekta (ta sama rola co
inne `arch/FINDING_*`) — CC nie pisze tutaj briefu implementacyjnego, to
zadanie architekta po przekazaniu przez Pawła.

**UWAGA DLA KAŻDEGO MODELU CZYTAJĄCEGO TEN DOKUMENT (Codex, architekt):**
to zgłoszenie dotyczy WYŁĄCZNIE dwóch warstw: (1) mapowania kodów na
wydruku (`rota/application/schedule_export.py` +
`rota/persistence/site_repository.py`) i (2) ręcznej korekty grafiku
(`rota/application/manual_edit.py`). **NIE dotyka i NIE MA dotykać
solvera CP-SAT (`rota/planning/solver.py`) ani katalogu zmian obiektu
(`SiteProfile.standard_shifts`/`ShiftCatalogKind`).** Jeśli po przeczytaniu
briefu wydaje się, że trzeba poprawić solver — to znaczy, że coś zostało
źle zrozumiane. PYTAJ, NIE ZGADUJ. Trzy poniższe podsystemy są od siebie
całkowicie niezależne i to rozróżnienie jest sednem tego findingu:

1. **Solver (`rota/planning/solver.py`)** — układa PLAN/REPLAN, celuje w
   `target_hours` każdego pracownika (TARGET-01, "ABSOLUTE PRIORITY").
   Korzysta z katalogu zmian obiektu (standardowe D/N 12h w ochronie).
   **Nietknięty przez ten finding, w żadnym zakresie.**
2. **WorkBalance / analityka / bilans kwartalny (`rota/balance.py`,
   `rota/application/analytics_read.py`)** — liczy realne przepracowane
   godziny wprost z zapisanych w bazie `Assignment.start_datetime`/
   `end_datetime`. **Nie patrzy na żaden kod z wydruku.** Dowolna
   długość realnego Assignmentu liczy się tu automatycznie, bez żadnej
   dodatkowej pracy.
3. **Wydruk (`rota/application/schedule_export.py`)** — zamienia realny
   Assignment na czytelny dla koordynatora kod (D1/N1/...) do druku.
   **Tu i tylko tu jest dziś sztywne ograniczenie, które trzeba zmienić.**

## Origin / requirement (Paweł, 2026-09-05)

Koniec kwartału: koordynator ręcznie ustala pracownikowi dokładną liczbę
godzin do wypracowania w tym miesiącu (`target_hours`, mechanizm już
istnieje i już działa — patrz [[project_quarter_closing_overtime_gap]] w
pamięci CC, potwierdzone empirycznie że solver trafia w cel w granicach
jednego bloku zmianowego). Żeby dobić do dokładnej liczby, czasem
potrzebna jest **pojedyncza zmiana o niestandardowej długości** — w tym
kwartale np. 14h, w kolejnym może być 15h, 17h, 18h, 19h — **nie da się
tego z góry wyliczyć na sztywno**, wartość zależy od bieżącego bilansu
pracownika i zmienia się kwartał do kwartału.

Paweł wprost: *"solvera nie ruszamy, on nadal poda grafik bliski celowi
godzin [...]. Koordynator zamienia ręcznie np D1 na D7 (17h) a wydruk nam
to zliczy do analityki"* — potwierdzone przez CC, z jednym uściśleniem
mechaniki (patrz "Jak to działa mechanicznie" niżej).

Materiał referencyjny (prawdziwe karty pracy klienta, `Grafiki/7442.jpg`,
`Grafiki/7732.jpg`) pokazuje, że u klienta length-kody D1-D5/N1-N5/U1-U5/
C1-C5 **już dziś mają różne wartości godzinowe w różnych miesiącach tego
samego arkusza** (np. D3=24h w jednym legendzie, D3=7h w innej, tego
samego obiektu) oraz że klient dokłada **zupełnie nowe kody** (D6=14h,
N6=10h) gdy standardowa piątka nie wystarcza.

## Verified findings (sprawdzone bezpośrednio w kodzie, nie zgadywane)

**1. `FROZEN_WORK_CODE_HOURS` jest dziś globalną, zamrożoną stałą — to
jest realna blokada, i to na poziomie wydruku, nie solvera.**
`rota/persistence/site_repository.py:51-54`:
```python
FROZEN_WORK_CODE_HOURS = {
    "D1": 12, "D2": 4, "D3": 24, "D4": 2, "D5": 24,
    "N1": 12, "N2": 16, "N3": 24, "N4": 24, "N5": 24,
}
```
Komentarz nad stałą: *"Never persisted as mutable configuration"*.
Koordynator może dziś zmieniać tylko godziny ZEGAROWE danego kodu
(`work_code_intervals`), ale `_validate_work_code_intervals`
(`site_repository.py:96-109`) odrzuca każdą konfigurację, w której
wyliczony z godzin czas trwania nie zgadza się dokładnie z wartością z
tej tabeli (`site_repository.py:103-104`).

**2. Realny Assignment o niestandardowej długości (np. 17h) DZIŚ ZEPSUJE
WYDRUK, niezależnie od tego, czy powstał ręcznie czy przez solver.**
`schedule_export.py::_map_work_code` (linie 306-320) wymaga dokładnego
dopasowania czasu trwania Assignmentu do jednej z 10 wartości z
`FROZEN_WORK_CODE_HOURS` — gdy żaden kod nie pasuje, rzuca
`ExportProblemError("WORK_CODE_MAPPING_REQUIRED", ...)`. To jest realny,
sprawdzony blocker, nie hipoteza.

**3. `rota/application/manual_edit.py` (ręczna korekta grafiku,
`apply_manual_correction`) NIE odwołuje się nigdzie do katalogu zmian
(`StandardShift`/`ShiftCatalogKind`) — sprawdzone grepem, zero trafień.
Przyjmuje dowolny realny `start_datetime`/`end_datetime`, walidowany tylko
przez ogólne reguły (`validate()` — odpoczynek, nakładanie się itd.), nie
przez przynależność do katalogu. Czyli koordynator już dziś MOŻE zapisać
Assignment o dowolnej długości przez ten mechanizm — solver i katalog
zmian nie stoją na przeszkodzie.

**4. WorkBalance/analityka liczy z realnego Assignmentu, nie z kodu
wydruku — sprawdzone: `rota/balance.py` i
`rota/application/analytics_read.py` czytają godziny bezpośrednio z bazy
(`Assignment.start_datetime`/`end_datetime` przez schedule_repository),
zero odwołań do `schedule_export.py` czy do `FROZEN_WORK_CODE_HOURS`. Więc
dowolna długość realnego Assignmentu **automatycznie** trafia poprawnie do
bilansu, bez żadnej dodatkowej zmiany w analityce.

**5. Reserve sloty po stronie urlopu/chorobowego (U3-U5, C3-C5) JUŻ DZIŚ
mają dowolną, definiowalną wartość godzinową** — `_validate_reserve_hours`
(`site_repository.py:112-117`) przyjmuje dowolną dodatnią liczbę całkowitą,
bez porównania do żadnej zamrożonej tabeli. To jest precedens dokładnie
takiego mechanizmu, jaki jest potrzebny — ale istnieje tylko dla
urlopu/chorobowego (`RESERVE_SLOT_KEYS`), NIE istnieje analogiczny
mechanizm po stronie realnych zmian roboczych (D/N).

## Czego NIE trzeba robić (żeby uniknąć nieuzasadnionego rozszerzania zakresu)

- Nie trzeba zmieniać `rota/planning/solver.py` — cel end-to-end (solver
  trafia blisko `target_hours`) już działa i ma zostać dokładnie taki,
  jaki jest.
- Nie trzeba zmieniać `SiteProfile.standard_shifts`/`ShiftCatalogKind` —
  katalog zmian, z którego solver buduje demand/rozkłady, zostaje
  nietknięty. Niestandardowa zmiana wchodzi do grafiku wyłącznie przez
  ręczną korektę, nigdy przez solver.
- Nie trzeba przebudowywać WorkBalance/analityki — już dziś liczy
  poprawnie z realnego Assignmentu, niezależnie od jego długości.

## Co prawdopodobnie trzeba zmienić (do potwierdzenia/doprecyzowania przez architekta, CC nie projektuje rozwiązania)

- Otwarty, niesztywny sposób definiowania dodatkowych kodów/okien
  czasowych po stronie realnych zmian roboczych (analogicznie do już
  istniejącego `RESERVE_SLOT_KEYS`/`reserve_hours` dla urlopu/
  chorobowego, ale nie ograniczony do stałej liczby 3 slotów na rodzinę —
  Paweł: kolejny kwartał może potrzebować zupełnie innej wartości niż
  ta z bieżącego kwartału, wartości nie da się z góry wyliczyć).
- `_map_work_code`/`_validate_work_code_intervals` muszą umieć rozpoznać
  taki definiowalny kod obok istniejących 10 zamrożonych, bez naruszania
  ich obecnej sztywności.

## OWNER decyzje (2026-09-05, po przeglądzie Codexa — patrz BOARD.md ROTA-WORK-CODE-DURATIONS-REVIEW)

Codex przed napisaniem briefu przejrzał ten finding i sprawdził go w
kodzie (CC niezależnie zweryfikował każdy punkt, wszystkie potwierdzone
prawdziwe — nie jest to "wymyślanie" przez zmęczoną instancję):

1. **Ekran "Ręczna korekta" (`frontend/src/screens/MonthlyPlanning.tsx:831-871`)
   nie ma dziś pola do zmiany godziny początku/końca zmiany** — tylko
   backend (`manual_edit.py::apply_manual_correction`) to umie. UI trzeba
   rozszerzyć.
2. **`_hours_of()` (`schedule_export.py:450-464`) cicho zwraca `0`
   godzin dla nieznanego kodu** (np. hipotetyczne "D6") — pada przez
   `_legal_uc_value()`, który zna tylko U/C, kończy na `or 0`. Bez
   naprawy suma na wydruku byłaby CICHO zaniżona, nie zgłosiłaby błędu.
3. Obecne ustawienia (`SitePrintSettings`) są kluczowane wyłącznie po
   `site_id` — nie ma wymiaru miesiąca. Legenda ma dziś sztywno 5 slotów
   na rodzinę (D/N/U/C).
4. Dowody: `Grafiki/7442.jpg` różni się dziś w working tree od wersji w
   commicie, `Grafiki/7732.jpg` nie jest w ogóle w gicie — żaden model
   czytający repo na konkretnym SHA by tego nie zobaczył. **Poprawione
   niżej: transkrypcja zamiast surowych zdjęć** (RODO — karty klienta
   mają realną nazwę firmy i czytelny podpis, nie nadają się do
   commitowania w repo bez zgody klienta).

**Rozstrzygnięcia OWNERA (Paweł) na 4 pytania Codexa:**

1. **Zakres definiowalności**: TYLKO dodatkowe kody (D6, N6, ...) są
   definiowalne. `D1-D5`/`N1-N5` zostają zamrożone dokładnie tak jak dziś
   (`FROZEN_WORK_CODE_HOURS` bez zmian dla tych 10 kluczy).
2. **Kod czy godziny**: koordynator wybiera z listy **zdefiniowany kod**
   (kod musi istnieć w ustawieniach obiektu, zanim zostanie użyty) —
   program NIE dobiera/tworzy kodu automatycznie z wpisanej liczby godzin.
3. **PLAN vs WYK**: definiowalny kod trafia do **obu kolumn** (PLAN i
   WYK), zgodnie z dokładnie tą samą semantyką co dziś standardowe kody
   D1-D5/N1-N5 — żadnego nowego, osobnego traktowania.
4. **D/N vs U/C**: definiowalne kody dotyczą **wyłącznie realnej pracy**
   (rodzina D/N). Urlop/chorobowe (U/C) zostają jak dziś — mają już
   własny, elastyczny mechanizm (`reserve_hours` dla U3-U5/C3-C5),
   niezmieniony przez ten finding.

Otwarte technicznie (do architekta, nie rozstrzygnięte przez OWNERA
wprost, ale zawężone powyższymi decyzjami): per-obiekt na stałe czy
per-miesiąc — transkrypcja niżej pokazuje, że u klienta wartości kodów
różnią się między miesiącami tego samego obiektu, więc per-miesiąc wydaje
się zgodne z realną praktyką, ale to architekt ustala dokładny kształt
kontraktu.

## Transkrypcja materiału referencyjnego (zamiast surowych zdjęć — RODO)

Dwie legendy kodów z realnych kart pracy klienta (ten sam obiekt,
ROYALPACK/APEXIM, dwa różne miesiące — 2026-07 i 2026-09). Tylko kody i
wartości godzinowe, bez żadnych danych osobowych ani identyfikujących
firmę poza tym, co już jawnie widnieje w repozytorium (nazwa
ROYALPACK/APEXIM pojawia się już w innych, wcześniej zaakceptowanych
materiałach tego repo).

**Legenda, miesiąc 2026-07:**
```
D1=12h  D2=24h  D3=24h  D4=24h  D5=2h
N1=12h  N2=16h  N3=12h  N4=24h  N5=12h
U1=12h  U2=16h  U3=0h   U4=24h  U5=20h
C1=12h  C2=16h  C3=0h   C4=24h  C5=20h
```

**Legenda, miesiąc 2026-09 (koniec kwartału — ten sam obiekt):**
```
D1=12h  D2=24h  D3=7h   D4=3h   D5=6h   D6=14h  <- nowy kod
N1=12h  N2=16h  N3=8h   N4=24h  N5=24h  N6=10h  <- nowy kod
U1=12h  U2=16h  U3=8h   U4=3h   U5=6h   U6=10h
C1=12h  C2=16h  C3=8h   C4=3h   C5=6h
```

Widać: D3/D4/D5 mają różne wartości w obu miesiącach (nie tylko D6/N6 są
nowe) — to była podstawa wątpliwości Codexa co do kierunku "zamrożone
D1-D5 + dodatkowe kody obok" (punkt sporny wyżej). OWNER mimo to
zdecydował: D1-D5/N1-N5 zostają zamrożone, zmienność obsługują wyłącznie
nowe, dodatkowe kody (patrz decyzja 1 powyżej) — to świadomy wybór węższy
niż to, co robi klient dziś w Excelu, nie przeoczenie.

## Powiązane materiały

- [[project_absence_hours_accounting_finding]] (pamięć CC) — wcześniejsza
  część tej samej rozmowy z Pawłem, ustaliła że PRE_PLAN_LEAVE (urlop
  wpisany z góry) dziś dekomponuje sumę godzin algorytmem "coin-change"
  minimalizującym liczbę kodów i zostawia resztę dni jako `X~` bez
  wartości — kontrastuje z realnym wzorcem z `Grafiki/7442.jpg`, gdzie
  KAŻDY dzień urlopu dostaje albo kod zmiany (dopasowany do cyklu D/N
  pracownika), albo "0", nigdy pustki. To osobny, nierozstrzygnięty
  wątek (dekompozycja urlopu), nie część tego findingu, ale ta sama
  rozmowa go ujawniła i może mieć wspólne miejsce naprawy w
  `schedule_export.py`.
- `Grafiki/7442.jpg`, `Grafiki/7732.jpg` — lokalne zdjęcia realnych kart
  pracy klienta (APEXIM/ROYALPACK), które CC obejrzał w rozmowie z
  Pawłem. NIE traktować jako dowód na konkretnym SHA — `7442.jpg` w
  working tree różni się od wersji w commicie, `7732.jpg` nie jest wcale
  w gicie (Codex to poprawnie złapał). Sekcja "Transkrypcja materiału
  referencyjnego" wyżej jest właściwym, weryfikowalnym źródłem do
  kontraktu.
