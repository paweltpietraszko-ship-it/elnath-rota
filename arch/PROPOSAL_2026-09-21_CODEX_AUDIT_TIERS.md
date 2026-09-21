# PROPOSAL 2026-09-21 — poziomy audytu Codexa (LIGHT/STANDARD/DEEP) i odchudzenie kosztu sesji

STATUS: szkic do decyzji ARCHITEKTA + OWNERA. CC niczego nie zmienia w `AGENTS.md`,
`CODEX_START_HERE.md` ani w konfiguracji Codexa — to proces audytu (własność
architekta/ownera). Tekst poniżej jest gotowy do wklejenia po akceptacji.

Powód (OWNER, 2026-09-21): Codex zużywa limit, bo nie ma podziału na lekki audyt
prostych tematów i poważny audyt trudnych. Cel: ten sam poziom wykrywalności błędów
przy mniejszym zużyciu — bez zdejmowania bramek jakościowych.

## 1. Diagnoza (stan obecnych plików)

- Już działa: dowody „do wagi zmiany" (`INDEPENDENT_AUDIT` pkt 1–4), precheck briefu
  bez testów, wąski re-check poprawki, zakaz pełnej suity bez zgody OWNERA,
  `DEFECT_GATE` (TRACE+OWNERSHIP+REPRO) tnący fałszywe FAIL-e.
- Brak: poziom audytu nie jest wybierany z góry. „Dobierz dowód do wagi" zostawia
  ocenę wykonawcy, a bramki (`PRE_IMPLEMENTATION_REDUCTION_GATE`,
  `OWNER_EXPLANATION_GATE`, `WHERE_MAP`, pion, macierz) każda uznaje samą siebie za
  właściwą dla „nietrywialnego" zadania.
- Koszt stały: `AGENTS.md` 11 KB + `CODEX_START_HERE.md` 7 KB czytane przy każdej nowej
  instancji; precheck, `DEFECT_GATE` i limity testów są w obu plikach; ok. 40 linii
  to tablice nagrobne (`COORDINATOR_SIMULATORS_REMOVED`, `LEGACY_BENCHMARKS_REMOVED`),
  bez znaczenia dla audytu. Limit Codexa 32 KiB nie jest przekroczony (nic się nie
  ucina) — to koszt tokenów, nie poprawności.
- Konfiguracja Codexa OWNERA (`~/.codex/config.toml`): model `gpt-5.6-terra`,
  `model_reasoning_effort = "medium"` globalnie, brak profili; włączone globalnie
  wtyczki niezwiązane z audytem kodu (documents, pdf, spreadsheets, presentations,
  template-creator, visualize, computer-use, unified-computer-use) oraz serwery MCP
  `node_repl` i `maestro`. Każde narzędzie dokłada opis schematu do każdej tury.

## 2. Proponowana sekcja do `AGENTS.md` (gotowy tekst)

```text
## AUDIT_TIER
Architekt wpisuje w wierszu BOARD / w briefie: AUDIT_TIER: LIGHT | STANDARD | DEEP.
Brak wpisu = STANDARD. Codex może tylko PODNIEŚĆ poziom i musi wskazać konkretny
powód (plik, reguła, klasa błędu); nie obniża poziomu sam.

LIGHT  — wyłącznie: dokumenty/teksty UI po polsku, CSS/układ, zmiana bez logiki
         (<= ok. 30 linii, jeden plik produkcyjny), poprawka tylko testu, literalny
         re-check jednej zamkniętej poprawki.
         Zakres: diff exact SHA + JEDEN celowany reproduktor/test. Bez pionu,
         macierzy, WHERE_MAP, PRE_IMPLEMENTATION_REDUCTION_GATE. OWNER_EXPLANATION_GATE
         tylko gdy pojawia się NOWE zachowanie widoczne dla użytkownika.
         Raport <= 30 linii: SHA, co uruchomiono, werdykt.
STANDARD — obecne INDEPENDENT_AUDIT pkt 1–3.
DEEP   — dotyka którejkolwiek ścieżki: rota/planning/**, rota/persistence/db.py,
         migracje, rota/persistence/pii_crypto.py, api/auth/**, Dockerfile, albo zmienia
         kontrakt/HARD regułę. Pełne INDEPENDENT_AUDIT (pkt 1–4, pkt 4 tylko za zgodą
         OWNERA), WHERE_MAP zgodnie z sekcją WHERE_MAP.
Ścieżki wyzwalające DEEP są mechaniczne (lista wyżej), nie ocena wykonawcy.

ROUND_CAP: max 2 rundy re-checku na ten sam temat; trzecia = WYMAGA_DECYZJI
(zgodnie z ROLE_AND_ORACLE), nie kolejna runda FAIL.
STOP_RULE: po znalezieniu wystarczającego dowodu (reproduktor FAIL lub PASS na
exact SHA w zakresie poziomu) zakończ; nie rozszerzaj poszukiwań.
```

Bramki jakościowe zostają BEZ zmian we wszystkich poziomach: exact SHA,
`DEFECT_GATE`, reproduktor per finding, PASS tylko dla SHA, nadpisywanie raportów
zabronione.

## 3. Odchudzenie plików (cel: <= 8 KB łącznie)

1. Usunąć `COORDINATOR_SIMULATORS_REMOVED` i `LEGACY_BENCHMARKS_REMOVED`; zostawić
   JEDNO zdanie: „`benchmarks/` i `tests/property/` nie istnieją; nie odtwarzać bez
   nowej decyzji OWNERA i kontraktu. Żywa infrastruktura: `tests/support/`."
   (historia zostaje w `git log`).
2. `CODEX_START_HERE.md` §4–§5 nie powtarza `DEFECT_GATE`, prechecku, limitów
   testów — odsyła do `AGENTS.md` (jedno źródło prawdy na regułę).
3. Zachować w całości: `ROLE_AND_ORACLE`, `BRIEF_ONLY_PRECHECK`, `DEFECT_GATE`,
   `OWNER_EXPLANATION_GATE`, `SYNTHETIC_DATA_NOT_PRODUCT_TRUTH`, `WORKTREE`,
   zasady raportu i UI po polsku.
Uwaga uczciwie: prompt jest cache'owany (koszt ok. 10% zwykłego), więc odchudzenie
plików daje mniej niż poziomy audytu i konfiguracja poniżej.

## 4. Ręcznie po stronie OWNERA (poza repo — nie da się tego wymusić z `AGENTS.md`)

`AGENTS.md` nie przełączy modelu ani poziomu rozumowania. Kto uruchamia audyt,
wybiera je przy starcie wątku, na podstawie `AUDIT_TIER` z BOARD:

| AUDIT_TIER | model_reasoning_effort | uwagi |
|---|---|---|
| LIGHT | low | ewentualnie mniejszy model |
| STANDARD | medium (dziś globalnie) | bez zmian |
| DEEP | high | `xhigh` tylko wyjątkowo (wg źródeł 3–5x tokenów vs medium) |

Zalecane zmiany w `~/.codex/config.toml` (weryfikuje OWNER/instancja Codexa —
CC nie ruszał; wsparcie profili w aplikacji desktopowej vs CLI niesprawdzone):
- wyłączyć na czas audytów kodu wtyczki niezwiązane z kodem (documents, pdf,
  spreadsheets, presentations, template-creator, visualize, computer-use,
  unified-computer-use); `browser` zostawić, jeśli audyt UI używa
  `playwright-interactive`;
- `model_verbosity = "low"`;
- `tool_output_token_limit = 12000` (ochrona przed długimi odczytami/logami);
- `model_auto_compact_token_limit` niżej niż domyślnie; `/compact` ok. 60% kontekstu;
- jedna sesja = jeden audyt (świeży wątek zamiast dokładania kolejnych tematów);
- profile `light`/`deep` (CLI: `codex --profile light`), jeśli aplikacja je obsługuje.

## 5. Po stronie CC (bez zmian procesu, tylko dyscyplina dostawy)

- W wierszu BOARD proponuję `AUDIT_TIER` z uzasadnieniem jedną linią (decyzja
  zostaje architekta).
- W dostawie podaję DOKŁADNĄ listę uruchomionych testów/komend, żeby Codex nie
  powtarzał ich mechanicznie (reguła już jest w `CODEX_START_HERE.md` §5).
- Małe, wąskie SHA zamiast dużych paczek.

## 6. Ryzyka i pytania otwarte (dla architekta/ownera)

1. Czy lista ścieżek DEEP jest kompletna (np. `api/routers/schedule.py`,
   `rota/application/plan_ops.py`)? Za wąska = DEEP nie wyzwoli się dla
   ryzykownej zmiany; za szeroka = wraca dzisiejszy koszt.
2. Kto przypisuje poziom przy audytach bez wiersza BOARD (bezpośrednie polecenie
   ownera)? Propozycja: owner mówi wprost, inaczej STANDARD.
3. Pomiar: dla 5 najbliższych audytów zapisać zużycie (`/status` / liczba tokenów)
   przed i po, żeby ocenić realny efekt zamiast zgadywać.
4. Czy poziom LIGHT nie osłabi wykrywalności: zabezpieczenie = wyzwalacze DEEP są
   mechaniczne, a Codex może tylko podnosić poziom.

## Źródła (zalecenia zewnętrzne; blogi praktyków, liczby orientacyjne)

- Codex Knowledge Base: Diagnosing and Reducing Codex CLI Token Consumption (2026-06)
  i Codex CLI Performance Optimisation (2026-04): profile fast/deep,
  `model_reasoning_effort`, `model_verbosity`, `tool_output_token_limit`,
  `model_auto_compact_token_limit`, zawężanie narzędzi MCP, jedna sesja = jedno zadanie,
  cache tokenów ok. 10% ceny.
- OpenAI Developers: Custom instructions with AGENTS.md (limit `project_doc_max_bytes`
  32 KiB, instrukcje zwięzłe).
- Cortex „A Practical Guide to Risk-Based Code Review", AgentPatterns.ai „Agentic
  Code Review Patterns", Cloudflare „Orchestrating AI Code Review at scale":
  wysiłek recenzji proporcjonalny do kosztu pomyłki, tanie deterministyczne kroki
  najpierw, głęboka recenzja tylko dla zmian ryzykownych.
