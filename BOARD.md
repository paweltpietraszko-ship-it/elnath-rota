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
| ROTA-T065-PRINT-GAP | CC | Architekt | — (finding, brak briefu) | `rota/application/schedule_export.py` (T020 kontrakt) niezmieniony przez T065; brief `tasks/ROTA-T065/brief.md` sekcje 19/21 (linie 251, 382) jawnie wyłączają PDF z zakresu | OWNER_DECISION_NEEDED | **Wydruk (`rota/application/schedule_export.py`) jest w całości zaprojektowany pod OCHRONA i nie działa dla nowych ról ORDINARY (Kierownik/Sprzedawca-załoga) — sprawdzone bezpośrednio przez `where.py --symbol EmployeeRole`: zero wystąpień w tym pliku.** To zgodne z briefem T065 (sekcja 19/21, linia 251/382): PDF był jawnie wyłączony z zakresu jako "osobny późniejszy Task". Ten finding jest tym Taskiem — właściciel poprosił o zbadanie, co trzeba zaprojektować.

**Konkretne miejsca, które się łamią:**
1. `_map_work_code` (linia 427) wymaga `demand.shift_kind` (D/N) i dokładnego dopasowania czasu trwania do sztywnej tabeli `site_repository.FROZEN_WORK_CODE_HOURS` (`D1=12h,D2=4h,D3=24h,D4=2h,D5=24h,N1=12h,N2=16h,N3=24h,N4=24h,N5=24h`). Typowa zmiana sklepowa (np. 8h) nie ma żadnego pasującego kodu → `WORK_CODE_MAPPING_REQUIRED`, eksport PDF kończy się błędem.
2. Nawet gdy długość akurat trafi w istniejący kod, wydrukowana komórka pokazuje gołe "D1"/"N1" bez żadnej informacji o roli (Kierownik vs Sprzedawca-załoga) — `_family()` (linia 685) i legenda `_legend_entry_text` (linia 788) znają wyłącznie D/N/U/C/24/S1.
3. Logika absencji (`_legal_uc_value` linia 454: `U1=12,U2=16,C1=12,C2=16`; `_pair_values`/`_minimal_sequence`/`_decompose`, linie 456-504) to algorytm "coin change" rozkładający godziny absencji na sztywne bloki zmianowe — sensowne tylko tam, gdzie zmiany są ustandaryzowane (Ochrona). Dla sklepu z 8h/dzień to założenie jest bez sensu.
4. `SitePrintSettings.work_code_intervals` (ekran konfiguracji wydruku) każe koordynatorowi z góry zdefiniować godziny startu/końca DLA KAŻDEGO symbolu D1-D5/N1-N5 — dla Ordinary nie ma z góry ustalonych symboli do skonfigurowania.

**Research (na wyraźną prośbę właściciela — nie zgadywać wzoru z powietrza):** Kodeks pracy art. 129 §3 wymaga wprost, żeby grafik podawał **godziny rozpoczęcia i zakończenia pracy w każdym dniu roboczym** — to wymóg prawny, nie tylko wygoda; żaden przepis nie wymaga kodów zmianowych. Dostępne branżowe szablony sklepowe (Kadromierz, GrafikPro, Excelness, Proplanum) idą w stronę zwykłych zakresów godzin w komórce, nie kodów — bo zmiany sklepowe nie mają ustandaryzowanej długości. Absencja wg prawa oznaczana jest nazwą typu (urlop/L4/dzień wolny), nie zakodowaną wartością godzinową. Realny obrazek `Grafiki/7732.jpg` (obiekt ROYALPACK/APEXIM, ochrona) potwierdza, że obecny model D1-D5/N1-N5/U1-U5/C1-C5 wprost odwzorowuje istniejący branżowy arkusz ochrony — nie jest to model uniwersalny, tylko dopasowany do tej jednej branży. Nie istnieje gotowa biblioteka/szablon open-source do podłączenia (sprawdzone: generyczne tutoriale ReportLab identyczne z tym, czego już używamy; `pdfschedule` to kalendarz jednej osoby, nie roster wielu pracowników; pełne produkty typu Kadromierz/Planday/TimeTrex to konkurencyjne aplikacje, nie komponenty do wpięcia) — silnik renderowania PDF (strony/nagłówki/czcionki polskie) z T020 nadaje się do ponownego użycia, zmienia się tylko logika treści komórki.

**Kierunek zaakceptowany wstępnie przez właściciela, do sformalizowania przez architekta:** dla obiektów ORDINARY osobny, prostszy model prezentacji równoległy do OCHRONA (rozgałęzienie po `site.planning_regime`, nie przebudowa istniejącego): komórka = dzień tygodnia + realny zakres godzin z przydziału (np. "Pon 5–12"), absencja = słowo typu (Urlop/L4/Wolne) zamiast kodu z ukrytą wartością godzinową, brak legendy symboli, suma godzin miesięcznie na końcu wiersza. Do zaprojektowania przez architekta: (a) czy `SitePrintSettings`/ekran konfiguracji wydruku ma osobną, dużo uboższą wersję dla ORDINARY (bez `work_code_intervals`), czy pole staje się opcjonalne/pomijane; (b) czy to nowa funkcja równoległa do `_render_pdf`/`_map_work_code` w tym samym pliku, czy osobny moduł; (c) jak numeracja stron/legenda/nagłówek (dziś współdzielone) mają się zachować, gdy jeden print dostaje symbole a drugi nie. CC nie projektuje tego samodzielnie — to zmiana zamrożonego kontraktu T020 wymagająca pełnego briefu i audytu Codex jak T065. |
