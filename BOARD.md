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
| ROTA-RARE-WEEKLY-SLOT-PINNED | CC | Architekt | -- (dowod zweryfikowany, brak kodu) | brak (prawdopodobnie nie wymaga zmiany solvera) | OWNER_DECISION_NEEDED | **DOWOD ARCHITEKTA ZWERYFIKOWANY RECZNIE (bez CP-SAT), zgadza sie.** 4 zmiany w oknie 7-dniowym = minimum 3x12+9=45h>40h, wiec nikt nie moze miec >3 zmian/okno; 6 zmian tygodniowo / 2 osoby / max 3 kazda => dokladnie 3-3; dwa sasiednie okna (sobota[n]-piatek[n+1] i niedziela[n]-sobota[n+1]) maja identyczne 5 zmian powszednich, roznia sie tylko sobota -- skoro oba wymagaja 3-3 a liczba zmian powszednich danej osoby jest STALA w obu oknach, ta sama osoba musi miec OBIE soboty; indukcyjnie wszystkie soboty miesiaca. Warunki dowodu POTWIERDZONE dla realnego Bolf (wszystkie odczytane wczesniej w tej sesji): dokladnie 2 LOCAL, rolling_7d_decision_threshold_hours=40 (HARD, add_load_constraints solver.py:1285), pelne pokrycie 5x12h pn-pt + 1x9h sobota, niedziela bez zmiany, zero external support uzytego, zero absencji. Dokladnie wyjasnia rozbieznosc: kazda rekonstrukcja CC w tej sesji uzywala rolling_7d_decision_threshold_hours=999 (efektywnie wylaczone), wiec dowod nie mial zastosowania i 3/2 bylo osiagalne. **WNIOSEK: to prawdopodobnie NIE jest blad solvera -- 5/0 jest matematycznie wymuszone przez realne dane obiektu (mala pula + HARD limit), nie slabosc tie-breaka.** Nie zamykam formalnie bez ponownego uruchomienia CP-SAT z poprawnym rolling_7d=40 jako ostatecznego potwierdzenia (nie wykonane w tej sesji z braku budzetu) -- ale dowod reczny + wszystkie potwierdzone realne warunki nie pozostawiaja miejsca na inna interpretacje. Osobno zaflagowane, nieimplementowane: rolling_7d_decision_threshold_hours nie ma ekranu edycji dla istniejacego obiektu (tylko create-time default=40) -- to bylo jedyne narzedzie, ktorym Pawel probowal to obejsc (40->48) i nie znalazl. Sesja CC konczy sie tutaj z braku budzetu -- nastepna sesja/Codex: uruchom finding 2026-09-21c z rolling_7d=40 dla ostatecznego potwierdzenia, zamknij wpis jesli sie zgadza. |

| ROTA-OCHRONA-EDIT-7D-LIMIT | CC | Architekt | `task/ROTA-OCHRONA-EDIT-7D-LIMIT` | `ef94c10` | OWNER_DECISION_NEEDED | **ZAIMPLEMENTOWANE w trybie wyjatkowym bez Codexa (za zgoda ownera 2026-09-21), gotowe do decyzji o merge.** Precheck briefu: brief wezki, zadnych realnych blokerow ani zbednego zakresu. Zakres dokladnie wg TASK_SCOPE: (1) nowe GET/PUT `/workspace/sites/{site_id}/rolling-7d-limit` w `api/routers/site_profile.py` -- ten sam wzorzec co istniejace `delegation-default-hours`, marszaluje istniejace `SiteProfile.rolling_7d_decision_threshold_hours` przez istniejace `update_site_profile()` bez zmian (zadnego nowego pola DB, zadnej nowej sciezki zapisu); OCHRONA-only egzekwowane PO STRONIE SERWERA (ORDINARY odrzucane niezaleznie od UI); >72h wymaga `confirmed_over_72h=true` egzekwowane na samym API (nie tylko w modalu) i zapisywane w istniejacym `note` audit trail decyzji razem z automatycznym before/after state, ktore `update_site_profile` juz rejestruje dla tego pola. (2) `frontend/src/screens/SiteRolling7dLimit.tsx` -- przycisk "Zmien limit godzin" + maly modal (obecna wartosc, pole nowego limitu, Anuluj/Zapisz); ostrzezenie z dokladna trescia z briefu + niezaznaczony domyslnie checkbox pojawiaja sie DOPIERO po wpisaniu wartosci >72h; zamontowane w zakladce Obiekt panelu sterowania, warunkowo `planningRegime === "OCHRONA"` (zero kontrolki dla ORDINARY). (3) `tests/test_ochrona_edit_7d_limit.py` -- 9 testow pokrywajacych wszystkie 5 testow akceptacyjnych briefu; wszystkie przechodza, brak regresji w sasiednich suite (test_t030_shift_catalog_api, test_t011_c_site_coordinator_lifecycle), ruff czysty, `tsc --noEmit` czysty. **Granice weryfikacji (uczciwie):** NIE weryfikowane przegladarkowo/wizualnie (modal, checkbox, ostrzezenie nie zostaly obejrzane w dzialajacym UI, tylko typecheck + testy API); wspoldzielony profile_id pomiedzy obiektami nie dostal nowej ochrony -- `update_site_profile` juz istniejaco rejestruje `affected_site_ids` dla wszystkich obiektow z tym profilem (tak samo jak kazda inna edycja profilu), wiec zmiana progu dla profilu wspoldzielonego wplynie na wszystkie jego obiekty widoczne w audit trail, ale nie dodalem osobnego ostrzezenia o tym (brief nie wymagal). CC self-test nie jest niezaleznym audytem; merge wylacznie po decyzji OWNERA. |
