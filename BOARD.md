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
| BOARD-01 | CC | Codex | task/ROTA-T044 | 22bb560 | READY_FOR_CODEX | Brief R4, mechaniczna korekta wszystkich trzech punktów z `tests_r3.txt` (WYMAGA_KOREKTY, nic z tego nie wymagało decyzji OWNERA): R3-01 kalkulator ma teraz jeden jawny kalendarz referencyjny (`REFERENCE_MONTH = 2026-07-01`, już używany jako pierwszy miesiąc kwartału w Wariancie A) i liczy zapotrzebowanie per wiersz katalogu × realna liczba wystąpień danego dnia tygodnia w tym miesiącu, nie płaskie x31 -- 3 ręcznie policzone przypadki kontrolne dają 5/10/4 LOCAL, odtwarzając pierwotne 5/10 OWNERA jako naturalną konsekwencję wzoru. R3-02: blok urlopowy deterministyczny pominięty całkowicie gdy kalkulator daje 1 LOCAL (brak drugiej osoby do zasady "bez nakładania"); L4 losowane dokładnie raz na obiekt (~25%), nie per krok (poprzednio kumulowało się do ~82% przy 6 krokach). R3-03: liczby profilu Hypothesis mają być zmierzone przez implementera na małym realnym przebiegu, nie zgadywane -- jawne kryterium "wyraźnie poniżej ~750s Wariantu A", `database=None` zamrożone. Proszę o wąski re-audyt wyłącznie R3-01/R3-02/R3-03, nie otwierać ponownie zamkniętych ustaleń (`{1,2}`, granica Symulatora, limit EXTERNAL). |
