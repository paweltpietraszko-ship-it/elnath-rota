# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

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
| ROTA-OCHRONA-EQUITY-SURGICAL-FIX | CC | Antigravity | `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX` | brief poprawiony `a21b919` | READY_FOR_CODEX | **OWNER_CORRECTED 2026-09-20 (sekcja 3a poprawiona, dosłownie): "w życiu nie jest tak jak byś chciał czyli 0/1... Solver powinien respektować wszystkie zasady i mieć hierarchię ważności gdy trzeba coś poświęcić na rzecz czegoś innego. I to zostało zaprzepaszczone."** Poprzednia wersja tego wiersza (SHA `5af157b`) błędnie stawiała OWNEROWI pytanie "priorytet: rozstrzał czy rytm" — wycofane jako fałszywy wybór. Poprawne ujęcie: solver już ma działający mechanizm ścisłej hierarchii SOFT (wzorzec "strictly dominate" konsekwentnie użyty w `_add_combined_objective`, np. TARGET-01 nad equity+rytm, dawny equal-split nad rytm+weekend+holiday) — to działało poprawnie wcześniej. Regresja to nie brak hierarchii, tylko zła rola TARGET-01 w niej (karze niedobicie do sufitu jak cel, zamiast tylko przekroczenie). Poprawka ma przywrócić TARGET-01 rolę sufitu, żeby CAŁA istniejąca hierarchia znów działała — bez arbitralnego poświęcania sprawiedliwości ani rytmu. Zmierzony spadek rytmu w eksperymencie pos-only (23→11, `pos_only_report.md`) przeformułowany jako pytanie TECHNICZNE dla architekta+Codex, nie decyzja OWNERA: czy proste wyzerowanie `neg` psuje istniejący porządek wag (equity i rytm mają dziś RÓWNE wagi =1, więc bez różnicującej presji `neg` mogą zacząć swobodnie konkurować) — do zweryfikowania i poprawnego zakodowania, nie do arbitralnego rozstrzygnięcia. Pozostałe 4 punkty prechecku (metryka fallbacku, semantyka braku targetu, mieszany wektor/REPLAN, zakres testów) bez zmian względem poprzedniej korekty. Pełny brief: `tasks/ROTA-OCHRONA-EQUITY-SURGICAL-FIX/brief.md`. Proszę o niezależny precheck Antigravity na dokładnym SHA `a21b919`. |
