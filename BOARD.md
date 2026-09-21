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
| ROTA-RARE-WEEKLY-SLOT-PINNED | Architekt | CC | — (dowód wykonalności, bez zmiany kodu) | `arch/FINDING_2026-09-21c_CONTROLLED_EXPERIMENT_DOES_NOT_REPRODUCE_REAL_SKEW.md` | READY_FOR_CODEX | **NOWA HIPOTEZA MATEMATYCZNA ARCHITEKTA — sprawdź ją NIEZALEŻNIE, szukając kontrprzykładu, nie zakładaj PASS solvera.** OWNER potwierdził: po ręcznej zamianie soboty na dzień tygodnia Paweł przekroczył w ruchomym oknie 7 dni 40h (otrzymał 48h), choć miesięczne sumy obu osób były równe. Dla standardowego Bolf: TYLKO 2 dostępnych LOCAL, w każdym pełnym tygodniu 5 pojedynczych zmian pn–pt po 12h oraz 1 sobotnia 9h (niedziela wolna), pełne pokrycie, twarde obciążenie każdego pracownika <=40h w dowolnym ruchomym 7-dniowym oknie, bez dodatkowego pracownika ani innych nakładek: sześć zmian tygodniowo wymusza dokładnie po TRZY zmiany dla każdej osoby (4 zmiany mają minimum 3×12+9=45h). Porównaj dwa sąsiednie 7-dniowe okna sobota[n]–piątek[n+1] i niedziela[n]–sobota[n+1]: mają DOKŁADNIE te same 5 zmian pn–pt, różnią się tylko sobotą[n] vs sobotą[n+1]; skoro obie osoby muszą mieć po 3 zmiany w OBU oknach, soboty muszą należeć do TEJ SAMEJ osoby. Indukcyjnie wszystkie soboty miesiąca muszą być u jednej osoby. To może być poprawne działanie solvera, a nie błąd weekend fairness! **ZADANIE CC:** najpierw na kartce/przy małym deterministycznym enumeratorze niezależnie zweryfikuj dowód lub podaj konkretny legalny grafik z rozdziałem sobót; nie używaj CP-SAT wyniku jako dowodu. Następnie zweryfikuj warunki dowodu wobec faktycznego Bolf: profil 40h vs `rolling_7d_decision_threshold_hours`, HARD czy decyzja/soft, wszystkie soboty i dniówki 9/12h, wymagane coverage, pozostałe osoby/zewnętrzne wsparcie, granice miesiąca i ewentualne już istniejące godziny; szczególnie wyjaśnij dlaczego wcześniejsza uproszczona rekonstrukcja dawała 3/2 OPTIMAL — który warunek dowodu w niej NIE obowiązywał (np. parametr progu, `enforce_load_cap` lub wariant dopuszczający przeciążenie). Nie podejmuj kolejnych hipotez o seed/PII przed tym rozstrzygnięciem. Zapisz krótki raport: (a) dowód lub kontrprzykład, (b) tabelka warunki dowodu vs realny obiekt i uproszczone repro, (c) wniosek czy 3/2 jest w ogóle możliwe bez naruszeń. TYLKO diagnoza, bez kodu produkcyjnego, nowych wag, rotacji i merge; wynik przez BOARD do Architekta. |
