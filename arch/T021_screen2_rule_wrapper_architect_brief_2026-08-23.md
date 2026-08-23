# Brief dla architekta — brakujące funkcje pośredniczące nad regułami pracownika

## Kontekst

T021 (front) buduje ekran per-pracownik (Panel sterowania → Obsada →
[Nazwisko]) z macierzą dostępności: Ogólna dostępność, Dniówka, Nocka,
24h, 7× dzień tygodnia. Zamrożona decyzja właściciela:
`arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md`, sekcja 5.

T021 (`tasks/ROTA-T021/brief.md` §6) NIE MOŻE modyfikować `rota/**` —
zamrożona zasada tego zadania. Ten dokument jest wyłącznie faktograficzny
(zebrane fakty z kodu), NIE proponuje kształtu nowych funkcji — to
decyzja architekta.

## Co już działa dziś (gotowe funkcje, T021 może z nich korzystać wprost)

- **Ogólna dostępność** — `durable_inputs.append_availability(conn, *,
  coordinator_id, site_id, availability_id, employee_id, kind:
  AvailabilityKind, start_date, end_date, active, note=None,
  responds_to_decision_required_id=None)`. Tej samej funkcji używa
  "Zgłoś nieobecność" (wszystkie 5 wartości `AvailabilityKind`).
- **24h** (`can_work_24h`) — zwykły trwały bool na `SiteMembership`,
  bez zakresu dat, przez `durable_inputs.update_membership(conn, *,
  coordinator_id, site_id, membership: SiteMembership, note=None,
  responds_to_decision_required_id=None)`.
- **Godziny docelowe/miesiąc** — `durable_inputs.set_target_hours(conn,
  *, coordinator_id, site_id, employee_id, month, target_hours, note=None,
  responds_to_decision_required_id=None)`.
- **day_only flaga** — `durable_inputs.update_employee(conn, *,
  coordinator_id, site_id, employee: Employee, note=None, ...)`.

## Czego brakuje

**Dniówka, Nocka, 7× dzień tygodnia** (3 z 4 grup kolumn macierzy) idą
przez ogólny mechanizm `rule_decisions.record_structured_rule_decision(
conn, *, coordinator_id, site_id, rule_id: str, statement: str,
effective_from: date, rel: Optional[str] = None, rule_content:
Optional[NewRuleContent] = None, recorded_at=None, note=None,
responds_to_decision_required_id=None) -> DecisionRecord`.

Zweryfikowane w kodzie (`rota/planning/site_rules.py:90-118`) dokładne
kształty `structured_parameters` dla właściwych `rule_kind`:

- `EMPLOYEE_ALLOWED_SHIFT_KINDS`: `{"employee_id": str,
  "allowed_shift_kinds": list[str]}` (wartości `ShiftKind`) — pokrywa
  Dniówka/Nocka.
- `EMPLOYEE_ALLOWED_WEEKDAYS`: `{"employee_id": str, "allowed_weekdays":
  list[int]}` (ISO weekday 1-7) — pokrywa kolumny dni tygodnia.
- `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`: `{"employee_id": str,
  "weekdays": list[int], "forbidden_shift_kinds": list[str]}`.
- `EMPLOYEE_DAY_ONLY_N_EXCEPTION`: `{"employee_id": str}` — czasowy
  wyjątek Nocki dla `day_only=true` pracownika
  (`arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md`).

Rzeczywisty przykład zapisu (z `tests/test_t010_day_only_n_exception.py:56-65`):
```python
record_decision(
    conn, site_id=SITE_ID, rule_id="R-DAYONLY-EXC", statement="test",
    coordinator_id="COORD-1", recorded_at=..., effective_from=...,
    rel=None,
    rule_content=NewRuleContent(
        category=RuleCategory.CONFIRMED_EXCEPTION, rule_kind=EMPLOYEE_DAY_ONLY_N_EXCEPTION,
        structured_parameters={"employee_id": EMP}, enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED, effective_to=...,
        description=None, source=None, reason=None,
    ),
)
```
(`record_decision` to persistence-layer funkcja pod
`record_structured_rule_decision`, użyta tu bezpośrednio w teście — samo
`record_structured_rule_decision` dodaje kontekst koordynatora + wpis do
`site_memory`.)

**Nie znalazłem** w istniejącym kodzie żadnej konwencji "jak wybrać/
wygenerować `rule_id` dla pary (pracownik, rodzaj reguły)" ani jak
odznaczenie w UI (jeden checkbox, jeden zakres dat) ma się przełożyć na
`rel`/łańcuch poprzednika (`predecessor_chain`) przy kolejnej zmianie tej
samej komórki. To jest realna decyzja projektowa, nie do zgadnięcia przez
implementatora.

## Pytania do rozstrzygnięcia przez architekta (nie przeze mnie)

1. Jaki kształt powinny mieć wygodne funkcje pośredniczące (np.
   `set_employee_allowed_shift_kinds`, `set_employee_allowed_weekdays`,
   `set_employee_forbidden_shift_kinds_on_weekdays` — nazwy przykładowe,
   nie propozycja) — jedna funkcja per rodzaj reguły, czy jedna wspólna
   przyjmująca `rule_kind`?
2. Jak wyznaczyć/wygenerować stabilny `rule_id` per (employee_id,
   site_id, rule_kind), żeby kolejne odznaczenia tej samej komórki
   tworzyły poprawny łańcuch decyzji (`rel`), a nie osobne, niepowiązane
   reguły?
3. Czy `statement` (opis w dzienniku decyzji) ma być generowany
   automatycznie z parametrów (np. "Dniówka: zablokowana 20–31.08"), czy
   koordynator go wpisuje?
4. `effective_to` — czy UI ma pozwalać tylko na zakres z automatycznym
   powrotem "po dacie do" (zgodnie z zamrożoną zasadą sekcja 5), czy też
   otwarty koniec?

## Zakres

Wyłącznie `rota/application/rule_decisions.py` (lub nowy moduł, wg
uznania architekta) + testy. Nie dotyczy frontu ani API — to osobne
zadanie od T021, z własnym audytem, zanim T021 zacznie budować kolumny
Dniówka/Nocka/dni tygodnia.
