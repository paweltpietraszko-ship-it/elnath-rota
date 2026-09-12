# ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS — blokada wydruku przy świeżym niepotwierdzonym LAW

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE FINDING: `main@e4d150442deaa156b90d9ebfdf14155f70bd3588`

## 1. Cel

Zamknąć jedną lukę zgodności: program nie może wygenerować PDF grafiku, jeśli dokładnie ten drukowany grafik ma świeżo wykryte naruszenie kategorii `LAW`, którego koordynator nie potwierdził dla tej jednej próby wydruku.

To nie jest redesign lifecycle i nie jest nowy workflow decyzyjny. W szczególności nie tworzymy drugiego `DECISION_REQUIRED`, drugiego panelu, drugiego validatora ani osobnego subsystemu potwierdzeń.

## 2. Reuse istniejącej ścieżki komunikacji

T062 pozostaje wzorcem prezentacji: istniejący ekran `MonthlyPlanning` i istniejące powierzchnie komunikatu/ostrzeżenia mają być użyte ponownie.

Nie wolno tworzyć:
- nowego modala tylko dla eksportu;
- nowego modelu decyzji;
- nowej trwałej tabeli potwierdzeń eksportowych;
- trwałego `acknowledged=True` tylko dlatego, że użytkownik drukuje;
- nowego ekranu lub osobnego kroku lifecycle.

Reuse dotyczy komunikacji/UI i istniejącej listy odchyleń. Semantyka `DECISION_REQUIRED` z planowania nie jest rozszerzana na eksport.

## 3. Granica backendowa

Każdy request generowania PDF musi przed renderem:

1. zidentyfikować dokładnie bieżący `ScheduleVersion` dla `(site_id, month)`;
2. użyć istniejącego ownera świeżej walidacji / istniejącego validatora do ponownego wyliczenia odchyleń dla tego właśnie grafiku;
3. wyodrębnić tylko odchylenia kategorii `LAW`;
4. porównać je z jednorazowym potwierdzeniem dostarczonym przez ten request;
5. wygenerować PDF tylko wtedy, gdy wszystkie świeże LAW z tej próby zostały potwierdzone.

`WORKING` sam w sobie pozostaje drukowalny. Non-LAW nie blokują PDF.

Bezpośredni POST do endpointu eksportu nie może ominąć tej reguły.

## 4. Potwierdzenie tylko dla jednego wydruku

Potwierdzenie LAW dla eksportu:
- jest przekazywane tylko z bieżącego UI/requestu;
- obowiązuje tylko dla tej jednej próby wydruku dokładnej bieżącej wersji;
- nie jest zapisywane jako trwałe `Deviation.acknowledged`;
- nie finalizuje grafiku;
- nie zmienia statusu `ScheduleVersion`;
- nie tworzy `CoordinatorAction` ani `DECISION_REQUIRED` tylko z powodu wydruku;
- następny eksport przy nadal istniejącym LAW wymaga ponownego potwierdzenia.

## 5. Tożsamość potwierdzanego LAW

Nie wolno opierać eksportowego potwierdzenia wyłącznie na obecnym `deviation_id` typu `DEV-{index}-{rule}`, ponieważ taki ID nie identyfikuje wystarczająco faktu naruszenia.

Najwęższy kontrakt: backend buduje stabilny fingerprint z pełnych strukturalnych danych świeżego LAW, które już istnieją w `Deviation` i jego źródłowym fakcie, bez parsowania ludzkiego `message`.

Fingerprint musi odróżniać co najmniej różne:
- reguły;
- affected assignment/employee;
- source reference / target;
- istotny fakt naruszenia, jeśli jest dostępny strukturalnie.

Nie projektować uniwersalnego systemu fingerprintów dla całego produktu. To ma być wąski identyfikator dla jednorazowego eksportowego ack.

## 6. Spójność check -> render

Walidacja i wygenerowanie PDF muszą dotyczyć tej samej bieżącej wersji.

Jeżeli current version zmieni się między fresh-checkiem a renderem, eksport ma odmówić i poprosić o ponowienie zamiast wygenerować dokument dla innego stanu.

Nie budować nowego transaction/lifecycle subsystemu. Użyć istniejącego `version_id` / revision / provenance, które exporter już zna.

## 7. UI

Istniejąca lista `Odchylenia` pozostaje jedynym miejscem wskazywania LAW przez koordynatora.

`Wygeneruj PDF`:
- przy braku świeżych LAW działa jak dziś;
- przy świeżych LAW, których bieżąca próba nie potwierdza, nie generuje PDF;
- pokazuje istniejącą powierzchnią komunikatu prosty komunikat, że przed wydrukiem trzeba potwierdzić wskazane odchylenia prawne;
- po zaznaczeniu wymaganych LAW koordynator ponawia `Wygeneruj PDF`;
- non-LAW nie muszą być zaznaczone dla wydruku.

Nie dodawać drugiego panelu ani modala.

## 8. Stary preview PDF

Jeżeli eksport zostaje zablokowany z powodu świeżego LAW albo bieżący grafik/miesiąc/obiekt zmienia się przed kolejnym eksportem, UI nie może pozostawiać starego `previewBlob` jako aktualnie oferowanego dokumentu.

To jest mechaniczna ochrona przed pobraniem starego PDF po zmianie stanu, nie nowy lifecycle.

## 9. Acceptance

P1. Legalny `WORKING` bez LAW nadal generuje PDF.

P2. Grafik z non-LAW, ale bez LAW, nadal generuje PDF bez dodatkowego potwierdzenia.

P3. Świeże niepotwierdzone LAW blokuje PDF i zwraca czytelny komunikat do istniejącej powierzchni UI.

P4. Bezpośredni POST bez wymaganego export-ack również jest blokowany.

P5. Potwierdzenie wszystkich świeżych LAW dla tej jednej próby pozwala wygenerować PDF.

P6. Potwierdzenie eksportowe nie zmienia persisted `Deviation.acknowledged`, statusu wersji, lifecycle ani historii decyzji.

P7. Kolejna próba eksportu tego samego grafiku z tym samym LAW znów wymaga potwierdzenia.

P8. Zmiana faktu naruszenia przy tej samej regule/indexie nie może odziedziczyć starego potwierdzenia; fingerprint musi się różnić.

P9. Zmiana current version pomiędzy walidacją a renderem nie może wygenerować PDF dla niesprawdzonego stanu.

P10. Po zablokowanym eksporcie lub zmianie site/month/current UI nie oferuje starego preview jako aktualnego PDF.

P11. Brak nowego `DECISION_REQUIRED`, nowej tabeli, nowego modala i nowego validatora.

## 10. Literalny TASK_SCOPE

Production — oczekiwany minimalny zakres:
- `rota/application/schedule_export.py` — świeży LAW guard związany z dokładnie eksportowaną wersją; reuse istniejącego validatora/assemblera;
- `api/routers/export.py` — transport jednorazowych LAW fingerprints/ack oraz ludzki komunikat problemu;
- `frontend/src/components/Export.tsx` — przekazanie bieżących zaznaczonych LAW i unieważnienie starego preview;
- `frontend/src/screens/MonthlyPlanning.tsx` — wyłącznie jeśli potrzebne mechaniczne przekazanie istniejącej listy/zaznaczeń LAW do `Export`; bez nowego panelu;
- `frontend/src/api/client.ts` — wyłącznie mechaniczna zmiana request type/API call;
- istniejący helper walidacji/application layer tylko jeśli Codex wskaże konkretną brakującą ścieżkę reuse; bez drugiego validatora.

Tests:
- nowy wąski `tests/test_export_unacknowledged_law.py`;
- istniejący test/export E2E rozszerzony tylko o P1–P10;
- bez symulatorów, benchmarków i pełnego lifecycle redesignu.

Jawnie poza scope:
- zmiana reguł LAW;
- zmiana manual correction;
- REPLAN/restore redesign;
- finalization redesign;
- nowy decision model;
- nowa trwała tabela ack;
- blokowanie wszystkich WORKING;
- blokowanie non-LAW;
- techniczne identyfikatory UI jako osobny finding;
- `ROTA-TECHNICAL-ERROR-RECOVERY-UX`.

## 11. Preimplementation re-check Codexa

Sprawdzić tylko:
1. czy `schedule_export` może użyć istniejącego assemblera/validatora i związać wynik z dokładnie renderowaną current version bez nowego validatora;
2. czy obecne dane `Deviation` wystarczą do stabilnego eksportowego fingerprintu bez parsowania `message`; jeśli nie, wskazać dokładnie brakujące pole, bez redesignu domeny;
3. czy frontend może reuse istniejącą listę/zaznaczenia LAW i przekazać je do `Export` bez drugiego panelu/modala;
4. czy stary preview da się mechanicznie unieważnić na zmianę export result/site/month/current;
5. czy literalny scope jest kompletny.

Jeżeli 1–5 = TAK: PASS exact brief SHA i zwolnienie IMPLEMENTATION HOLD. Jeżeli NIE: wskazać jedną konkretną lukę ścieżki lub pola; bez poszerzania do lifecycle/REPLAN/restore.