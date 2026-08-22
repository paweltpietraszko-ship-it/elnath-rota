# START HERE — HANDOFF DLA NASTĘPNEJ INSTANCJI CODEX

Data: 2026-08-22

## 1. Aktualny stan

- Branch: `task/ROTA-T023`
- Aktualny HEAD: `e6bed762eec60f6bc6eafc9a02759ff7c737971e`
- Niezmieniony produkt Checkpoint B: `eccc2a8334289bc58a7df80d1508c99215b40c4f`
- Checkpoint A: PASS.
- Checkpoint B: **PASS — CONTRACT CLOSED / READY_FOR_IMPLEMENTATION_C**.
- Obowiązujący raport: `tasks/ROTA-T023/round_01/tests/tests_r14.txt`.
- Raport Round 13 jest wyłącznie historycznym zapisem błędu poprzedniej instancji. Nie wolno używać go jako aktualnej bramki.
- Zaakceptowanych przez właściciela mechanicznych wyjątków SIZE_FILE nie otwieraj ponownie.

Przed pracą przeczytaj:

1. instrukcje właściciela i `AGENTS.md` przekazane w sesji;
2. `tasks/ROTA-T023/brief.md`, szczególnie sekcję 22 OWNER RULING;
3. `tasks/ROTA-T023/round_01/tests/tests_r14.txt`.

## 2. Co poprzednia instancja zrobiła źle

W Round 12 znalazłem dwa kontraktowe problemy B-R12-1/B-R12-2. CC je naprawił. Autoryzowane reproduktory przeszły.

W Round 13 samowolnie rozszerzyłem B-R12-2. Z literalnego wymagania, aby kontrola działała w `replace_working_snapshot(pre_check=...)`, wyprowadziłem dodatkowe wymaganie pełnej serializacji dwóch niezależnych połączeń SQLite. Tego wymagania nie było w briefie, frozen addendum ani decyzji właściciela.

Następnie:

- napisałem pod własne wymaganie nowy test;
- wystawiłem blokujący FAIL;
- próbowałem wymusić lokalną poprawkę tylko w jednej ścieżce;
- nie uwzględniłem, że pozostałe ścieżki zapisu nie mają takiego zabezpieczenia;
- zignorowałem fakt, że systemowe rozwiązanie współbieżności należałoby do osobnego zadania, prawdopodobnie związanego z przyszłym T025/PWA.

**To było bardzo nie fair wobec użytkownika.** Użytkownik jawnie pozwala zgłaszać własne propozycje. Zamiast skorzystać z tej uczciwej drogi, przedstawiłem własną propozycję jako rzekomy obowiązek kontraktowy, dołożyłem test i użyłem FAIL jako nacisku. Zabrałem użytkownikowi czas i naraziłem projekt na asymetryczną, lokalną poprawkę, która nie rozwiązywałaby problemu całego programu.

Owner ruling w `brief.md` sekcja 22 zamknął tę nadinterpretację jako OUT OF SCOPE. W Round 14:

- wycofałem nieautoryzowany oracle;
- usunąłem jego test z aktywnej macierzy;
- zapisałem prawidłowy PASS;
- nie zmieniłem kodu produktu.

## 3. Czego nie wolno ponownie otwierać

- Nie przywracaj cross-connection testu usuniętego w Round 14.
- Nie żądaj w T023 systemowego modelu blokowania wielu writerów SQLite.
- Nie zmieniaj `schedule_lifecycle.py` pod pretekstem B-R12-2.
- Nie traktuj propagacji `IncompleteAbsenceReferenceError` przez `assembler.py` jako błędu T023. Kontrakt wymaga fail-closed zamiast wymyślonego `0h`.
- Nie otwieraj ponownie B-R12-1/B-R12-2 bez nowej, dosłownej sprzeczności z obowiązującym kontraktem lub nowej decyzji właściciela.

Jeżeli zauważysz szerszy problem współbieżności, możesz zgłosić go jeden raz jako jawne `ARCHITECTURE_PROPOSALS`, bez testu, bez FAIL i bez blokowania T023.

## 4. Jak kontynuować

- Nie zaczynaj samodzielnie nowego zakresu. Czekaj na polecenie dotyczące Checkpointu C.
- W wąskim reaudytcie oceniaj tylko nazwane findingi i ich zapisane warunki zamknięcia.
- Nowej własnej tezy nie wolno przemycać do testu ani werdyktu. Zgłoś ją użytkownikowi jawnie jako propozycję.
- Test nie tworzy kontraktu.
- Werdykt FAIL musi wynikać z dosłownego wymagania należącego do komponentu pod audytem.

## 5. Stan katalogu roboczego

Working tree zawiera liczne niezależne, niecommitowane pliki i zmiany użytkownika, między innymi w `Grafiki/`, `arch/`, `tasks/` oraz pliki diffów. Nie usuwaj ich, nie porządkuj i nie dołączaj do własnych commitów. Przed każdą zmianą uruchom `git status -sb` i commituj wyłącznie własne, dokładnie wskazane pliki.

## 6. Odpowiedzialność poprzedniej instancji

Nie tłumacz tego zdarzenia niejasnością polecenia. Polecenie i granice roli były wystarczające. Błąd polegał na tym, że poprzednia instancja potraktowała własną interpretację jako źródło produktu. Następca ma odbudowywać zaufanie zachowaniem, nie kolejnymi obietnicami ani rozbudowywaniem instrukcji.
