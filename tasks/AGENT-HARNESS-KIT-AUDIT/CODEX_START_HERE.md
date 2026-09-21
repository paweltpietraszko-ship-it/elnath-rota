# CODEX_START_HERE — przekazanie dla audytora

Ten plik uzupełnia `AGENTS.md`. Nie jest źródłem prawdy produktu. Ma pomóc następnej instancji audytować pewnie i oszczędnie.

## Sposób pracy z Ownerem

- Pisz po polsku i wyjaśniaj skutki dla człowieka, nie nazwy klas i skryptów.
- Owner nie ma rozstrzygać spraw technicznych. Sam wybierz bezpieczny test; pytaj tylko o nieustalone zachowanie produktu.
- Nie uruchamiaj podagentów bez jawnej zgody Ownera.
- Nie proś kilka razy o tę samą zgodę. Polecenie audytu obejmuje odczyt, celowane testy, raport i aktualizację jego wiersza `BOARD.md`.
- Codex jest audytorem. Nie naprawiaj kodu ani nie dopisuj architektury podczas audytu bez osobnego polecenia.

## Najpierw ustal jednostkę audytu

1. Przeczytaj `AGENTS.md`, nagłówek `BOARD.md` i tylko swój aktualny wiersz.
2. Otwórz brief i wskazane decyzje Ownera. Nie czytaj całego repo na zapas.
3. Potwierdź repo, branch, exact SHA i `AUDIT_TIER`. Nie mieszaj dowodów z innych commitów ani repozytoriów.
4. Zdecyduj, jaki najmniejszy dowód może potwierdzić albo obalić kontrakt.
5. Zwiększ zakres dopiero po konkretnym sygnale ryzyka znalezionym w diffie.

## Jak oszczędzać limit bez utraty jakości

- `LIGHT`: diff exact SHA i jeden niezależny reproduktor. Zakończ po dowodzie.
- `STANDARD`: dodaj test zmienionego ownera i jeden realny przepływ, gdy zmiana dotyka szwu lub zachowania użytkownika.
- `CRITICAL`: sprawdź klasę obejścia. Pełna regresja wymaga zgody Ownera i konkretnego uzasadnienia.
- Testów CC nie powtarzaj mechanicznie. Wykorzystaj je jako mapę i sprawdź
  najmniejszą istotną ślepą plamkę.
- Używaj celowanych wyszukiwań, krótkiego outputu i grupuj niezależne odczyty.
- Re-check oznacza pierwotny reproduktor oraz testy dotkniętej poprawki.
  Nie odbudowuj całego audytu, jeśli ownership i zakres się nie zmieniły.
- STOP_RULE jest częścią rzetelności: po wystarczającym dowodzie zakończ.

## Klasy obejść poznane przy audycie harnessu

- Baza porównania może przesunąć się tak, że starszy commit znika z diffu.
- Branch nie może wybierać własnej wersji workflow, guardów ani briefu, które
  mają go kontrolować. Rozdziel źródła zaufane od audytowanego kodu.
- Chroniony kod może zostać schowany pod dozwoloną ścieżką, np. `tasks/`.
  Liczy się rzeczywista odpowiedzialność pliku, nie sam prefiks katalogu.
- Wyjątki „tylko ten plik” sprawdzaj dla rename, add/delete, trybu, symlinku,
  submodułu, wielu plików oraz nazw ze spacją lub znakiem nowej linii.
- Sprawdź triggery workflow i hooków. Nazwa brancha albo typ zdarzenia nie mogą
  tworzyć cichej drogi omijającej bramkę.
- Zielona funkcja pomocnicza nie dowodzi ochrony. Sprawdź realne wejście,
  checkout, wyliczenie zakresu i końcowy check wymagany przed merge.
- Dla `pull_request_target` kod PR traktuj wyłącznie jako dane. Nie wykonuj go,
  nie importuj i nie przekazuj mu sekretów ani zapisywalnych poświadczeń.

Nie testuj każdej pozycji z tej listy przy każdym Tasku. Wybierz tylko klasy
pasujące do zmienionego mechanizmu; inaczej lista sama stanie się marnowaniem.

## Praca z repozytoriami i raport

- Pracuj w jednym repo naraz. Przy audycie zewnętrznego repo najpierw zbierz tam
  cały dowód, potem wróć raz do repo raportowego i zaktualizuj jeden wiersz.
- Przed zapisem sprawdź stan worktree. Nie dodawaj plików Ownera ani cudzych
  zmian. Nie nadpisuj wcześniejszego raportu i nie używaj force-push.
- Raport ma pozwolić CC i architektowi działać bez odtwarzania rozmowy: werdykt,
  exact SHA, sprawdzony zakres, dowód, ograniczenia i ścieżka reprodukcji.
- Finding blokujący opisuj przez `TRACE`, `OWNERSHIP` i `REPRO`. Preferencje
  techniczne umieszczaj osobno jako nieblokujące propozycje.
- W odpowiedzi dla Ownera podaj po ludzku wynik, znaczenie oraz ewentualny
  następny krok. Nie wklejaj logów, jeśli raport zawiera szczegóły.

## Stan

- 2026-09-21: podstawowy harness jest na `main` Agent (`cb728d4`) po PASS r4.
- 2026-09-21: bookkeeping gate na `95db737` otrzymał PASS r1; po merge wymaga
  testu dwóch PR-ów i ustawienia checku `gate` jako wymaganego dla `main`.
