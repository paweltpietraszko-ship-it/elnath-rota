# Handoff brief dla architekta — ROTA-T019b Odczyt DECISION_REQUIRED (decision guidance readback)

STATUS: OWNER INTENT — READY FOR ARCHITECT CONTRACT

DATE: 2026-08-20

TASK_ID: ROTA-T019b

BASE_BRANCH: main

BASE_SHA: 9618477f6014fad63699a154b04730e2b8ff1db2

RELATED: T013 (rota/planning/decision_guidance.py, DECISION_REQUIRED payload
treść/kontrakt), T019 (analityka koordynatora — osobny, równoległy read
model, bez zależności technicznej między T019 a T019b).

## 1. Intencja właściciela

Skąd wziął się ten task: przy przeglądzie briefu T019 właściciel zauważył, że
UI ma docelowo mieć przycisk pozwalający koordynatorowi podejrzeć treść
ostatniego DECISION_REQUIRED (blockery + unblocking options z T013) — nie
tylko w chwili, gdy plan()/replan() właśnie się wykonał, ale też później, "na
żądanie". Ten task ma dostarczyć minimalny read model do tego, analogicznie
do tego, co T019 robi dla WorkBalance. Nie ma tworzyć UI (to T021) ani zmieniać
treści/logiki samego payloadu (to zamrożone przez T013).

## 2. Fakt sprawdzony na BASE_SHA: brak persystencji

`rota/planning/decision_guidance.py::build_decision_payload()` zwraca
`DecisionRequiredPayload` (rota/planning/engine_types.py:32-36:
`blocking_shift_demands`, `blockers`, `load_blocker`, `unblocking_options`).

`rota/planning/engine.py` woła `build_decision_payload()` w czterech
terminalnych ścieżkach autonomy-boundary i pakuje wynik w
`PlanningResult(status="DECISION_REQUIRED", ..., payload, ...)`.

`rota/application/plan_ops.py::plan_month()` i `::replan()` wywołują `plan(state)`
i zwracają `PlanningResult` bezpośrednio do wywołującego, jednorazowo,
synchronicznie.

Sprawdzone: `rota/persistence/` nie zawiera żadnego pliku odwołującego się do
`DecisionRequired`, `decision_guidance` ani `PlanningResult` (`grep -rl` bez
wyników). Nie istnieje żadna tabela, repozytorium ani odczyt, który
przechowywałby albo pozwalał odtworzyć DECISION_REQUIRED wygenerowany przez
poprzednie wywołanie `plan()`/`replan()`. Po zwróceniu odpowiedzi do
wywołującego, payload nigdzie nie żyje dalej.

## 3. Konsekwencja dla przyszłego przycisku w UI (T021)

Jeżeli koordynator ma móc "podejrzeć zawartość" DECISION_REQUIRED w chwili
innej niż bezpośrednio po nieudanym plan()/replan() (np. po odświeżeniu
strony, po powrocie do zakładki), dzisiejszy kod nie ma z czego tego odczytać
— nie ma zapisanego stanu do pokazania. T021 nie może "skonsumować istniejącej
operacji", bo taka operacja readback dziś nie istnieje.

## 4. Zakres, który właściciel chce zamrozić w T019b (do potwierdzenia/doprecyzowania przez architekta)

Właściciel nie zamawia:

- zmiany treści/logiki DECISION_REQUIRED (T013 pozostaje jedynym właścicielem
  renderowania blockerów i unblocking options);
- zmiany solvera, `plan()`, `replan()` ani punktów wywołania w `engine.py`;
- UI w T019b (to T021);
- historii/audytu wielu poprzednich DECISION_REQUIRED — wystarczy odtworzyć
  najnowszy stan dla danego site/month, jeśli architekt uzna to za
  wystarczające; czy potrzebna jest historia, czy tylko "ostatni", jest
  pytaniem otwartym do architekta (patrz sekcja 5).

Właściciel oczekuje, że architekt określi:

- czy DECISION_REQUIRED wymaga nowej trwałości (nowa tabela/kolumna), czy da
  się odtworzyć bez zapisu (np. re-run `plan()` na żądanie w trybie
  wyłącznie-diagnostycznym, bez zapisu wyniku) — oba kierunki są otwarte,
  właściciel nie ma preferencji technicznej;
- jeśli potrzebna jest nowa trwałość: relację do `ScheduleVersion` (per
  wersja? per site+month niezależnie od wersji? nadpisywana przy każdym
  kolejnym plan()?) oraz zachowanie przy restore/select innej wersji;
- kształt minimalnego read modelu analogicznego do T019 (moduł w
  `rota/application/`, brak SQL w UI, deterministyczny wynik).

## 5. Pytania dla architekta — wyłącznie techniczne

1. Czy readback DECISION_REQUIRED wymaga nowej persystencji, czy wystarczy
   odczyt na żądanie bez zapisu (i jakie są konsekwencje wydajnościowe/
   spójności tego wyboru)?
2. Jeśli nowa persystencja: minimalny kształt (tabela/kolumna), relacja do
   `ScheduleVersion` i `site_id`+`month`, zachowanie przy nadpisaniu przez
   kolejny plan()/replan() i przy restore innej wersji.
3. Czy ma być "tylko najnowszy" per site+month, czy architekt widzi powód do
   historii — i czy to jest w ogóle w zakresie T019b, czy odrębny task.
4. Minimalny moduł/API do skonsumowania przez T021 bez importu
   `rota.persistence` ani `rota.planning` w UI.
5. Literalny TASK_SCOPE i macierz testów.

Żadne z tych pytań nie otwiera zmiany treści DECISION_REQUIRED zamrożonej w
T013.

## 6. Wymagany wynik pracy architekta

Zamrożony kontrakt `tasks/ROTA-T019b/brief.md`, ta sama bramka co T019: Codex
preimplementation audit -> CC implementacja -> backend.py + pełna suita ->
Codex implementation audit -> finalny gate architekta przed merge.

## 7. Relacja do T019, T020, T021

T019b jest równoległy do T019 (osobny read model, brak zależności
technicznej). T021 konsumuje read modele z obu tasków. T020 (wydruk) nie ma
dziś żadnej wskazanej zależności od T019b — architekt potwierdza, jeśli to się
zmieni.
