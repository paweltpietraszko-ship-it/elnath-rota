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
| ROTA-TARGET-HOURS-CEILING-NOT-BULLSEYE | Architekt | CC | `task/ROTA-TARGET-EQUITY-DIAGNOSIS` | diagnoza `3c17782`; scope finding `55cfdc0` | READY_FOR_CODEX | **OWNER: wstrzymaj globalne zmiany wag/TARGET-01. Najpierw rozdziel diagnozę i kontrakt OCHRONA vs ORDINARY.** Nowe `regime_scope_finding.md` wykazuje, że gate `require_complete_target_hours` powstał po repro na FF (ORDINARY), został włączony dla obu reżimów i blokuje aktywny obiekt OCHRONA bez targetów. To uzasadnia naprawę zakresu gate, ale SAMO NIE DOWODZI, że wyłączenie gate przywróci sprawiedliwy podział: stary `add_equal_split_fairness` usunięto, a Royal ma komplet targetów. Eksperyment pos-only Royal 144→12h jednocześnie obniżył D/N 23→11 i trwał 90s; nie wdrażaj go. **Ważna korekta analizy:** przy pełnym pokryciu i braku przekroczeń suma `neg` jest stała, więc sam ten składnik nie faworyzuje nierówności; wyniki pos-only mogą wynikać z degeneracji celu, innych SOFT, wyszukiwania/gap, a nie udowodnionego indywidualnego 'dobijania do celu'. CC: wykonaj wąską, read-only analizę faktycznych ścieżek dla OCHRONA z niekompletnym i kompletnym target vector oraz ORDINARY (gate, wcześniejszy fallback, bieżący equity, `_effective_targets`, absencje/delegacje). Ustal na konkretnych testach, jakie zachowanie OCHRONA działało PRZED 15.09, co dokładnie utracono, i czy można odtworzyć je bez przywrócenia absence-blind fallback; uwzględnij Royal (komplet targetów) i drugi obiekt OCHRONA (brak targetów), oddziel dostępne dowody od hipotez. Nie zmieniaj kodu produkcyjnego, reguł HARD, wag ani granic reżimów na własną rękę. Wynik: krótki raport wskazujący minimalne reżimowo rozdzielone zasady i testy akceptacyjne, bez prywatnych danych i bez modyfikacji baz; przekazanie przez BOARD do Architekta przed briefem/fixem/merge. **KOREKTA CC tego samego dnia (OWNER złapał błąd faktograficzny):** teza "OCHRONA polegała na absence-blind fallbacku" jest FAŁSZYWA — `_effective_targets` (target - absence_hours) istnieje od **22.08** (`5ae3f48`), czyli przed T032 (25.08), przed T041/fallbackiem (29.08) i przed jakąkolwiek pracą nad Ordinary (~8.09+). Ochrona nigdy nie ignorowała absencji w ścieżce TARGET-01 — wycofuję tę część `regime_scope_finding.md`. Mocniejszy, wcześniejszy i reżimowo-neutralny kandydat: TARGET-01 dostało "matematycznie bezwzględny priorytet" nad sprawiedliwością **25.08** (`9663883`), trzy tygodnie przed Ordinary. Próba bezpośredniego odtworzenia Royal na solverze sprzed tej zmiany (`pre_t032_snapshot/`, commit `fbe8b89`) NIE URUCHAMIA SIĘ na dzisiejszych danych (`ValueError: too many values to unpack` — miesiąc późniejszych zmian rozjechał sygnatury) — zgłaszam to jako lukę dowodową, nie obchodzę jej na skróty. Uczciwy stan: luka reżimowa (gate uogólniony z Ordinary) jest realna i osobno warta naprawy, ale NIE jest ustalona jako przyczyna rozstrzału na Royal — Royal ma komplet targetów i faza-1 już dowiodła bajt-identyczności starego/nowego solvera na nim, więc zmiana z 15.09 nic tam nie zmieniła. Najbardziej prawdopodobna, wciąż niepotwierdzona bezpośrednim odtworzeniem przyczyna to zmiana z 25.08, niezwiązana z reżimem. Pełna korekta: `tasks/ROTA-TARGET-EQUITY-DIAGNOSIS/round_01/tests/regime_scope_finding.md` (sekcja CORRECTION), commit `26c1036`. |
