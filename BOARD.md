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
| ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT | CC | Architekt | — (finding, brak briefu) | `backend.py` niezmieniony od `03e5353` (jeden commit w całej historii); brief `tasks/ROTA-T065/brief.md` | OWNER_DECISION_NEEDED | **`backend.py` nie był nieautoryzowanie zmieniony — sprawdzone `git log --oneline -- backend.py`, dokładnie jeden commit w historii, baseline projektu. Przyczyna jest odwrotna: format brief.md architekta odjechał od kontraktu, którego `backend.py` mechanicznie wymaga, i nikt tego nie złapał, bo mechaniczna bramka nie jest już uruchamiana w bieżącym procesie CC↔Codex/BOARD.md (ostatni realny przebieg: `tasks/ROTA-T055/round_01/tests/backend_output_r4.txt`, 4 września).** `backend.py::read_task_scope()` wymaga LITERALNEJ linii `TASK_SCOPE:` (dwukropek, bez nagłówka markdown) z listą plików jako myślniki (`- plik.py`) — dokładnie tak wyglądał `tasks/ROTA-T055/brief.md` (`TASK_SCOPE:` + myślniki), i wtedy `SIZE_FILE`/`SIZE_FUNC`/`RUFF`/`DIFF_SCOPE` realnie działały. `tasks/ROTA-T065/brief.md` sekcję nazywa `## 19. Literalny TASK_SCOPE` (nagłówek markdown, nie literalne `TASK_SCOPE:`) i wypisuje pliki jako listę numerowaną (`1. `, `2. `...), nie myślnikami. Zweryfikowane bezpośrednim uruchomieniem `read_task_scope()` na tym pliku: `ValueError: TASK_SCOPE missing in brief` — parser nie znajduje sekcji wcale, więc `check_sizes`/`check_ruff`/`check_scope_and_files`/`find_importers` dostają pustą listę i milczą, zamiast wyrzucić błąd na przekroczenie limitu linii pliku/funkcji. **Prośba do architekta: pisząc TASK_SCOPE w każdym brief.md, używać dokładnie formatu `backend.py` już umie parsować — literalna linia `TASK_SCOPE:` (nie nagłówek), pliki jako myślniki, nie lista numerowana** — to jedyna mechaniczna bramka pilnująca limitu wielkości plików/funkcji niezależnie od implementatora; jej ciche wyłączenie zwiększa ryzyko rozrostu kodu (spaghetti) bez sygnału. CC nie zmienia formatu briefów samodzielnie — to decyzja architekta/właściciela co do konwencji pisania briefów. |
| ROTA-T065-PRINT-GAP | CC | Codex/Architekt | `task/ROTA-T065-PRINT-GAP` | prototyp `66c7c23` (poprzedzone PASS preimplementation `18665e3`) | READY_FOR_CODEX | **OWNER_ACCEPTED CHECKPOINT A.** Właściciel obejrzał i zatwierdził próbkę PDF (`tasks/ROTA-T065-PRINT-GAP/prototype/sample_ordinary.pdf`, dane w 100% syntetyczne) po dwóch rundach korekt — najpierw wizualny mockup HTML, potem przełożony na realny PDF tym samym silnikiem renderowania co T020. Zamrożone dokładnie:
1. **Godziny**: literalny zakres z Assignment, bez zer wiodących (`5–12`, nie `05-12`).
2. **Rola**: pełne słowo (nie litera/kod) wypisane RAZ pod nazwiskiem pracownika — jego rzeczywiste stanowisko, niezmienne dzień do dnia. Osoba pokrywająca dodatkową zmianę zwykle przypisaną innej roli NIE zmienia etykiety (owner: "to nie degradacja, tylko dodatkowa zmiana"). Komórki dni pokazują wyłącznie godziny, nigdy roli.
3. **Wiele zmian jednego dnia**: osobne linie w tej samej komórce, kolejność chronologiczna (nie separator "/" w jednej linii — nie mieścił się przy pełnym miesiącu, R1 finding).
4. **Zmiana przez północ**: godzina końcowa z dopiskiem `(+1)`, np. `22–06(+1)`, zakotwiczona na dacie startu.
5. **PLAN/WYK**: jeden wiersz na pracownika/dzień dla ORDINARY (nie dwa jak w Ochronie) — realne godziny już SĄ faktem, nie ma osobnego kodu planu i wykonania do rozjechania.
6. **Absencje**: pełne słowo (`Urlop`, `L4`), bez wypełnienia, rozróżnione WYŁĄCZNIE stylem obramowania (Urlop = pogrubiona pełna ramka, L4 = przerywana) — ten sam słownik co akceptowany druk Ochrony.
7. **Zwykły dzień bez pracy**: `–`, bez ramki.
8. **Tło strony**: zawsze białe, jawnie wymuszone niezależnie od trybu wyświetlania — realny wydruk nie ma trybu ciemnego.
9. **Wypełnienie komórek pracy**: gęstość szarości jako DODATKOWA (nie jedyna) podpowiedź tej samej roli co już widać pod nazwiskiem — potwierdzone przez ownera że wypełnienia OK, tylko całe tło strony miało wcześniej błędnie robić się szare.
10. **Rezygnacja z przykładu podwójnej roli** — pierwsza wersja (Kierownik z dopisaną na stałe drugą rolą, żeby pokryć obcy slot) odrzucona jako realny problem godności/etykietowania, nie tylko kwestia wizualna; przełożone jako dodatkowe pytanie do architekta w `ROTA-T065-CONFIGURABLE-ROLES` (substytucja/hierarchia ról).
11. Dokładna liczba i przypisanie odcieni szarości do konkretnych ról (dziś 3 przykładowe) zależy od finalnej, konfigurowalnej listy ról z `ROTA-T065-CONFIGURABLE-ROLES` — zamrożony jest JĘZYK WIZUALNY (słowo pod nazwiskiem + jednolita szarość komórki jako echo), nie konkretna paleta dla N ról.

CHECKPOINT B (implementacja produkcyjna `rota/application/schedule_export.py` wg WHERE_MAP z brief.md) jest teraz odblokowany zgodnie z brief §15 — wymaga PASS audytu brief'u (już mamy z `18665e3`) oraz zgodności z powyższą zamrożoną listą. Prototyp (`generate_sample.py`) pozostaje izolowanym artefaktem projektowym, nigdy nie był i nie jest importowany przez kod produkcyjny. |
| ROTA-T065-CONFIGURABLE-ROLES | Architekt | Codex | `task/ROTA-T065-CONFIGURABLE-ROLES` | brief `98226a792b24a293bba24bb67365b741b8403234` | READY_FOR_CODEX | Preimplementation review. OWNER correction frozen: configurable role catalog per Site; every ORDINARY demand has a role; organizational title is separate from role of work; no automatic hierarchy/fallback; manager remains manager when covering seller work; coordinator must explicitly authorize substitution or may choose external support. Verify minimal data owner and no second role/solver pipeline. |
| ROTA-T065-ORDINARY-TIME-AVAILABILITY | Architekt | Codex | `task/ROTA-T065-ORDINARY-TIME-AVAILABILITY` | brief `087c228fbea02964cc9e916a1a93637beffc1112` | READY_FOR_CODEX | Preimplementation review after/alongside configurable roles. Dated daily hourly unavailability extends existing append-only AvailabilityRecord and one shared interval-overlap oracle for solver + manual validation. No D/N or shift-row semantics, no second availability engine. |
| ROTA-T065-MANUAL-MIDDLE-SHIFT | Architekt | Codex | `task/ROTA-T065-MANUAL-MIDDLE-SHIFT` | brief `41f2e4c84fc8498dd87eae7b069b9ac0a659b317` | READY_FOR_CODEX | Preimplementation review after configurable roles. Manual seasonal/event middle work only through existing manual-correction child ScheduleVersion; real work with normal HARD/deviation rules, mandatory performed role, no S1 exemptions, no solver/generator or separate history. |
