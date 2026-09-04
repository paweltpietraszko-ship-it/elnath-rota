# ROTA-T053 — jeden wspólny miesiąc roboczy koordynatora

STATUS: READY FOR PREIMPLEMENTATION RE-AUDIT — ZERO KODU PRODUKTU

BASE_MAIN_SHA: `7cd5fde8446bd08a02c647d4eabaab9db200acba`

Źródła:
- `arch/FINDING_2026-09-03_GLOBAL_WORKING_MONTH.md`
- `arch/ARCHITECT_HANDOFF_UX_BACKLOG_06_08_2026-09-03.md`
- decyzje OWNERA 2026-09-03
- PREIMPLEMENTATION AUDIT round_01 — FAIL mechaniczny: `Export.tsx` posiada własny miesiąc i musi wejść do TASK_SCOPE

## 1. Cel

Koordynator wybiera miesiąc roboczy raz. Ekrany pracujące na miesiącu używają tego samego wyboru. Ponowne wybieranie tego samego miesiąca na każdym ekranie ma zniknąć.

To jest zadanie frontendowe. Nie tworzyć backendowego pojęcia „globalnego miesiąca”, nie zmieniać solvera, wersjonowania grafiku ani kontraktu domenowego.

## 2. Decyzje OWNERA — zamrożone dla tego tasku

1. Wybrany miesiąc obowiązuje wspólnie podczas przechodzenia między ekranami.
2. Wybór ma przetrwać odświeżenie aplikacji.
3. Po zmianie obiektu zachowujemy ten sam wybrany miesiąc.
4. Jeżeli koordynator wybierze później inny miesiąc, nowy wybór staje się od tej chwili domyślnym miesiącem roboczym całej aplikacji.
5. `Decyzje koordynatora` są wyjątkiem: lista realnych miesięcy z `DECISION_REQUIRED` nie jest globalnym selektorem i nie wolno jej przepinać na working month.
6. Nie łączyć tasku z konsolidacją ekranów ani szerszym redesignem.
7. Opis okresu na wydruku ma wynikać z wybranego miesiąca; nie utrzymywać osobnego źródła prawdy dla tego samego okresu.

## 3. Właściciel logiki

`frontend/src/screens/Room.tsx` już posiada stan współdzielony między ekranami (`activeNav`, `controlPanelTab`, `decisionContext`). Working month ma użyć tego istniejącego poziomu kompozycji, bez nowego globalnego store.

Trwałość po reloadzie: najprostszy lokalny mechanizm przeglądarki (`localStorage` lub istniejący równoważny helper, jeżeli repo już go ma). Wartość jest kontekstem koordynatora, nie własnością Site.

## 4. Ekrany/funkcje objęte

MUST używać working month:
- `MonthlyPlanning` — wraz z wejściami „Ręczna korekta” i „Wydruk Grafiku”, które zgodnie z T037/T041 są tą samą instancją ekranu;
- `Analytics`;
- miesięczny kontekst w `EmployeeDetail`;
- `Export.tsx` — jego istniejący własny miesiąc/period source musi zostać przepięty na working month tam, gdzie nadal uczestniczy w aktualnym flow wydruku.

MUST NOT być przepinane:
- `Decisions` — zachowuje własną listę miesięcy z faktycznymi oczekującymi decyzjami;
- `History`, jeżeli nie ma selektora miesiąca służącego pracy na jednym miesiącu;
- inne ekrany bez istniejącej semantyki month input.

## 5. Zachowanie

- Pierwsze uruchomienie bez zapisanej wartości: bieżący miesiąc kalendarzowy `YYYY-MM`.
- Zmiana selektora na np. `2026-10`: wszystkie objęte ekrany natychmiast pracują na `2026-10`.
- Przejście do innego ekranu nie resetuje miesiąca.
- Reload aplikacji przywraca ostatnio wybrany miesiąc.
- Przejście na inny obiekt nie resetuje miesiąca.
- Kolejna ręczna zmiana miesiąca nadpisuje zapamiętaną wartość i staje się nowym domyślnym working month.
- Nieprawidłowa/brakująca wartość w storage: fail-soft do bieżącego miesiąca, bez awarii aplikacji.
- Wydruk używa tego samego miesiąca do okresu; nie może pozostać drugi niezależny month picker/period source reprezentujący ten sam okres.

## 6. UI

Selektor ma być widoczny na poziomie `Room` w stałym miejscu wspólnym dla ekranów obiektu (najprościej topbar/breadcrumb area). Nie projektować nowej nawigacji.

Ekrany objęte taskiem nie powinny dalej prezentować własnych niezależnych selektorów tego samego miesiąca. Jeżeli `EmployeeDetail` wymaga chwilowego innego miesiąca z przyczyny funkcjonalnej, preimplementation audit musi wskazać konkretny istniejący flow; bez takiego dowodu używa working month.

## 7. TASK_SCOPE

Dozwolony kod produktu:
- `frontend/src/screens/Room.tsx`
- `frontend/src/screens/MonthlyPlanning.tsx`
- `frontend/src/screens/Analytics.tsx`
- `frontend/src/screens/EmployeeDetail.tsx`
- `frontend/src/screens/Export.tsx`
- tylko istniejący komponent/helper frontendowy dla persistence miesiąca, jeżeli jego użycie pozwala uniknąć duplikacji; bez tworzenia frameworka state-management
- istniejący CSS dotyczący `Room`/topbar, wyłącznie jeśli potrzebny do umieszczenia selektora

Dozwolone dokumenty/testy:
- `tasks/ROTA-T053/brief.md`
- najmniejszy test frontendowy istniejącym mechanizmem repo lub pionowy test UI

Poza zakresem:
- Python backend/API
- DB
- solver/validator
- `Decisions.tsx` poza ewentualnym dowodem, że pozostaje niezależne
- redesign/konsolidacja ekranów
- nowy globalny store/context framework

## 8. Acceptance

T53-01: koordynator wybiera październik na wspólnym selektorze; `MonthlyPlanning`, `Analytics`, `EmployeeDetail` i aktualny flow wydruku używają października bez ponownego wyboru.

T53-02: przejście między ekranami nie zmienia miesiąca.

T53-03: reload aplikacji zachowuje październik.

T53-04: przejście z obiektu A do B zachowuje październik.

T53-05: zmiana na listopad powoduje, że listopad staje się nowym working month i po reloadzie nadal nim jest.

T53-06: `Decyzje koordynatora` nadal pokazują faktyczne miesiące z oczekującymi decyzjami i nie są filtrowane/sterowane working month.

T53-07: wydruk/preview/download używa working month; `Export.tsx` nie utrzymuje niezależnego wyboru okresu reprezentującego ten sam miesiąc.

T53-08: uszkodzona wartość storage nie wywraca UI; aplikacja wraca do bieżącego miesiąca.

## 9. PREIMPLEMENTATION RE-AUDIT

Codex/niezależny audytor ma po mechanicznej korekcie potwierdzić:
- dokładne istniejące month inputs;
- że `Room.tsx` jest najwęższym istniejącym wspólnym ownerem stanu;
- że `Decisions` jest prawidłowym wyjątkiem;
- że `Export.tsx` jest już objęty zakresem i nie pozostaje w nim niezależne źródło month/period dla tego samego wydruku;
- czy w repo istnieje helper do localStorage, który należy reuse zamiast pisać nowy.

PASS nie może rozszerzać kontraktu. Test nie tworzy wymagania.

Oczekiwany werdykt: `PASS — READY_FOR_IMPLEMENTATION` albo `FAIL` z konkretną sprzecznością w aktualnym kodzie.

## 10. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T053/brief.md
- frontend/src/screens/Room.tsx
- frontend/src/screens/MonthlyPlanning.tsx
- frontend/src/screens/Analytics.tsx
- frontend/src/screens/EmployeeDetail.tsx
- frontend/src/screens/Export.tsx
- frontend/src/App.css
- frontend/e2e/monthly-planning.spec.ts
- frontend/e2e/t041-daily-workflow.spec.ts
- frontend/e2e/t042-local-date.spec.ts
- frontend/e2e/t053-independent-audit.spec.ts
