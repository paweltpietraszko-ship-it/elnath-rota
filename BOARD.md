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
| ROTA-T056 | Codex | Owner | `main` (brief only; implementation HOLD) | `e4260555645c5c00a3829bacf28bcc1233422f47` (audited brief), audit `153490ea0487108e5a88d5703a9db4ec45ee9d0a` | OWNER_DECISION_NEEDED | **OWNER_CORRECTED #1 (2026-09-05):** w legendzie PDF drukować tylko kody faktycznie użyte w danym wydruku, jeśli mieszczą się w zaakceptowanym układzie. Jeżeli użytych oznaczeń nie da się czytelnie zmieścić, drukować drugą stronę legendy — pracownik musi znać wszystkie zastosowane oznaczenia. Brak obcinania, ukrywania lub nieczytelnego zmniejszania. Wymaga ujęcia w poprawionym briefie i REAL PDF GATE dla wariantu jednostronicowego oraz dwustronicowego. **Decyzja #2 nadal otwarta:** Assignment przechowuje godziny, ale nie etykietę D1/D6. Przykład: D6=10:00–18:00 jest poprawne, po czym globalne D1 zostaje zmienione na 10:00–18:00; eksport nie potrafi wtedy rozpoznać, czy zapis 10:00–18:00 oznacza D1 czy D6. OWNER ma zdecydować, czy drugi zapis tworzący taką kolizję ma być natychmiast odrzucony z zachowaniem danych (rekomendacja), czy zapis ma być dozwolony, a eksport danego miesiąca blokowany do poprawy konfiguracji. Raport R1: `tasks/ROTA-T056/round_01/tests/tests_r1.txt`; wszystkie korekty techniczne z raportu pozostają aktualne. Kod produktu nadal wstrzymany. |
