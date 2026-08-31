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
| BOARD-01 | CC | Codex | task/ROTA-T044 | 688a165 | READY_FOR_CODEX | Dopisek do R7 (sekcja 7a): OWNER dodał jawne uzasadnienie, dlaczego kalkulator nie musi być zweryfikowany dla KAŻDEJ możliwej liczby LOCAL, tylko dla ręcznie policzonych przypadków kontrolnych (5/10/4) -- "jeśli udowodnimy że Rota prawidłowo wylicza przy X pracowników to poprawnie wyliczy i przy X +/- 1", bo solver nie ma progu specyficznego dla konkretnej liczby osób. Sprawdzone też źródła branżowe (PZP Ochrona, Polska Izba Ochrony) -- publikują wyłącznie kalkulatory kosztu roboczogodziny, nie metodykę obsady, więc nie ma oficjalnej formuły do porównania. Reszta R7 Brief R7 -- OWNER zweryfikował R6 na własnym referencyjnym obiekcie (D/N 12h, required_primary_count=1, 5 osób) i złapał, że margines urlopowy sam windował go do 6: "jeśli sztucznie zawyzysz obsadę to dasz fory solverowi [...] za mało, to solver będzie rządać wciąż wsparcia za dużo będzie mieć fory." Margines USUNIĘTY CAŁKOWICIE (nie zmniejszony). Dwie niezależne poprawki: (1) `required_primary_count` to teraz cecha CAŁEGO obiektu (losowana raz, {1,2}), nie per wiersz katalogu -- pasuje do przykładu OWNERA (D i N mają tę samą wartość) i unika niejasności "co gdy D i N różne". (2) Kalkulator liczy jedną warstwę i mnoży przez tę wartość -- zweryfikowane: stabilne 5/10 na wszystkich 12 miesiącach dla wzorów "cały tydzień" (bez żadnej pomocy), maksimum po 12 miesiącach z poprzedniej rundy zostaje wyłącznie dla wzorów asymetrycznych (zweryfikowane: 3 albo 4 zależnie od miesiąca dla "tylko dni robocze"). Granica liczba_LOCAL==1 z poprzedniej rundy bez zmian. Przy okazji naprawione też dwa kolejne martwe/nieaktualne fragmenty w sekcji 7a znalezione przy przeglądzie. Proszę o wąski re-audyt: kalkulator bez marginesu (1.1), required_primary_count per obiekt (1.2), zgodność TASK_SCOPE/WHERE_MAP z tą zmianą. |
