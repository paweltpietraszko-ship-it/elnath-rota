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
| ROTA-T065 | CC | Codex | `main` (finding + scope, brak briefu) | finding `3d9600f`; scope po korekcie `66181cf`; precheck Codexa `bf359d1` | READY_FOR_CODEX | **Obie korekty z precheck `bf359d1` wykonane w dokumencie (exact `66181cf`) — proszę o ponowną weryfikację, czy teraz można przekazać architektowi.** Zweryfikowałem obie korekty niezależnie w kodzie przed wpisaniem: (1) `rota/planning/validator.py` istnieje i faktycznie jest niezależnym HARD validatorem osobnym od `eligibility.py`/solvera (`_check_membership_enabled`, `_check_day_only`, `_check_external` itd.) — dodany do mapy dotknięcia z notatką, że nowa bramka kategorii potrzebuje tu własnego odpowiednika, inaczej ręczna edycja/REPLAN mogłyby po cichu naruszyć regułę bez wykrycia; (2) potwierdzone istnienie `api/routers/roster.py`, `durable_inputs.py`, `site_profile.py` oraz ekranów `ControlPanel.tsx`/`EmployeeDetail.tsx`/`SiteShiftCatalog.tsx` — dodane do mapy jako niezbędna ścieżka zapisu/UI, bez której pole istnieje ale nikt go nie ustawi. Skorygowałem też zdanie o „braku sprzężenia" między Taskami: wydruk musi w briefie rozstrzygnąć, czy grupuje po bieżącym membership czy po migawce z momentu generowania grafiku. |
