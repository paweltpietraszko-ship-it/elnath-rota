# Prośba do Codexa: niezależna diagnoza Symulatora Koordynatora + brief naprawczy

Status: **PROŚBA O DIAGNOZĘ I BRIEF, NIE BRIEF SAM W SOBIE — CC celowo nie
pisze tego briefu, patrz sekcja "Dlaczego Codex, nie CC" niżej.**

## Kontekst rozmowy z OWNER (2026-08-30, dosłownie)

> "Cc, mnie najbardziej wkurza sytuacja gdy wasze testy sa zielone a ja na
> pierwszym grafiku widzę bzdury, nie mówię, że tak jest teraz bo na razie
> codex robi testy. Mam wrażenie, że nie testujemy profesjonalnie i to nie
> mozliwe, że w tych czasach nie ma automatycznych, deterministycznych
> narzędzi, które sprawdzaja pracę LLMa."
>
> "Potzrebuję Task który nie będzie pudrować rzeczywistości tylko naprawdę
> sprawdzi gdzie kod sie wywala lub produkuje bzdury bo teraz nie mam żadnej
> pewności, że Rota działa. Musimy sprawdzic to co audyt mógł tylko
> zakładać lub domyslać się. Tylko pytanie czy przed naprawa Symulatora czy
> po?"
>
> "Ty napisałes Symulator i sa dwie drogi: albo ty piszesz brief naprawczy
> bo znasz kod i wiesz co poprawić albo codex bo ty będziesz bronić swojej
> pracy"

OWNER zaakceptował rekomendację: nie sekwencjonować "napraw Symulator" i
"użyj go do sprawdzenia rzeczywistości" jako dwóch osobnych Tasków. Kryterium
odbioru ma być **raport, który OWNER faktycznie przeczyta**, nie zielone
testy o poprawionym narzędziu.

## Dlaczego Codex, nie CC

CC zaprojektował i zaimplementował Symulator (ROTA-T038/T039). CLAUDE.md już
zabrania CC self-review/self-approval własnej pracy produktowej — ta sama
zasada dotyczy pisania briefu naprawczego dla własnego wcześniejszego
projektu narzędzia: nawet bez złej woli, CC ma strukturalną skłonność
interpretować niejasności na korzyść wcześniejszych decyzji projektowych.
OWNER wskazał to wprost i CC się z tym zgadza. Diagnoza przyczyn i treść
briefu naprawczego mają być niezależne od CC.

## Materiał źródłowy do wglądu (kontekst, nie ograniczenie)

- `tasks/ROTA-T038/brief.md`, `round_01/tests/tests_r1.txt`..`tests_r3.txt` —
  oryginalny brief i rundy audytu Symulatora.
- `tasks/ROTA-T039/brief.md`, `round_01/tests/*` — kontynuacja T038.
- `tasks/ROTA-T038/round_01/tests/simulator_report.md` — ostatni realny
  raport wygenerowany przez narzędzie.
- `tests/property/coordinator_simulator.py` (343 linie),
  `tests/property/test_coordinator_simulator.py` (233 linie) — obecny kod.
- Pełen plan projektowy z sesji, w którym ustalono zasadę "liczba
  pracowników musi wynikać z realnego zapotrzebowania godzinowego obiektu,
  nigdy nie może być losowana niezależnie od niego" — załączony niżej w
  całości, żeby diagnoza nie zaczynała się od zera:

<details>
<summary>Pełny plan projektowy T038 KOREKTA 2 (rozwiń)</summary>

```markdown
# Symulator Koordynatora — KOREKTA 2 (OWNER_CORRECTED, 2026-08-28)

## Context

T038 v1 (`f6d1b85`) był property-based benchmarkiem oceniającym niezmienniki
solvera — odrzucone: "nie projektuj warstwy zarządzającej solverem, tylko
cienką warstwę klikającą ptaszki i reportującą". Pierwsza próba korekty
(jeden ustalony obiekt) też odrzucona: Paweł chce RÓŻNE wymyślone obiekty i
RÓŻNE wymyślone scenariusze absencji, nie jeden sztywny przypadek.

Kluczowa zasada, ustalona po kilku rundach dopytywania (nie zgadywania):
**liczba pracowników na wymyślonym obiekcie musi wynikać z realnego
zapotrzebowania godzinowego tego obiektu, nigdy nie może być losowana
niezależnie od niego.** Paweł złapał dokładnie ten błąd w v1: tam
`employee_count` był losowany 4-8 kompletnie niezależnie od tego, ile
godzin pracy obiekt faktycznie generował.

## Zasada projektowa (fundament tej korekty)

Każdy wymyślony obiekt: NAJPIERW ustalam zapotrzebowanie godzinowe
(liczba posterunków/zmian dziennie x wymagana liczba osób na zmianę x
długość zmiany x dni w miesiącu), POTEM liczę realistyczną obsadę
(ceil(godziny_miesięcznie / realistycznych_godzin_na_osobę) + mały margines
na rotację/REST), i DOPIERO z tej wyliczonej liczby buduję roster.

Zmienność między wymyślonymi obiektami bierze się z wariowania SAMEGO
ZAPOTRZEBOWANIA (liczba równoległych posterunków/wymaganych osób na zmianę:
1-3; kształt zmiany: D/N 12h vs pojedyncza 24h; regime OCHRONA/ORDINARY),
nie z niezależnego losowania obsady.

Absencje (chorobowe/urlop/wolne na żądanie) WCIĄŻ losowane z ziarna na
każdym wygenerowanym obiekcie.

## Generator (tests/property/coordinator_simulator.py)

random_object_spec(seed, month) -> ObjectSpec:
1. Losuje zapotrzebowanie: shift_shape, posts (1-3), regime,
   rolling_7d_threshold_hours.
2. Liczy monthly_hours_needed.
3. Liczy employee_count = ceil(monthly_hours_needed / 160) + margin.
4. Osobno external_support.
5. DAY_ONLY mix: podzbiór lokalnych.

random_absence_set(...) — 0-3 rekordy, seed=0 = "wszyscy dostępni".

## Driver — klika i raportuje, nic nie osądza

Dla każdego seeda (świeża :memory: baza): zbuduj obiekt przez prawdziwe
HTTP -> zaaplikuj absencje -> PLAN -> zapisz do raportu. Druga faza:
kolejna absencja -> REPLAN -> też zaraportowane.

Jedyna assercja: brak wyjątku/brak 5xx. Status PLAN/REPLAN, liczba
faktycznie użytych pracowników vs zadeklarowana obsada, treść powodu przy
DECISION_REQUIRED -- wszystko trafia do raportu jako fakty, nie werdykt.

## Raport

tasks/ROTA-T038/round_01/tests/simulator_report.md. Na wpis: zapotrzebowanie,
obsada, pełna lista osób, absencje, status PLAN+powód, status REPLAN+powód,
liczba i lista faktycznie użytych employee_id.
```

</details>

## Znane, już potwierdzone problemy z tym obszarem (z AUDIT-3, punkt 6)

- README i komentarz Symulatora nadal przedstawiają stare benchmarki
  (`benchmarks/real_object`, `rota_stress`, `manual_audits`) jako źródło
  oceny poprawności, choć OWNER tę rolę odrzucił
  ([[feedback_no_benchmarks_generator_ever]] w pamięci CC — Symulator
  koordynatora jest jedynym zaakceptowanym narzędziem tego typu). Pełny
  pytest nadal zbiera stare benchmarki, więc "wszystkie zielone" miesza
  testy o różnej wartości dowodowej.
- Symulator zapisuje wynik zwykłego uruchomienia testów bezpośrednio do
  historycznego, śledzonego raportu T038 (`simulator_report.md`). Zmienna
  `ROTA_SIM_SEEDS` może zmienić ten plik jako efekt uboczny zwykłego
  odpalenia testów -- historyczny dowód może zostać nadpisany bez żadnej
  celowej decyzji.

AUDIT-3 sam to nazwał wprost: to są **domysły/założenia z czytania kodu**,
nie potwierdzone uruchomieniem. To jest właśnie luka, którą OWNER chce
zamknąć.

## Prośba do Codexa

1. Niezależnie zdiagnozuj: dlaczego obecny stan Symulatora nie daje OWNER
   pewności, że Rota działa. To może obejmować (nie ogranicza się do):
   błędy w samym generatorze/driverze, błędy w tym, co i jak raportuje,
   błędy w interpretacji wyniku, albo że Symulator w ogóle nie był
   uruchamiany od dłuższego czasu i stan jest nieznany.
2. Napisz brief naprawczy (`tasks/ROTA-T0??/brief.md`) którego **kryterium
   odbioru to realny raport z uruchomienia na kilku różnych obiektach**
   (różne regime'y, różne rozmiary, z i bez absencji), gotowy do
   przeczytania przez OWNER wprost -- nie "testy X/Y PASS".
3. Rozstrzygnij samodzielnie, czy "naprawa narzędzia" i "wygenerowanie
   pierwszego wiarygodnego raportu" powinny być jednym Taskiem, czy jednak
   dwoma powiązanymi -- ten dokument to punkt wyjścia, nie zamknięta
   specyfikacja. Jeśli uznasz, że coś z powyższego planu projektowego jest
   już nieaktualne albo błędne, powiedz to wprost w brief.md zamiast po
   cichu to obchodzić.
4. Nie przyjmuj żadnej mojej (CC) wcześniejszej decyzji projektowej w tym
   obszarze jako z góry słusznej -- to jest właśnie ten obszar, gdzie masz
   być niezależny.
