# ROTA-T010-C — szkolenie i READY_FOR_PRIMARY

STATUS: DRAFT FOR CODEX AUDIT

`S` pozostaje ręcznym TRAINEE w konkretnym grafiku przez istniejącą manualną korektę. Nie ma ustawienia „Szkolenie” w konfiguracji pracownika i solver nie tworzy szkolenia z własnej inicjatywy.

`readiness_state` i `readiness_source` pozostają informacją w `SiteMembership` i nie uczestniczą w eligibility.

Usunąć z `rota/application/training.py` automatyczną zmianę na `READY_FOR_PRIMARY` po osiągnięciu liczby REALIZED TRAINEE. REALIZED TRAINEE nie może modyfikować membership/readiness. Jeżeli `mark_training_realized()` zostaje dla zgodności z istniejącym API, ma tylko korzystać z manualnej korekty bez zmiany membership.

Liczbę szkoleń wolno później pokazywać jako fakt; nie wolno wyprowadzać z niej decyzji o pracowniku.

Testy: REALIZED TRAINEE nie zmienia readiness; `NOT_READY` i `READY_FOR_PRIMARY` mają identyczne eligibility przy tych samych pozostałych danych; TRAINEE nadal działa przez istniejące wersjonowanie grafiku; regresja poza usuwaną automatyką pozostaje PASS.

FAIL za nowy automatyczny mechanizm dopuszczania lub odsuwania pracownika na podstawie szkoleń albo historii.