# ROTA-T044 — pomiar profilu Hypothesis (przed zamrożeniem liczb)

Zgodnie z ARCHITECT_FINAL_PREIMPLEMENTATION_GATE.md sekcja 3.4 / brief.md
1.3: implementer mierzy, nie zgaduje `max_examples`/`stateful_step_count`.

## Komenda

```
python -c "
import time, random
from api.deps import get_conn
from api.main import app
from rota.persistence.db import connect
from fastapi.testclient import TestClient
from tests.property import coordinator_simulator as sim

def run_one(seed):
    connection = connect(':memory:')
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        spec = sim.random_object_spec_b(seed)
        sim.assert_headcount_b(spec)
        site_id = sim.build_object_b(client, spec)
        rng = random.Random(seed*104729+1)
        draws = sim.initial_absences_b(spec, rng)
        sim.apply_absences_b(client, site_id, spec, draws)
        result = sim.run_plan(client, site_id, spec.month)
        final = result
        if result['status']=='DECISION_REQUIRED' and result.get('decision_payload'):
            loop = sim.run_with_external_loop_b(client, site_id, spec.month, spec, result)
            final = loop['final_result']
        if final['status']=='FEASIBLE':
            sim.select_first_candidate(client, site_id, spec.month, final)
            sim.run_replan(client, site_id, spec.month)
        return spec.employee_count, final['status']
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()

t0=time.time()
results=[run_one(seed) for seed in range(10)]
t1=time.time()
print('10 examples took', t1-t0, 'seconds')
print('avg per example', (t1-t0)/10)
print(results)
"
```

Exact SHA (worktree HEAD w chwili pomiaru): 972d32778c41041b84e78ee7805a7d061799ae7a
(brief/Task frozen contract; kod Wariantu B jeszcze w trakcie tej implementacji).

## Wynik

- 10 pełnych przebiegów (build_object_b + initial_absences_b + PLAN +
  ewentualna pętla EXTERNAL + select-candidate + REPLAN) = **98.93 s**.
- **~9.89 s / przebieg** (jeden przebieg odpowiada z grubsza jednemu
  przykładowi Hypothesis z 4 krokami stateful: PLAN, ewentualny EXTERNAL,
  select, REPLAN).
- Wszystkie 10 przebiegów: FEASIBLE (obsada 3-6 osób, żaden EXTERNAL
  potrzebny w tej próbce).

## Wybrane liczby

**Profil domyślny** (zwykły `pytest`): `max_examples=8`,
`stateful_step_count=4` → szacowany czas ≈ 8 × 9.89 s ≈ **79 s**, rząd
pojedynczych dziesiątek sekund do niskiej minuty, wyraźnie poniżej ~750 s
zmierzonego wcześniej pełnego portfela Wariantu A (`tests_r1.txt:92`).

**Profil eksploracyjny** (`ROTA_SIM_VARIANT_B_FULL=1`): `max_examples=30`,
`stateful_step_count=8` → szacowany rząd wielkości: 30 × (2×9.89s) ≈ 594 s,
zauważalnie większy niż domyślny, ale wciąż jednorazowy ręczny przebieg, nie
część zwykłego `pytest`.

`deadline=None`, `database=None`, `derandomize=False` — zamrożone wprost w
kontrakcie, nie wynikają z tego pomiaru.
