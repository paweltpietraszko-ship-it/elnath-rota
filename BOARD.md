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
