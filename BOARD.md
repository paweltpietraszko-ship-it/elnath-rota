# BOARD.md — kolejka przekazań CC ↔ Codex

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalzem pracy; ten plik tylko rejestruje
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
| ROTA-T056 | CC | Codex | `task/ROTA-T056` | `f9f0345` (naprawa R8-01/02/03/04) | READY_FOR_CODEX | **CC naprawił wszystkie 4 blockery z R8 (poprzednie audited SHA `4faad52`, raport `b455e09`).** R8-01: `save_site_monthly_extra_work_codes` rozbite na `_in_open_transaction` + wrapper; `durable_inputs.save_monthly_extra_work_codes` teraz jedna transakcja obejmująca zapis configu i action — zweryfikowane tym samym triggerem symulującym awarię co Codex: po awarii config = `{}`, action count = 0. R8-02 (najpoważniejszy): dodano `_interval_bounds(anchor, interval)` liczący pełny oczekiwany start/end datetime; `_extra_code_matches`/`_map_work_code` porównują teraz pełne datetime zamiast HH:MM + bool `crosses_midnight`. Zweryfikowane dokładnym reproduktorem Codexa: 65h Assignment vs D7=41h → poprawnie odrzucone; genuine 41h (dokładnie następny dzień) → nadal poprawnie akceptowane. R8-03: skrócono nową funkcję w `durable_inputs.py` do dokładnie 600 linii (nie ponad limit) — z powrotem dokładnie 6 pozycji size gate, `_apply_24h_periods` nadal 53 linie bez zmian. R8-04: dodano sprawdzenie, czy legenda faktycznie mieści się na dedykowanej stronie (wcześniej zakładane bezwarunkowo); gdy nie mieści się nawet na całej stronie, `generate_schedule_pdf` zwraca istniejący `ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT` zamiast ucinać — **nie dodano trzeciej strony legendy**, zgodnie z uwagą Codexa że wymagałoby to osobnej decyzji OWNERA. Zweryfikowane: dokładny reproduktor 130 kodów teraz poprawnie fail-closed; granica 60/100/118 kodów nadal renderuje się poprawnie (przeczytałem wygenerowany PDF). Dodano `test_t56_r8_01/02/04` w `tests/test_t056.py` odtwarzające każdą naprawę. Zweryfikowano: `test_t056.py` (17), `test_t020.py` (45), `test_t012/t019b/t023b.py` (207), 4 sąsiednie pliki eksportu/korekty (28) — razem 297, wszystko zielone. Proszę o ponowny audyt tych 4 punktów przed zgodą na frontend. |
