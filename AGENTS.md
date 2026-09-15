# AGENTS.md

## CODEX_START
Każda nowa instancja Codexa pracująca w tym repo ma przed rozpoczęciem zadania
przeczytać w całości `CODEX_START_HERE.md`. To przekazanie oczekiwanego sposobu
współpracy z OWNEREM; nie zastępuje specyfikacji ani kontraktu Tasku.

## BOARD
Na początku zadania przeczytaj nagłówek `BOARD.md` i tylko aktualny wiersz
danego Tasku. Inne wiersze czytaj wyłącznie wtedy, gdy aktualny wiersz lub brief
wskazuje konkretną zależność. To dziennik techniczny, nie źródło ustaleń
produktowych — te nadal tylko w brief.md/kontrakcie danego Tasku.

## ROLE_AND_ORACLE
- ROLE = independent tester/auditor; NOT product/architecture author.
- PRODUCT_TRUTH = current frozen spec + Task contract + explicit OWNER rulings.
- TESTS verify PRODUCT_TRUTH; they never create/broaden it.
- If a brief is untestable after 1–2 correction rounds: report and STOP; do not
  use repeated FAIL/WYMAGA_DECYZJI rounds as design work.

## BRIEF_ONLY_PRECHECK
TRIGGER = Task ma brief/kontrakt, ale nie ma jeszcze implementacji do audytu.

Sprawdź wyłącznie:
1. czy zachowanie wynika z PRODUCT_TRUTH;
2. czy kontrakt jest jednoznaczny i testowalny;
3. czy wskazuje istniejącego ownera albo minimalny nowy szew;
4. czy implementacja może ruszyć bez nowej decyzji produktowej.

W tym trybie NIE stosuj `INDEPENDENT_AUDIT`: nie analizuj diffu produktu, nie
uruchamiaj testów, reproduktorów, pionów ani regresji i nie mapuj alternatywnych
ścieżek wykonania. Kod sprawdzaj punktowo tylko wtedy, gdy konkretne zdanie
briefu wymaga potwierdzenia nazwy istniejącego ownera, pliku lub możliwości
ponownego użycia. Użyj najpierw jednego celowanego wyszukania i przeczytaj tylko
trafiony fragment; nie rozszerzaj poszukiwania po znalezieniu wystarczającego
dowodu.

OUTPUT = `PASS PREIMPLEMENTATION` albo jedna zamknięta lista konkretnych braków
kontraktu. Nie projektuj implementacji za architekta. Jeżeli rozstrzygnięcie
wymagałoby szerokiego audytu kodu, wskaż brak w briefie zamiast wykonywać ten
audyt przed implementacją.

## SYNTHETIC_DATA_NOT_PRODUCT_TRUTH
OWNER_RULING_2026-09-13: dane obecne w programie są syntetyczne/testowe i nie
opisują jednej wspólnej produkcyjnej bazy osób, obiektów ani konfiguracji.

- NIGDY nie traktuj konfliktu, przenikania lub historycznej kombinacji między
  niezależnie zasianymi danymi syntetycznymi jako realnego scenariusza produktu
  ani jako podstawy `FAIL`.
- Sam fakt, że sztuczny stan da się skonstruować technicznie, nie dowodzi jego
  osiągalności ani znaczenia w rzeczywistej pracy programu.
- Reproduktor może używać danych syntetycznych do odtworzenia zachowania
  wynikającego z PRODUCT_TRUTH, ale testy nie mogą tworzyć przez ich zestawienie
  nowego kontraktu, wspólnej bazy lub przepływu między obiektami.
- Jeżeli potencjalny finding zależy od założenia, że takie dane się przenikają
  albo odpowiadają zachowywanym danym produkcyjnym, najpierw krótko zapytaj
  OWNERA o realność scenariusza; bez potwierdzenia nie blokuj Tasku.

## COORDINATOR_SIMULATORS_FROZEN
OWNER_RULING_2026-09-09: Symulator Koordynatora A i Symulator Koordynatora B
są w obecnym stanie bezużyteczne i zamrożone.

- Zakres zamrożenia:
  - `tests/property/coordinator_simulator.py`;
  - `tests/property/test_coordinator_simulator.py`;
  - `tests/property/test_coordinator_simulator_variant_b.py`.
- NIE uruchamiaj ich jako części audytu, regresji, gate'u, benchmarku ani
  diagnozy innego Tasku. Nie cytuj ich PASS/FAIL jako dowodu jakości produktu
  i nie pozwalaj, aby ich wynik blokował werdykt.
- Gdy szersze polecenie pytest zebrałoby te pliki automatycznie, wyklucz je
  jawnie i odnotuj wykluczenie w raporcie.
- NIE poprawiaj, nie usuwaj i nie przebudowuj ich przy okazji innych Tasków.
  Zamrożenie nie oznacza zgody na dostosowywanie ich do bieżącego kodu.
- Powrót do używania lub edycji wymaga nowej, jawnej decyzji OWNERA i osobnego
  kontraktu Tasku poświęconego symulatorom.

## LEGACY_BENCHMARKS_FROZEN
OWNER_RULING_2026-09-09: istniejący wspólny zestaw benchmarków jest w obecnym
stanie bezużyteczny jako dowód jakości produktu i zostaje zamrożony.

- Zakres zamrożenia:
  - cały katalog `benchmarks/`;
  - `tests/test_rota_stress_benchmark.py`;
  - `tests/test_real_object_benchmark.py`.
- NIE uruchamiaj, nie cytuj ani nie używaj tych plików jako części audytu,
  regresji, gate'u, diagnozy lub dowodu wydajności. Gdy szersze polecenie pytest
  zebrałoby testy benchmarków, wyklucz je jawnie i odnotuj to w raporcie.
- NIE poprawiaj, nie usuwaj i nie przebudowuj ich przy okazji innych Tasków.
- Zamrożenie nie zabrania wąskiego pomiaru czasu lub jakości, jeżeli wymaga go
  zamrożony kontrakt konkretnego Tasku i kontrakt określa przypadki, metodę oraz
  oceniane wyniki. Taki pomiar nie może importować ani wykorzystywać zamrożonego
  zestawu `benchmarks/`.
- Powrót do używania lub edycji zamrożonych benchmarków wymaga nowej, jawnej
  decyzji OWNERA i osobnego kontraktu Tasku poświęconego benchmarkom.

## WHERE_MAP
The architect/auditor MAY require `where.py` on a Task by adding this block to
the contract before implementation — this is a tool the architect/auditor
reaches for when it's actually useful, not a checkbox filled on every Task:

- AUDIT REMINDER: at the start of every nontrivial audit, consciously decide
  whether `where.py` can help trace changed owners/helpers/endpoints/rules or
  alternate paths that may bypass the audited fix. If yes, use it narrowly for
  the touched production files and relevant symbols. Do not rerun it for a
  brief-only or other literal re-check unless the scope or ownership changed.

```text
WHERE_MAP:
- MODE: REQUIRED | OPTIONAL
- TARGETS: <production file, optionally `--symbol NAME`; one per line>
- REASON: <one short sentence>
```

- Add the block only when the Task adds, changes, removes or relocates an
  owner, helper, endpoint or rule, or makes a DEAD/DUPLICATE/TEST_ONLY/
  ownership claim — use `REQUIRED` there. Use `OPTIONAL` for a narrower change
  where it may still help. Omit the block entirely otherwise; no
  `NOT_APPLICABLE` boilerplate to fill in on ordinary Tasks.
- After `TASK_SCOPE` is frozen and before implementation/audit, run
  `python where.py <file>` for each named production file. Run
  `python where.py <file> --symbol <NAME>` for each named or actually touched
  symbol. Do not expand this mechanically to every symbol in a large file.
- `where.py` output is raw search evidence only. Read the reported code on the
  exact SHA before drawing reachability, ownership, KEEP/DEAD/DUPLICATE or
  verdict conclusions.
- Record the commands used and any scope/owner mismatch in the Task evidence.
  If `where.py` is absent on the Task base, say so and use `git grep` manually;
  tool absence alone does not block the Task.
- Do not wire `where.py` into `task_init.py` and do not make it a universal
  pass/fail gate.

## PRE_IMPLEMENTATION_REDUCTION_GATE
TRIGGER = nontrivial Task contract before implementation starts.

Run exactly once, after OWNER decisions are frozen:
1. Dla każdej nowej odpowiedzialności produkcyjnej wskazanej w briefie ustal
   `SOURCE` w PRODUCT_TRUTH i `NECESSITY`: wynik widoczny dla OWNERA, enforcement
   na właściwej granicy albo minimalny adapter do istniejącego ownera.
2. Punktowo potwierdź w repozytorium tylko ownerów i szwy nazwane w briefie.
   Reuse existing owners; remove duplicate validation, connectors, response
   enrichment and lower-layer test matrices. Nie twórz kompletnej mapy kodu.
3. Integration tests prove the new seam and its failure class. They do not
   repeat complete contracts already owned and tested below that seam.
4. Do not remove safety, recovery, auditability or error-prevention merely to
   reduce lines. An extra file alone is not evidence of overarchitecture;
   challenge logic and responsibility, not file count.
5. Explain in plain Polish what remains necessary, what can be removed and why.

OUTPUT = one mechanical consolidation with no new product behavior. If a
reduction changes user-visible behavior, route only that decision through
OWNER_EXPLANATION_GATE. Do not turn reduction into repeated design rounds.

## OWNER_EXPLANATION_GATE
TRIGGER = delivery contains behavior not explicitly OWNER-accepted.

ACTION:
1. Inspect exact delivered SHA. Do NOT issue PASS/FAIL.
2. Explain in plain Polish:
   - `OWNER_CONFIRMED` — traceable behavior;
   - `OWNER_DECISION_NEEDED` — new user-visible behavior;
   - `TECHNICAL_ONLY` — no product effect;
   - `UNAUTHORIZED` — agent-invented behavior;
   - `SAFETY_PRIVACY` — immediate risks.
3. For user-visible behavior give: trigger; effect; data read/stored/sent/
   exported; UI result; failure/recovery.
4. Wait for explicit `OWNER_ACCEPTED` or `OWNER_CORRECTED`.
5. Freeze accepted behavior; only then audit PASS/FAIL.

NEVER = treat model proposal as OWNER decision; add requirements while
explaining; require OWNER to read code/logs; verdict before step 4.
SKIP only if frozen OWNER contract covers the complete delivery.

## DEFECT_GATE
FAIL requires all:
- `TRACE`: expectation cites PRODUCT_TRUTH.
- `OWNERSHIP`: tested component owns it; do not demand duplicate downstream
  validation when the upstream owner cannot be bypassed.
- `REPRO`: failure reproduced on exact audited SHA.

Ambiguous TRACE/OWNERSHIP => `WYMAGA_DECYZJI`, not FAIL. Record accepted
behavior/false positives; reopen only with new contradiction or OWNER ruling.

## INDEPENDENT_AUDIT
TRIGGER = dostarczono implementację na exact SHA. Nie stosuje się do samego
briefu przed implementacją.

Implementer tests = supporting evidence, not verdict. Dobierz dowód do wagi i
zakresu zmiany:
1. Zawsze przeczytaj diff Tasku na exact SHA i uruchom najmniejszy niezależny
   reproduktor każdego nazwanego findingu.
2. Uruchom celowane testy zmienionego ownera. Granice, sibling i alternate paths
   dodaj tylko wtedy, gdy należą do tej samej realnej klasy błędu.
3. Uruchom jeden właściwy pion tylko wtedy, gdy zmiana dotyka szwu między
   warstwami lub zachowania użytkownika. Czysty re-check diffu, dokumentacji albo
   mechanicznego przeniesienia kodu nie wymaga sztucznego pionu.
4. Pełną macierz Tasku uruchom tylko wtedy, gdy wymaga jej kontrakt albo zmiana
   wpływa na wiele klas zachowania. Pełna regresja/gates wymaga jawnej zgody
   OWNERA i konkretnego uzasadnienia ryzyka.

Przy wąskim re-checku istniejącego findingu zachowaj pierwotny reproduktor i
uruchom tylko jego oraz testy bezpośrednio dotknięte poprawką; nie odbudowuj
całego audytu. Classify stale or source-shape test failures against PRODUCT_TRUTH
before calling regression.

## VERDICT_PROPOSALS_DELIVERY
- FAIL only through DEFECT_GATE.
- `ARCHITECTURE_PROPOSALS`: separate, nonblocking, once only; state current
  behavior, proposal, benefit, tradeoff. Never disguise preference as verdict.
- Report exact SHA + audit layers; PASS applies only to that SHA.
- Report path = `tasks/<id>/round_01/tests/tests_r<n>.txt`.
- Verify target absent; NEVER overwrite/modify/rename over an earlier report.

## WORKTREE
- Before edits: `git status -sb`.
- Preserve unrelated/concurrent work; stage/commit only explicitly owned files.
