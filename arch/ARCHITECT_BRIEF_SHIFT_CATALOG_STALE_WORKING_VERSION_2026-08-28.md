# BRIEF DLA ARCHITEKTA — KATALOG ZMIAN ZAPISANY PO UTWORZENIU WERSJI WORKING NIE ODŚWIEŻA JEJ ZAPOTRZEBOWAŃ

**Stan:** ZGŁOSZENIE ZNALEZISKA — CC READ-ONLY, NIE READY FOR IMPLEMENTATION.
**Źródło:** realny obiekt testowy Pawła w `rota_dev.db`, znaleziony przy
okazji diagnozowania innego problemu (`ARCHITECT_BRIEF_NIGHT_STREAK_24H_FALSE_POSITIVE_2026-08-28.md`)
— **niezwiązane z tamtym zgłoszeniem**, wydzielone osobno na zalecenie
audytu, żeby nie rozszerzać zakresu przyszłego tasku solvera.

## 1. Obserwowane zachowanie

1. Koordynator tworzy nowy obiekt, PLAN tworzy pierwszą wersję `WORKING`
   dla miesiąca ZANIM katalog zmian został zapisany (pusty katalog →
   zero zapotrzebowań w tej wersji).
2. Koordynator zapisuje katalog zmian (np. przez Panel sterowania →
   Obiekt).
3. Koordynator klika "Przelicz (PLAN)" ponownie.

Oczekiwane: siatka grafiku pokazuje zapotrzebowania z nowego katalogu.
Rzeczywiste: siatka pozostaje pusta — `GET .../schedule/{month}` nadal
zwraca zero `demands` dla bieżącej wersji.

## 2. Przyczyna (potwierdzona czytaniem kodu)

`rota/application/plan_ops.py::plan_month`, gałąź dla istniejącej wersji
(`current_id is not None`, linie ~148-151): woła świeżo
`assemble_planning_state` i `plan()`, ale `_persist_decision_readback`
zapisuje wyłącznie bookkeeping `DECISION_REQUIRED`/jego wyczyszczenie —
NIGDY nie nadpisuje tabeli `shift_demands` dla istniejącej wersji.
`shift_demands` są zapisywane raz, przy TWORZENIU wersji
(`_create_first_version`), i pozostają niezmienne, dopóki `select_candidate`
nie zapisze wybranego kandydata na tę samą wersję.

Skutek: candidates zwrócone przez kolejne PLAN odzwierciedlają nowy
katalog (świeże w pamięci), ale odczyt miesiąca (`GET`) pokazuje starą,
pustą treść wersji, dopóki koordynator nie wybierze kandydata.

## 3. Obejście zastosowane w tej sesji (dev-baza Pawła)

Ręczne usunięcie wpisu w `current_schedule_versions` dla (site_id,
miesiąc), żeby kolejny PLAN nie znalazł żadnej bieżącej wersji i utworzył
zupełnie nową (poprawna gałąź `plan_month`, `current_id is None`) — to
zadziałało, ale to obejście na poziomie bazy, nie rozwiązanie produktowe.

## 4. Otwarte pytanie dla architekta (nie rozstrzygane tutaj)

Czy to jest w ogóle błąd, czy oczekiwane zachowanie wymagające innego kroku
koordynatora (np. jawne odrzucenie/reset roboczej wersji przed zmianą
katalogu)? Jeśli jest to błąd — czy naprawa polega na: (a) regenerowaniu
`shift_demands` istniejącej wersji WORKING przy każdym PLAN, gdy katalog
się zmienił, czy (b) dodaniu jawnej akcji koordynatora "odśwież wersję
roboczą po zmianie katalogu"? CC nie proponuje rozwiązania.

## 5. Poza zakresem

Niezwiązane z `ARCHITECT_BRIEF_NIGHT_STREAK_24H_FALSE_POSITIVE_2026-08-28.md`
— to osobny problem (persystencja/odświeżanie wersji), nie solver/CP-SAT.
