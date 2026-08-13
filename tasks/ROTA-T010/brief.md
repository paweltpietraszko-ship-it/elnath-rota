# ROTA-T010 — fundament konfiguracji dla przyszłego Panelu Sterowania

STATUS: DRAFT FOR CODEX AUDIT
OWNER BASIS: `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md`
BASELINE: main `51b71725186fa30be23219e94aa135bb69bc5bce`

## 1. Cel

T010 przygotowuje backend/application dla pierwszej konfiguracji obiektu i późniejszej edycji tych samych danych. Docelowe okno UI będzie nazywać się **Panel Sterowania**, ale powstaje dopiero w T012.

T010 NIE tworzy UI, parsera, DSL, uniwersalnego edytora reguł, osobnego onboardingu ani drugiego źródła prawdy.

## 2. Zasada nadrzędna: reuse first

Jeżeli zachowanie lub trwały fakt już istnieje, T010 ma go wykorzystać. Panel Sterowania nie dostaje własnej logiki biznesowej.

W szczególności T010 wykorzystuje istniejące:

- `Coordinator`, `SiteProfile`, `Site`, `CoordinatorSiteAssociation` i ich repository;
- `Employee`, `SiteMembership` oraz `membership.enabled`;
- `AvailabilityRecord`;
- `SiteRuleVersion` i miesięczną aplikowalność reguł;
- T009 application layer, w tym zapis pracownika, membership, profilu i target_hours;
- `record_structured_rule_decision()`;
- `apply_manual_correction()` i wersjonowanie ScheduleVersion;
- istniejące liczenie WorkBalance.

**Skopiowanie istniejącej logiki lub stworzenie równoległego stanu konfiguracji = FAIL architektoniczny, nie uwaga do późniejszego refaktoru.**

## 3. Podział T010

T010 jest jednym zakresem produktowym, ale implementacyjnie dzieli się na cztery małe części. Każda część ma osobny kontrakt i osobny audyt Codexa przed implementacją CC:

- **T010-A — pierwsza konfiguracja i bieżąca obsada**: `part_a_bootstrap_roster.md`;
- **T010-B — matryca dostępności pracownika**: `part_b_availability.md`;
- **T010-C — szkolenie i informacyjny READY_FOR_PRIMARY**: `part_c_training_readiness.md`;
- **T010-D — NN jako fakt niewykonanej zmiany**: `part_d_nn.md`.

Nie wolno implementować wszystkich czterech części jako jednego dużego commita.

## 4. Wspólne zasady produktu

1. Program nie ocenia, nie dopuszcza i nie odsuwa pracownika z własnej inicjatywy. Wykonuje jawne decyzje koordynatora.
2. Dostępność ustawiona przez koordynatora jest HARD dla solvera.
3. Wszystkie ptaszki mają jedno znaczenie: `✓` = solver może korzystać, `☐` = solver nie może korzystać w obowiązującym zakresie.
4. Dla nowego zwykłego pracownika Ogólna dostępność, Dniówka, Nocka oraz Pon–Nd są domyślnie `✓`. Istniejące `day_only=true` jest bazowym źródłem Nocka `☐`.
5. Okres `od–do` jest włącznie z obiema datami. Po `do` automatycznie wraca stan bazowy; nie zapisuje się przyszłej operacji „przywróć”.
6. Szkolenie `S` jest ręczną decyzją w konkretnym grafiku. Solver nie decyduje, czy ktoś potrzebuje szkolenia.
7. `READY_FOR_PRIMARY` pozostaje informacją i nie uczestniczy w eligibility.
8. `NN` jest faktem o konkretnej niewykonanej zmianie po planowaniu, a nie regułą dostępności pracownika.
9. TARGET-01 pozostaje bez zmian: target_hours jest SOFT i nie tworzy pracy ani nie pozwala naruszać HARD.

## 5. Granice

T010 nie implementuje:

- Reacta/Tauri ani innego UI;
- osobnego kreatora pierwszego uruchomienia;
- trwałego `onboarding_state`, numeru kroku ani szkicu konfiguracji;
- parsera, LLM lub swobodnego tekstu jako źródła reguł;
- nowego workflow/command bus/DI framework;
- automatycznej oceny pracownika;
- automatycznego REPLAN po zmianie konfiguracji;
- logiki kadrowych konsekwencji NN.

T012 ma korzystać wyłącznie z operacji aplikacyjnych przygotowanych lub już istniejących po T010. Nie może zapisywać bezpośrednio do repository.

## 6. Warunek zakończenia T010

T010 jest gotowe dopiero po PASS Codexa dla A, B, C i D oraz po pełnej regresji istniejącego systemu, z wyjątkiem testów wymagających jawnie uchylonej automatycznej promocji READY_FOR_PRIMARY.
