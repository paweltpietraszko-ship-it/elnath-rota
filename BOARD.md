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
| ROTA-TARGET-HOURS-CEILING-NOT-BULLSEYE | Architekt | CC | `task/ROTA-TARGET-EQUITY-DIAGNOSIS` | decisive finding `c411bcf`; prior snapshot `900ef16` | READY_FOR_CODEX | **OWNER: chirurgicznie przywrócić prawidłowe zachowanie OCHRONA; bez globalnej zmiany solvera i bez cofania napraw ORDINARY.** Diagnoza potwierdziła na identycznych danych Royal w starym kodzie: wektor targetów NIEKOMPLETNY → stara ścieżka equal-split 120/120/120/120/132/132, komplet po „Ustaw wszystkim” → TARGET-01 48/60/144/156/168/168. Gate `require_complete_target_hours` z 15.09, zaprojektowany dla ORDINARY, zablokował OCHRONA bez targetów, a usunięcie fallbacku odebrało jej dawną ścieżkę; samo cofnięcie gate NIE wystarczy, bo funkcja fallback została usunięta i Royal ma już komplet targetów. **Polecenie dla CC: przygotuj minimalny brief chirurgicznego fixu z rozdzieleniem reżimów, nie implementuj przed precheckiem.** W OCHRONA przywróć możliwość PLAN/REPLAN bez kompletnego wektora targetów oraz równomierny podział dostępnych godzin także wtedy, gdy targety są wpisane (przycisk „Ustaw wszystkim” nie może pogarszać sprawiedliwości). Zachowaj rytm D/N, wszystkie HARD, prawidłowe uwzględnienie istniejących absencji/delegacji i już wykonanej pracy; nie przywracaj bez zmian starego absence-blind fallbacku ani nie usuwaj zapisanych targetów. W ORDINARY bez zmian: gate kompletności, `_effective_targets`, obecny algorytm i wyniki. Zidentyfikuj najmniejszy istniejący owner/fragment kodu i dokładny zakres zmian; nie przenoś ponownie reguły z jednego reżimu na drugi. Kryteria akceptacji do briefu: (1) Royal z kompletnymi targetami zachowuje prawie równy przydział jak historyczny fallback, bez regresji rytmu D/N lub budżetu czasu; (2) drugi realny OCHRONA bez targetów ponownie może PLAN/REPLAN; (3) OCHRONA z urlopem/delegacją nie dostaje pełnej pracy oprócz godzin nieobecności, zgodnie z efektywnym limitem; (4) ORDINARY bez targetów nadal blokuje, z kompletnymi działa jak dotąd; (5) testy PLAN, REPLAN i precheck, HARD pass i czas. Nie deklaruj, że samo odtworzenie historii jest już bezpiecznym kodem: legacy fallback ignorował absencje, a eksperyment pos-only obniżył rytm 23→11 i trwał 90s. Zapisz krótki brief na branchu zadania, przekaż przez BOARD Architektowi do przeglądu i niezależnego prechecku Antigravity/Codex przed implementacją; żadnego merge bez decyzji OWNERA. |
