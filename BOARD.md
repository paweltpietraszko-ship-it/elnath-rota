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
| ROTA-T056 | CC | Codex | `task/ROTA-T056` | `4faad52` (backend only, frontend jeszcze nie zaczęty) | READY_FOR_CODEX | **Prośba o audyt backendu przed frontendem — OWNER (Paweł) słusznie zauważył, że pisanie frontendu na niezweryfikowanym backendzie namnoży błędy.** Zaimplementowane na `4faad52` (poprzedni commit warstwy persystencji/API: `09995f6`): §4-7 (migracja 13, `MonthlyExtraWorkCodes`, wspólny invariant kolizji na obu write boundaries, `durable_inputs.save_monthly_extra_work_codes`, `api/routers/export.py` GET/PUT) oraz §8-13 dot. eksportu: `_validate_item` — wąski wyjątek 7 warunków z briefu §9.1 (dokładnie taki, jak zatwierdzony w exact SHA `404580b`); `_map_work_code`/`_hours_of` rozszerzone o D6+/N6+ (§9.2/9.3, nigdy cicho 0h); legenda pokazuje tylko użyte kody z automatyczną drugą stroną gdy nie mieszczą się (§9.4/11, OWNER ruling); `_document_revision` obejmuje dokładny `(site,month)` config extra codes (§9.5). Reproduktor R6 przeniesiony do `tests/test_t056.py` (T56-01/02/03/04/06/07/08/09/12), standalone skrypt usunięty z diffu jak wymagał §16. 4 nieaktualne testy wersji schematu naprawione (§11) — przy okazji `test_t019b.py`'s expected-new-tables set też był już nieaktualny przed T056 (brakowało `plan_previews` z T054); CC naprawił to tym samym literalnym zabiegiem zamiast zostawić połowicznie, co jest odrobinę szersze niż litera §11 ("wersji schematu" dosłownie) — proszę Codexa o ocenę, czy to akceptowalne czy wymaga osobnej decyzji OWNERA. Zweryfikowane: pełne `test_t020.py` (45), `test_t012/t019b/t023b.py` (207), `test_t021_export_api/t023_checkpoint_c/t047_print_export/vertical_full_stack.py` (28), nowe `test_t056.py` (14) — wszystko zielone. CC dodatkowo ręcznie wyrenderował i przeczytał dwa prawdziwe PDF-y (normalny przypadek + 60 pracowników/60 różnych extra codes wymuszające prawdziwą drugą stronę legendy) jako własną, nieformalną kontrolę — to NIE zastępuje wymaganego REAL PDF GATE z ludzką oceną optyczną (T56-13/14), które wciąż czekają, tak jak frontend (§6/8, T56-05). Proszę o wąski audyt tego, co jest gotowe, zanim CC zacznie frontend. |
