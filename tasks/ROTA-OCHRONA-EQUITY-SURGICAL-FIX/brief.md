# ROTA-OCHRONA-EQUITY-SURGICAL-FIX — przywrócenie sprawiedliwego podziału w OCHRONA

STATUS: PREIMPLEMENTATION — HOLD DO PRECHECKU ANTIGRAVITY/CODEX I DECYZJI OWNERA

SOURCE_REQUEST: BOARD.md / ROTA-TARGET-HOURS-CEILING-NOT-BULLSEYE, instrukcja
Architekta na `bdb563d`/decisive finding `c411bcf`, po diagnozie
`task/ROTA-TARGET-EQUITY-DIAGNOSIS`.

## 1. Zdiagnozowany problem (dowiedziony, nie hipoteza)

Ten sam kod solvera (snapshot sprzed 15.09, commit `900ef16`), te same
dane Royal, jedyna zmienna to kompletność wektora `target_hours`:

- Wektor NIEKOMPLETNY (co najmniej jeden aktywny LOCAL bez targetu) →
  awaryjny `add_equal_split_fairness`: rozstrzał **12h**
  (120/120/120/120/132/132).
- Wektor KOMPLETNY (dzisiejszy stan Royal po użyciu "Ustaw wszystkim") →
  TARGET-01: rozstrzał **120h** (48/60/144/156/168/168).

Gate `require_complete_target_hours` (`rota/application/plan_ops.py`,
15.09, task ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE) został zaprojektowany
i uzasadniony wyłącznie żywym repro na obiekcie FF (ORDINARY) — usunął
jednocześnie stary fallback (`add_equal_split_fairness`, `rota/planning/
fairness.py`) i wymusił kompletność wektora dla KAŻDEGO Site, obu reżimów.
Efekt uboczny dla OCHRONA: koordynator stracił możliwość pozostania w
niekompletnym, sprawiedliwym stanie — "Ustaw wszystkim" (funkcja
wprowadzona tym samym Taskiem) aktywnie pogarsza sprawiedliwość zamiast ją
poprawiać.

Legacy fallback NIE może wrócić bez zmian: ignorował absencje (prawdziwy,
osobny błąd z FF/ORDINARY, poprawnie naprawiony przez `_effective_targets`
już od 22.08, przed tym Taskiem — patrz `decisive_finding.md`).

**KOREKTA PO PRECHECKU ARCHITEKTA — dokładny mechanizm legacy fallbacku
(punkt precheku 1):** `add_equal_split_fairness` nie konsumuje żadnego
targetu — minimalizuje rozstrzał (max-min) **surowych** `worked_hours`
wśród dostępnych LOCAL. Nie "liczy na `_effective_targets`" (to było
niespójne sformułowanie w poprzedniej wersji briefu, wycofane). To
właśnie ten brak świadomości absencji w SUROWEJ metryce jest źródłem
oryginalnego błędu T041/FF: osoba na 80h urlopu i osoba bez urlopu
kończyły z niemal identyczną liczbą surowych `worked_hours`, bo fallback
wyrównywał złą wielkość.

**Zmierzony kompromis rozstrzał/rytm (punkt precheku 4, dane, nie
założenie):** `incomplete_vector_experiment.py`, 2 powtórzenia na
warunek, na Royal: niekompletny wektor (fallback) → rozstrzał 12h, **9
dopasowań rytmu D/N**; kompletny wektor (TARGET-01) → rozstrzał 72h,
**11 dopasowań**. **OWNER_CORRECTED 2026-09-20 (sekcja 3a)**: to NIE
oznacza, że sprawiedliwość i rytm są z natury nie do pogodzenia i trzeba
między nimi wybierać — solver ma już mechanizm hierarchii ważności, który
wcześniej respektował obie zasady naraz, sacrificing tylko gdy naprawdę
konieczne. Zmierzony spadek rytmu to sygnał do zweryfikowania przez
architekta, czy konkretne kodowanie poprawki poprawnie zachowuje tę
istniejącą hierarchię (patrz sekcja 3a) — nie powód do proszenia OWNERA
o wybór priorytetu.

## 2. Kryteria akceptacji (Architekt, dosłownie z BOARD.md)

1. Royal z kompletnymi targetami zachowuje prawie równy przydział jak
   historyczny fallback, bez regresji rytmu D/N lub budżetu czasu solvera.
2. Drugi realny obiekt OCHRONA bez targetów (`SITE-b8738d357a0f46fb97e0bd2d49565b52`)
   ponownie może PLAN/REPLAN.
3. OCHRONA z urlopem/delegacją nie dostaje pełnej pracy ponad godziny
   nieobecności — zgodnie z efektywnym limitem (`_effective_targets`).
4. ORDINARY bez zmian: bez targetów nadal blokuje (gate), z kompletnymi
   działa jak dziś (obecny algorytm, obecne wyniki, bez regresji).
5. Testy PLAN, REPLAN i precheck; HARD pass; czas solvera w dotychczasowym
   budżecie.

## 3. Zakres zmiany (do potwierdzenia/doprecyzowania przez Architekta+Codex)

CC nie projektuje ostatecznego kodowania CP-SAT — poniżej dwa kierunki
zidentyfikowane w diagnozie, oba zgodne z kryteriami powyżej, do wyboru
lub połączenia przez Architekta:

**Kierunek A — reżimowo odtworzony, absencjo-świadomy fallback.**
Przywrócić `add_equal_split_fairness`-podobny mechanizm dla
`SitePlanningRegime.OCHRONA` (ORDINARY bez zmian — gate kompletności
zostaje jak dziś, bo tam naprawił realny błąd), z dokładną semantyką
poniżej (odpowiedź na punkty precheku 2/3):

(a) **Metryka do wyrównania**: nie surowe `worked_hours` (oryginalny błąd
T041) i nie `_effective_targets` (niezdefiniowane dla osoby bez targetu —
punkt precheku 2). Zamiast tego wyrównywać **`worked_hours +
absence_hours + delegation_hours_in_range(...)`** — sumę godzin już
"zajętych" w miesiącu (rzeczywista praca + urlop/L4 + delegacja) —
niezależnie od tego, czy dana osoba ma wpisany target. To jedyna
zmiana konieczna, żeby nie powtórzyć błędu T041 (osoba na urlopie nie
dostaje PEŁNEGO nowego przydziału na wierzch absencji), bez wymyślania
nowego progu/wagi — używa już istniejącej, sprawdzonej funkcji
`rota.planning.absence.delegation_hours_in_range` i pola
`WorkBalance.absence_hours`.

(b) **Mieszany wektor (część osób ma target, część nie — punkt precheku
3)**: mechanizm aktywny dla WSZYSTKICH dostępnych LOCAL w OCHRONA
jednocześnie, niezależnie od indywidualnej kompletności; dla osoby, która
MA wpisany target, ten target działa wyłącznie jako SUFIT (nigdy jako
podłoga do "dobicia") — spójne z już wysłanym do architekta finding
`FINDING_2026-09-20_TARGET_HOURS_IS_A_CEILING_NOT_A_BULLSEYE.md`. Osoba
bez targetu nie ma sufitu, uczestniczy tylko w wyrównaniu opisanym w (a).

(c) **REPLAN / już przepracowane godziny (punkt precheku 3)**: bez zmian
względem obecnego mechanizmu `_fixed_hours_by_employee` — już
zaplanowane/przepracowane godziny liczą się do sumy jak dziś, fallback
tylko decyduje o rozkładzie NOWYCH, jeszcze nieprzydzielonych zmian.

(d) Aktywny NIEZALEŻNIE od kompletności wektora dla OCHRONA — nie tylko
jako fallback dla niekompletnego wektora (kryterium 1 wymaga
sprawiedliwości TAKŻE przy kompletnym wektorze, po "Ustaw wszystkim"),
raczej jako podstawowa ścieżka sprawiedliwości dla OCHRONA w miejsce
TARGET-01's `neg`-owej presji.

(e) gate `require_complete_target_hours` dla OCHRONA złagodzony/wyłączony
(kryterium 2), dla ORDINARY bez zmian.

**Kierunek B — wariant TARGET-01 bez presji "dobijania" (pos-only lub
tłumione `neg`), aktywny tylko dla OCHRONA.** Faza 3 diagnozy
(`pos_only_report.md`) pokazała, że usunięcie `neg` z TARGET-01 dla Royal
daje rozstrzał 12h — niemal identycznie jak historyczny fallback — ale
kosztem rytmu D/N (23→11 dopasowań) i budżetu czasu solvera (90s zamiast
1.8s, FEASIBLE zamiast OPTIMAL). Ten kierunek NIE spełnia kryterium 1
("bez regresji rytmu D/N lub budżetu czasu") w obecnej, najprostszej
formie (pełne zerowanie `neg`) — wymagałby złagodzonego wariantu (np.
tłumienie zamiast zerowania, próg tylko dla dużych niedoborów) i osobnego
pomiaru rytmu/czasu przed uznaniem za spełniający kryteria. Nie rozwiązuje
też kryterium 2 (gate) samodzielnie — potrzebowałby dodatkowo złagodzenia
gate dla OCHRONA, jak w kierunku A(d).

**CC nie ma preferencji między A i B — obie wymagają decyzji projektowej
Architekta**, którego CP-SAT owner to `rota/planning/solver.py`/`rota/
planning/fairness.py`. Modyfikowane pliki w obu kierunkach: `rota/planning/
fairness.py`, `rota/planning/solver.py`, `rota/application/plan_ops.py`
(gate), ewentualnie `api/routers/durable_inputs.py`/frontend (jeśli UI
"Ustaw wszystkim" ma się zmienić dla OCHRONA — do potwierdzenia, poza
zakresem tego briefu, jeśli architekt uzna że niepotrzebne).

## 3a. OWNER_CORRECTED 2026-09-20 — nie wybór priorytetu, przywrócenie hierarchii

Poprzednia wersja tej sekcji pytała OWNERA "co ma priorytet, rozstrzał
czy rytm" — OWNER wprost odrzucił to postawienie sprawy jako fałszywy
wybór 0/1: "w życiu nie jest tak jak byś chciał czyli 0/1... mnie
wkurza, że to już działało, a teraz do tego wracamy. Solver powinien
respektować wszystkie zasady i mieć hierarchię ważności gdy trzeba coś
poświęcić na rzecz czegoś innego. I to zostało zaprzepaszczone."

**Poprawne ujęcie, potwierdzone przez OWNERA ("Tak, zgadza się")**:
solver JUŻ MA mechanizm ścisłej hierarchii ważności między zasadami
SOFT (każda ważniejsza zasada ma wagę matematycznie dominującą sumę
wszystkich mniej ważnych — `_add_combined_objective`, wzorzec
"strictly dominate" używany konsekwentnie w tym kodzie, np. TARGET-01 nad
equity+rytm, dawny equal-split nad rytm+weekend+holiday). Ten mechanizm
działał poprawnie. To, co się zepsuło, to nie brak hierarchii — to że
TARGET-01 (kryterium celu godzinowego) dostało w tej hierarchii błędną
rolę: traktuje niedobicie do sufitu (`neg`) jako coś do naprawienia,
sztucznie wypychając sprawiedliwość i rytm z ich właściwych miejsc.
Poprawka MA przywrócić TARGET-01 do roli sufitu (kara tylko za
przekroczenie), żeby cała istniejąca hierarchia znów działała jak
wcześniej — nie ma tu do wyboru między sprawiedliwością a rytmem,
oba mają być respektowane wedle już istniejącej, sprawdzonej hierarchii.

**Ostrzeżenie z danych (do zweryfikowania przez architekta, nie do
rozstrzygania przez OWNERA)**: eksperyment pos-only (proste wyzerowanie
`neg`, `pos_only_report.md`) zmierzył spadek rytmu 23→11 na Royal. To
może oznaczać, że proste zerowanie `neg` jest ZŁYM sposobem przywrócenia
roli sufitu — jeśli psuje istniejącą hierarchię (np. equity i rytm mają
dziś RÓWNE wagi, `TARGET_EQUITY_WEIGHT=1`/`DN_RHYTHM_REWARD_WEIGHT=1`,
więc bez `neg`-owej presji różnicującej mogą zacząć swobodnie ze sobą
konkurować zamiast zachować zamierzoną kolejność) — a nie że
sprawiedliwość i rytm są z natury nie do pogodzenia. To pytanie
techniczne o poprawne kodowanie CP-SAT, nie pytanie do OWNERA — zostaje
w całości po stronie architekta+Codex do zweryfikowania i naprawienia
tak, żeby przywrócona hierarchia rzeczywiście działała jak przed
regresją, bez arbitralnego poświęcania którejkolwiek zasady.

## 4. Poza zakresem

- Żadna zmiana dla ORDINARY (gate, `_effective_targets`, TARGET-01,
  algorytm) — kryterium 4 wprost tego zabrania.
- Przywrócenie starego `add_equal_split_fairness` bez zmian (absence-blind)
  — wprost zabronione przez Architekta.
- Zmiana innych wag (weekend/holiday/rytm), HARD reguł, limitu czasu/gap
  poza tym, co wynika bezpośrednio z wybranego kierunku.

## 5. Dowody / materiały diagnozy (branch `task/ROTA-TARGET-EQUITY-DIAGNOSIS`)

- `decisive_finding.md` + `incomplete_vector_experiment.py` (zaktualizowany
  o pomiar rytmu, commit `c9b0f85`) — rozstrzygający dowód (sekcja 1).
- `pos_only_report.md` + `pos_only_experiment.py` — dane kierunku B.
- `regime_scope_finding.md` — chronologia gate'u i geneza na Ordinary/FF.

## 5a. Doprecyzowanie zakresu testów (punkt precheku 5)

Testy obejmują WYŁĄCZNIE istniejące wejścia PLAN/REPLAN/precheck (te same
funkcje wejściowe co dziś: `plan_ops.plan_month`/`replan_month`/
`precheck`), na obu obiektach OCHRONA z sekcji 2 (Royal — komplet
targetów; `SITE-b8738d357a0f46fb97e0bd2d49565b52` — brak targetów) oraz co
najmniej jednym obiekcie z MIESZANYM wektorem (część osób z targetem,
część bez) — żaden nowy system, endpoint ani ekran UI nie wchodzi w
zakres tego briefu.

## Verification (do wykonania po wyborze kierunku, przed implementacją)

- Precheck Antigravity/Codex na tym briefie (poprawność zakresu, ryzyko,
  kompletność kryteriów) — PRZED jakąkolwiek implementacją.
- Po precheku: pełny Task (branch `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX`),
  implementacja dopiero po PASS prechecku i decyzji OWNERA co do kierunku.
