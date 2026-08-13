# ROTA-T010-C — gate regresyjny

STATUS: DRAFT FOR CODEX AUDIT
NOWA IMPLEMENTACJA: NIE

T010 nie zmienia istniejącej obsługi szkolenia ani informacyjnej etykiety readiness.

Sprawdzić tylko:
- `S` pozostaje ręcznym TRAINEE;
- solver nie tworzy szkolenia sam;
- `NOT_READY` i `READY_FOR_PRIMARY` mają identyczne eligibility przy tych samych pozostałych danych;
- readiness nie blokuje ani nie dopuszcza do grafiku.

Nie usuwać i nie rozbudowywać automatycznego przestawiania samej etykiety w T010.

FAIL za nową logikę oceny pracownika opartą o readiness lub liczbę szkoleń.