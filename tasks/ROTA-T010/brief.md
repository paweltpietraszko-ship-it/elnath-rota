# ROTA-T010 — fundament konfiguracji dla Panelu Sterowania

STATUS: DRAFT FOR CODEX AUDIT
OWNER BASIS: `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md`
BASELINE: main `51b71725186fa30be23219e94aa135bb69bc5bce`

T010 przygotowuje application/backend dla pierwszej konfiguracji i późniejszej edycji tych samych danych. Bez UI, parsera, DSL, osobnego onboardingu i drugiego źródła prawdy.

**Reuse istniejącej logiki jest obowiązkowy. Duplikacja = FAIL architektoniczny.**

## Części

Implementacyjne i osobno audytowane:
- **A** — bootstrap, gotowość konkretnego miesiąca i bieżąca obsada: `part_a_bootstrap_roster.md`;
- **B** — jedna matryca dostępności: `part_b_availability.md`;
- **D** — NN konkretnej niewykonanej zmiany: `part_d_nn.md`.

**C nie jest implementacją.** `part_c_training_readiness.md` to tylko gate regresyjny: readiness nie może wpływać na eligibility. T010 nie usuwa ani nie rozbudowuje istniejącej automatyki samej etykiety.

Czasowe N dla `day_only=true` podlega `arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md`.

## Wspólne zasady

- `✓` zawsze znaczy „solver może”, `☐` „solver nie może” w obowiązującym okresie;
- zwykły nowy pracownik ma bazowo ✓ dla Ogólnej, D, N i Pon–Nd; `day_only=true` daje bazowo Nocka ☐;
- `od–do` jest włączne i po `do` wraca stan bazowy;
- dostępność koordynatora jest HARD;
- `S` pozostaje ręczne;
- `NN` jest wyłącznie faktem wcześniej zaplanowanej, niewykonanej zmiany;
- TARGET-01 pozostaje bez zmian i jest SOFT.

## Zakazy

Brak UI, trwałego onboarding_state, parsera/LLM, uniwersalnego edytora reguł, workflow/command bus/DI, automatycznego REPLAN i logiki kadrowej NN. T012 nie zapisuje bezpośrednio do repository.

Nie implementować A+B+D jednym dużym commitem.

## READY_FOR_IMPLEMENTATION po R1

Codex ma potwierdzić:
1. A rozdziela stałą kompletność obiektu od gotowości wskazanego miesiąca i sprawdza pełny CalendarDay;
2. B ma tylko wąski wyjątek od `DAY_ONLY-01` oraz append-only edycję/cofnięcie ograniczeń;
3. C jest wyłącznie regresją;
4. D ma jedno miejsce zapisu NN, `CANCELLED`, jednoznaczne planned/realized i zwykłą walidację coverage;
5. Aneks ma jedną semantykę NN.

Po PASS CC implementuje kolejno A, B, D.