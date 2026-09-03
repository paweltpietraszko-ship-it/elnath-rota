# BOARD.md — kolejka przekazań CC ↔ Codex

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalaczem pracy; ten plik tylko rejestruje
przekazanie, żeby nie trzeba było ręcznie przeklejać wiadomości między CC a
Codexem.

Statusy (dokładnie cztery, nic więcej):

- `READY_FOR_CODEX` — CC skończył, czeka na audyt.
- `CODEX_IN_PROGRESS` — Codex audytuje.
- `CODEX_REPORTED` — raport gotowy pod wskazaną ścieżką.
- `OWNER_DECISION_NEEDED` — audyt utknął na decyzji właściciela.

Nowy wiersz dopisuje autor przekazania; zmianę statusu na kolejny etap
wpisuje ten, kto ten etap kończy. Zamknięty wiersz (merge/decyzja, ostatni
status rozstrzygnięty) usuwa z tego pliku ten, kto go zamyka — pełna
historia i tak zostaje w `git log -p BOARD.md`, więc nic nie ginie, tylko
plik nie rośnie w nieskończoność (2026-08-29, OWNER_CORRECTED: wcześniejsza
wersja tej reguły mówiła "nie kasować wierszy" — celowo zmienione).

| ID | Autor | Odbiorca | Branch | Exact SHA | Status | Wiadomość |
|---|---|---|---|---|---|---|
| BOARD-08 | CC | Codex | task/ROTA-T049 | cba913f | READY_FOR_CODEX | Implementacja gotowa do audytu na kontrakcie PASS `bec6100`. `CreateSiteRequest`/formularz/`client.ts` — pole usunięte, `SiteProfile.display_name=payload.display_name` (kopiuje nazwę obiektu). 3 miejsca w harnessach symulatorów i 8 plików e2e (26 wywołań `createSite()` przez wspólny helper + 4 bezpośrednie wypełnienia w `diagnostics.spec.ts`/`diagnostics.audit-r1.spec.ts`) zaktualizowane, żadne nie wysyła już usuniętego pola. Zweryfikowane end-to-end: `POST /workspace/sites` bez pola działa, zapisany `SiteProfile.display_name` faktycznie przejmuje nazwę obiektu. Szybki przebieg obu harnessów symulatorów zielony, `ruff`/`git diff --check` czyste. Frontend build/typecheck niemożliwy w środowisku implementatora (brak `node_modules`) — zaznaczone transparentnie, jak przy T047/T048. `backend.py` (`bec6100..bed6a6d`): **FAIL wyłącznie na trzy nadwyżki sprzed tej zmiany** — `coordinator_simulator.py` 1477/600, `compute_quarter_oracle` 81/50 (funkcja nietknięta, ~540 linii od mojej edycji), `test_coordinator_simulator_variant_b.py` 729/600 — wszystkie zweryfikowane jako identyczne na kontrakcie PASS przed implementacją. **OWNER zaakceptował: "Akceptuję nadwyżki, wysyłaj do Codexa."** Jedno odstępstwo od dosłownego briefu, zgłoszone OWNEROWI i zaakceptowane milcząco (brak sprzeciwu): `diagnostics.spec.ts` test 10 miał osobny „kanarek prywatności" (`canaryProfile`) specyficzny dla usuwanego pola — usunięty razem z polem (deklaracja + wpis w pętli sprawdzającej wyciek), zamiast zostawić martwą zmienną lub zawsze-prawdziwe sprawdzenie. Pełny werdykt: `tasks/ROTA-T049/round_01/tests/backend_output.txt`. Zero innych zmian poza `TASK_SCOPE`. |
