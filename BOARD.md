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
| ROTA-T065 | Codex | Architekt | `main` (finding + zweryfikowany scope, brak briefu) | finding `3d9600f`; scope `66181cf`; re-check na `c60f944` | CODEX_REPORTED | **GOTOWE DO ARCHITEKTA — fakty i mapa właścicieli zweryfikowane po korekcie.** Potwierdzone: istniejący wzorzec `SiteMembership.can_work_24h`; przepływ `StandardShift` → `_Component` → `ShiftDemand`; wspólna bramka przed rozgałęzieniem LOCAL/EXTERNAL_SUPPORT; niezależny HARD validator dla ręcznych/istniejących Assignmentów; konieczność migracji i repozytoriów; istniejące wejścia API oraz ekrany zarządzania członkostwem i katalogiem; płaskie sortowanie wydruku w `_build_rows`. Rekomendacja dwóch kolejnych Tasków jest zasadna, ale zależna: najpierw kategorie w domenie, zapisie, planowaniu, walidacji i UI, następnie wydruk. Brief musi pozostawić do jawnej decyzji OWNERA: kategoria globalna czy per obiekt (rekomendowany przez CC precedens: `SiteMembership`), czy uwzględniać ekipę sprzątającą, czy `EXTERNAL_SUPPORT` zachowuje zgodność kategorii, oraz czy historyczny wydruk grupuje według bieżącego membership czy migawki zapisanej z grafikiem/demandem. To są decyzje produktowe, nie braki rozpoznania. Architekt może przygotować brief bez ponownego audytu scope przez Codexa. |
