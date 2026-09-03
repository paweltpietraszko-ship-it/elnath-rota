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
| BOARD-08 | Codex | CC | task/ROTA-T049 | cba913f | CODEX_REPORTED | `PASS`. Pole usunięte z UI/API i wszystkich żywych nadawców; realny POST zapisuje nazwę obiektu także jako techniczną nazwę profilu, oba krótkie kroki tworzenia obiektu w symulatorach przeszły, build frontendu i celowany Playwright tworzenia obiektu przeszły. Usunięcie `canaryProfile` jest TECHNICAL_ONLY i nie osłabia testu prywatności: nadal chronione są dane formularza przez `canarySite`, dane pracownika i treść błędu. „Milcząca akceptacja” nie jest decyzją OWNERA, ale tu nie była potrzebna. Osobno ujawniono stary błąd wspólnego helpera e2e: `openSite` czeka na „Panel sterowania”, choć aplikacja otwiera „Przegląd”; istniał już na kontrakcie PASS i nie obciąża T049. Raport: `tasks/ROTA-T049/round_01/tests/tests_r3.txt` na `task/ROTA-T049@967b25d`. |
