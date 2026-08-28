# ROTA-T037 — Ręczna korekta wbudowana w Planowanie miesiąca + Wydruk jako sekcja

Status: **IMPLEMENTACJA ZAKOŃCZONA (autor: CC), do audytu**

Base implementation SHA: `aa6330cd32d3f891777cc148805527bc307bd719` (`main`,
po zmergowaniu T021).

Owner decision: Paweł, 2026-08-28 (rozmowa, nie osobny dokument architekta) —
kontynuacja dyskusji z audytu PR #9 (za dużo osobnych ekranów grafiku).
Kolejne, jawne rozstrzygnięcia tej samej rozmowy:
1. Ekran "Wydruk Grafiku" (`Export.tsx`) już istnieje i działa — nie ruszać.
2. Realny brak to "Ręczna korekta" — w menu widniała jako `disabled`, backend
   (`rota/application/manual_edit.py`) istniał, ale bez API routera.
3. Ręczna korekta logicznie należy do Planowania miesiąca (koordynator widzi
   problem na siatce i poprawia go bez przeskoku na inny ekran), nie do
   Wydruku.
4. Wydruk mimo to wchodzi jako zwijana sekcja w Planowaniu (ten sam komponent
   `Export.tsx`, żadnej duplikacji logiki).
5. Obie pozycje ("Ręczna korekta", "Wydruk Grafiku") zostają DODATKOWO w menu
   jako powielone skróty do tej samej treści — na wyraźną prośbę właściciela,
   nie architektoniczna konieczność.
6. Zakres wąski: **bez** dry-run/preview przed zapisem (funkcja opisana w
   `arch/T021_spec.md` sekcja "Ręczna korekta" jako "foundational, must
   build" — świadomie odłożona). HARD violation nigdy nie blokuje zapisu
   (to już istniejące zachowanie `apply_manual_correction`) — po zapisie
   trafia jako `Deviation` do już istniejącego panelu "Odchylenia" na
   Planowaniu (żadnego nowego banera/mechanizmu ostrzegania).
7. Instrukcja właściciela w trakcie budowy: unikać nadmiarowego kodu/logiki,
   pamiętając o wnioskach audytu PR #9 (`arch/ARCHITECT_BRIEF_CODE_INVENTORY_AUDIT_2026-08-28.md`)
   o narastającej złożoności.

TASK_SCOPE:
- api/main.py
- api/errors.py
- api/routers/manual_edit.py (nowy plik)
- frontend/src/api/client.ts
- frontend/src/screens/Room.tsx
- frontend/src/screens/MonthlyPlanning.tsx
- tests/test_t037_manual_edit_api.py
- run_dev.bat (nowy plik, dev-convenience na wyraźną prośbę właściciela —
  odpala backend `.venv`/uvicorn:8123 + frontend vite:5173 w dwóch oknach)

## 1. Wynik dla właściciela

Na ekranie "Planowanie miesiąca": klik w komórkę siatki z istniejącym
przypisaniem otwiera panel ręcznej korekty (przypisz innej osobie / zamroź-
odmroź / oznacz jako nieprzepracowane — NN). Zapis zawsze się udaje, nawet
jeśli tworzy naruszenie HARD — naruszenie pojawia się w istniejącym panelu
"Odchylenia" po odświeżeniu. Poniżej historii wersji: zwijana sekcja
"Wydruk" z tym samym generatorem PDF co osobny ekran Wydruku. W menu:
"Ręczna korekta" i "Wydruk Grafiku" to dodatkowe, powielone wejścia do tego
samego ekranu Planowania (nie osobna logika).

## 2. Istniejący backend jest właścicielem

Zero zmian w `rota/**`. Nowy router tylko marshaluje trzy istniejące funkcje:

- `apply_manual_correction(conn, site_id, month, coordinator_id, effective_from, upsert_assignments, note=None, responds_to_decision_required_id=None)`
  — `rota/application/manual_edit.py:285`.
- `freeze_or_unfreeze(conn, ..., assignment_id, frozen)` — tamże, linia 337.
- `mark_not_worked(conn, ..., assignment_id)` — tamże, linia 358.

Jedyny odkryty i naprawiony bug: `ScheduleVersion` zwracany przez te funkcje
nie ma pola `deviations` — trzeba je odczytać przez
`get_schedule_snapshot(conn, version.version_id).deviations`, ten sam wzorzec
co istniejący `MonthViewOut` (`api/routers/schedule.py`).

## 3. Poza zakresem (świadomie)

- Dry-run/preview przed zapisem (odłożone, patrz punkt 6 wyżej).
- Dodawanie nowego przypisania na pustą komórkę (coverage-gap repair przez
  UI) — `apply_manual_correction` to obsługuje, ale UI tego jeszcze nie
  wystawia; tylko edycja istniejących przypisań w tej rundzie.
- Jakakolwiek zmiana nawigacji poza dodaniem "Ręczna korekta" do
  `BUILT_NAV_ITEMS` w `Room.tsx`.
- Refaktor `engine.py`/`durable_inputs.py` z audytu PR #9 — czeka na swoją
  kolej, nie część tego taska.

## 4. Weryfikacja

- `tsc --noEmit` czysty.
- `python -c "from api.main import app"` czysty.
- Logika 3 endpointów zweryfikowana jednorazowym, szybkim skryptem
  (pojedynczy przebieg solvera) — nie pełnym `pytest`, żeby nie mnożyć
  kosztownych przebiegów CP-SAT w trakcie iteracji (zgłoszona przez
  właściciela uwaga o czasie sesji).
- `tests/test_t037_manual_edit_api.py` napisany, czeka na jeden formalny
  przebieg przy tym audycie/backend.py gate.
