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
| BOARD-01 | CC | Codex | task/ROTA-T044 | f69c0ae | READY_FOR_CODEX | Brief R3, rozstrzyga wszystkie trzy punkty z `tests_r2.txt` (OWNER_DECISION_NEEDED): R2-01 kalkulator liczy na 31-dniowym miesiącu i odejmuje margines urlopowy (36 dni/rok ZPCh -> 24h/mies.) przed dzieleniem; nowa sekcja 1.2a rozdziela to od realnych bloków urlopowych (2 tyg./tydz., bez nakładania, deterministyczne) i L4 losowanego probabilistycznie ~25% (nie sztywny licznik). R2-02: `required_primary_count` zawężony do {1,2} (OWNER: "zostaje wąski zakres"). R2-03: zamrożone konkretne liczby Hypothesis (20/6 domyślnie, 50/10 eksploracyjnie, deadline=None, derandomize=False) i limit EXTERNAL = liczba_LOCAL z kalkulatora. Nowa sekcja 7a wymienia OWNER+CC świadomie zaakceptowane uproszczenia (kalkulator = przybliżenie nie model kadrowy, L4 poza kalkulatorem, bloki urlopowe niezależne od rocznego budżetu, wąski required_primary_count, niezweryfikowane empirycznie liczby profilu Hypothesis) -- audyt ma ocenić ich wykonywalność/spójność, nie odsyłać briefu jako "niedopracowany" za te konkretne, nazwane po imieniu decyzje. Proszę o wąski re-audyt wyłącznie R2-01/R2-02/R2-03 + sekcji 1.2a/7a, zgodnie z zapowiedzią w tests_r2.txt. |
