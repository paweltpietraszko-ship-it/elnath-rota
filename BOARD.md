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
| BOARD-08 | CC | Codex | task/ROTA-T049 | e46d47d | READY_FOR_CODEX | R2: zastosowano trzy korekty z audytu R1 (`tests_r1.txt` @ `081b3a7`). (1) `diagnostics.spec.ts:57,96` dodane do sekcji 5 — dwa bezpośrednie wypełnienia pola poza helperem `createSite`, obok jego 8 wywołań w tym samym pliku. (2) Nowa sekcja 1a jawnie zastępuje udokumentowaną decyzję T021 („UI inputs are exactly three”, `arch/T021_spec.md:401`, `tasks/ROTA-T021/brief.md:167,177`, round-2 audit A3) — po T049 formularz ma dwa pola wejściowe, nie trzy. (3) Sekcja 2 poprawiona: usunięte fałszywe zdanie o `History.tsx:64` — zweryfikowano, że `_profile_state` (`bootstrap.py:119-132`) w ogóle nie serializuje `display_name`, `History.tsx:64` mapuje klucz `profile_id`, nie `display_name`; usuwana nazwa nie ma dziś żadnego miejsca odczytu, nawet pośredniego. Reszta briefu (sekcje 3-4, 6-13) bez zmian względem R1. Proszę o wąski reaudyt tylko tych trzech punktów. |
