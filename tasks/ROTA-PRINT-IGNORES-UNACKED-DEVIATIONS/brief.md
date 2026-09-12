# ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS — blokada wydruku przy świeżym niepotwierdzonym LAW

STATUS: FINAL PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE FINDING: `main@e4d150442deaa156b90d9ebfdf14155f70bd3588`
PRECHECK R1: `66e348c00ce1a64a499cd16a4067267d0e2a6411`

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
2. użyć jednego współdzielonego application-layer helpera świeżej walidacji opartego o istniejące `assemble_planning_state(..., schedule_version_id=...)` + `validate(...)`; helper ma zastąpić duplikowanie przebiegu w lifecycle/export, nie tworzyć drugiego validatora;
3. wyodrębnić tylko świeże odchylenia kategorii `LAW`;
4. z tych samych świeżych `ViolationDetail` i wskazanych przez nie strukturalnych Assignment/Demand zbudować minimalne rekordy eksportowego LAW wraz z fingerprintem;
5. porównać fingerprinty świeżych LAW z jednorazowym potwierdzeniem dostarczonym przez ten request;
6. wygenerować PDF tylko wtedy, gdy wszystkie świeże LAW z tej próby zostały potwierdzone.

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

## 5. Tożsamość i transport świeżego LAW

Nie wolno opierać eksportowego potwierdzenia wyłącznie na obecnym `deviation_id` typu `DEV-{index}-{rule}`, ponieważ taki ID nie identyfikuje wystarczająco faktu naruszenia.

Najwęższy kontrakt:
- fingerprint powstaje backendowo podczas świeżej walidacji, bez parsowania ludzkiego `message`;
- źródłem są `ViolationDetail` oraz strukturalne dane Assignment/Demand wskazane przez ten violation;
- fingerprint musi odróżniać co najmniej różne: reguły, affected assignment/employee, demand/target/source reference i istotny fakt naruszenia dostępny strukturalnie;
- nie projektować uniwersalnego systemu fingerprintów dla całego produktu; to jest wąski identyfikator dla jednorazowego eksportowego ack.

Blokująca odpowiedź eksportu musi zwrócić minimalną listę świeżych LAW potrzebną do istniejącej powierzchni `Odchylenia`. Każdy element zawiera:
- backendowy `fingerprint`;
- istniejące, ludzkie dane prezentacyjne potrzebne do pokazania tego LAW w obecnej liście;
- bez nowego modelu domenowego i bez trwałego zapisu.

Ponowienie requestu eksportu przesyła wyłącznie zaznaczone fingerprinty świeżych LAW. `deviation_id` może pozostać elementem prezentacyjnym/istniejącego UI, ale nie jest podstawą autoryzacji eksportu.

## 6. Spójność check -> render

Walidacja i wygenerowanie PDF muszą dotyczyć tej samej bieżącej wersji.

Eksporter zapamiętuje oczekiwany current `version_id`, składa i waliduje tę konkretną wersję, renderuje tę samą wersję i przed zwrotem ponownie sprawdza current. Jeżeli wskaźnik zmienił się w międzyczasie, wygenerowane bajty są odrzucane i użytkownik ma ponowić próbę.

Nie budować nowego transaction/lifecycle subsystemu. Użyć istniejącego `version_id` / revision / provenance.

## 7. UI

Istniejąca lista `Odchylenia` pozostaje jedynym miejscem wskazywania LAW przez koordynatora.

`Wygeneruj PDF`:
- przy braku świeżych LAW działa jak dziś;
- przy świeżych LAW, których bieżąca próba nie potwierdza, nie generuje PDF;
- blokująca odpowiedź zasila istniejącą listę `Odchylenia` świeżymi LAW/fingerprintami i istniejącą powierzchnią komunikatu pokazuje prosty komunikat, że przed wydrukiem trzeba potwierdzić wskazane odchylenia prawne;
- po zaznaczeniu wymaganych LAW koordynator ponawia `Wygeneruj PDF`, a frontend odsyła zaznaczone fingerprinty;
- non-LAW nie muszą być zaznaczone dla wydruku.

Istniejące checkboxy LAW muszą być dostępne na potrzeby jednorazowego eksportu także wtedy, gdy drukowana wersja jest `FINAL`. To nie zmienia statusu, nie otwiera finalizacji i nie zapisuje trwałego acknowledgement.

Nie dodawać drugiego panelu ani modala.

## 8. Stary preview PDF

Jeżeli eksport zostaje zablokowany z powodu świeżego LAW albo bieżący grafik/miesiąc/obiekt zmienia się przed kolejnym eksportem, UI nie może pozostawiać starego `previewBlob` jako aktualnie oferowanego dokumentu.

`Export` ma użyć jednego mechanicznego helpera czyszczenia preview i wywoływać go co najmniej przy:
- wyniku blokującym eksport;
- zmianie `siteId`;
- zmianie `workingMonth`;
- zmianie bieżącego `current version_id` przekazanego z `MonthlyPlanning`.

To jest mechaniczna ochrona przed pobraniem starego PDF po zmianie stanu, nie nowy lifecycle.

## 9. Acceptance

P1. Legalny `WORKING` bez LAW nadal generuje PDF.

P2. Grafik z non-LAW, ale bez LAW, nadal generuje PDF bez dodatkowego potwierdzenia.

P3. Świeże niepotwierdzone LAW blokuje PDF i zwraca minimalną listę świeżych LAW z fingerprintami oraz czytelny komunikat do istniejącej powierzchni UI.

P4. Bezpośredni POST bez wymaganych fingerprintów export-ack również jest blokowany.

P5. Pokazane w istniejącej liście świeże LAW można zaznaczyć; ponowienie requestu z fingerprintami wszystkich aktualnych LAW pozwala wygenerować PDF.

P6. Potwierdzenie eksportowe nie zmienia persisted `Deviation.acknowledged`, statusu wersji, lifecycle ani historii decyzji.

P7. Kolejna próba eksportu tego samego grafiku z tym samym LAW znów wymaga potwierdzenia.

P8. Zmiana faktu naruszenia przy tej samej regule/indexie/targetcie nie może odziedziczyć starego potwierdzenia; fingerprint z fresh `ViolationDetail`/Assignment/Demand musi się różnić.

P9. Zmiana current version pomiędzy walidacją a renderem nie może wygenerować PDF dla niesprawdzonego stanu.

P10. Po zablokowanym eksporcie lub zmianie site/month/current UI nie oferuje starego preview jako aktualnego PDF.

P11. `FINAL` z LAW może użyć tej samej istniejącej listy/checkboxów do jednorazowego export-ack bez ponownej finalizacji i bez zmiany statusu.

P12. Brak nowego `DECISION_REQUIRED`, nowej tabeli, nowego modala i nowego validatora.

## 10. Literalny TASK_SCOPE

Production — oczekiwany minimalny zakres:
- `rota/application/schedule_export.py` — świeży LAW guard związany z dokładnie eksportowaną wersją oraz check current przed zwrotem;
- istniejący application-layer owner świeżej walidacji — wydzielić/reuse wspólny helper z obecnego przebiegu `lifecycle_ops._fresh_deviations` tak, aby lifecycle i export korzystały z jednego assembler+validator path; bez drugiego validatora;
- `api/routers/export.py` — minimalny request/response dla jednorazowych LAW fingerprintów oraz blokującej listy świeżych LAW; bez nowego endpointu/workflow;
- `frontend/src/screens/Export.tsx` — przekazanie bieżących zaznaczonych LAW fingerprintów i unieważnienie starego preview;
- `frontend/src/screens/MonthlyPlanning.tsx` — wyłącznie mechaniczne reuse istniejącej listy/zaznaczeń LAW, przyjęcie świeżej listy z export result i umożliwienie zaznaczeń także dla FINAL na potrzeby eksportu; bez nowego panelu;
- `frontend/src/api/client.ts` — mechaniczne pola request/response.

Tests:
- nowy wąski `tests/test_export_unacknowledged_law.py`;
- istniejący test/export E2E rozszerzony tylko o P1–P11;
- wymagany przypadek direct POST;
- wymagany przypadek tej samej reguły/indexu/targetu, ale zmienionego strukturalnego faktu -> stary fingerprint nie przechodzi;
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

## 11. Finalny preimplementation re-check Codexa

Nie otwierać ponownie punktów R1, które już mają TAK. Sprawdzić tylko:
1. czy wspólny fresh-validation helper może zastąpić prywatny przebieg lifecycle bez duplikacji validatora i bez zmiany semantyki lifecycle;
2. czy blokujący export response może przenieść minimalne świeże LAW + fingerprinty do istniejącej listy `Odchylenia`, a retry może odesłać zaznaczone fingerprinty bez nowego panelu/modelu;
3. czy ta sama istniejąca lista może udostępnić checkbox LAW dla `FINAL` wyłącznie na potrzeby jednorazowego export-ack, bez ponownej finalizacji;
4. czy poprawiony literalny scope (`frontend/src/screens/Export.tsx`, helper, request/response) jest kompletny;
5. czy nadal nie jest potrzebny REPLAN/restore/finalize redesign ani osobny system decyzji.

Jeżeli 1–5 = TAK: PASS exact brief SHA i zwolnienie IMPLEMENTATION HOLD. Jeżeli NIE: wskazać wyłącznie konkretną brakującą ścieżkę/pole, bez poszerzania do lifecycle/REPLAN/restore.
