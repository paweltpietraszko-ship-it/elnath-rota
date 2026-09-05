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
| ROTA-T056 | CC | Codex | `task/ROTA-T056` | `41e9208` (frontend §6/8) | READY_FOR_CODEX | **Frontend zaimplementowany na potwierdzonym PASS backendzie (`f9f0345`, raport `1de4736`).** `api/client.ts`: typ `MonthlyExtraWorkCodesOut` + `getMonthlyExtraWorkCodes`/`saveMonthlyExtraWorkCodes`. `Room.tsx -> ControlPanel.tsx`: `workingMonth` teraz przekazywane (wcześniej w ogóle nie szło do ControlPanel) tak jak wymaga brief §6. `PrintSettings.tsx`: nowa sekcja "Dodatkowe kody dla {miesiąc}" — osobny load/save, dodawanie/usuwanie wierszy, walidacja kształtu kodu po stronie klienta (rodzina D/N, suffix>=6) lustrzana do `_EXTRA_CODE_RE`, serwer pozostaje ostatecznym autorytetem. `MonthlyPlanning.tsx`: panel ręcznej korekty ma nowy selektor "Zamień na dodatkowy kod" — widoczny tylko dla zwykłego PRIMARY z jednoznacznym demandem D/N (nie S1/TRAINEE/NN/CANCELLED), oferuje tylko kody właściwej rodziny na bieżący miesiąc; wybór buduje nowy realny start/end zakotwiczony na dacie demandu (ten sam wzorzec co `addS1` dla end_next_day) i idzie przez istniejący `runCorrection`/`applyManualCorrection` — bez nowego endpointu, bez `operational_code`. **Zweryfikowane:** `npx tsc -b` czyste (exit 0); ręcznie zasiałem realny obiekt/roster/kalendarz/PLAN do jednorazowej bazy dev i uruchomiłem prawdziwe serwery uvicorn+vite — oba wstały, API odpowiada poprawnie. **Nie zweryfikowane przeze mnie:** rzeczywiste klikanie w przeglądarce — rozszerzenie Claude-in-Chrome nie było podłączone w tym środowisku, więc nie potwierdziłem wizualnie nowego UI. Zgłaszam to wprost zamiast twierdzić, że sprawdziłem coś, czego nie sprawdziłem — proszę o `playwright-interactive` albo szybki ręczny rzut oka przed dalszymi krokami. Po tym nadal wymagany pełny pion i oba REAL PDF GATE (T56-13/14). |
