# Instalacja dodatku Elnath Rota (jednorazowo, na komputerze użytkownika)

Ten dokument opisuje jednorazową instalację dodatku, wykonywaną przez
zaufaną osobę (administratora), nie przez samego użytkownika przy
każdym uruchomieniu.

## 1. Wymagania

- Klasyczny, desktopowy Microsoft Excel (nie Excel Online).
- Dostęp do internetu na tym komputerze.
- Adres uruchomionej usługi Rota (np. `https://twoja-rota.up.railway.app/api`).
- Klucz dostępu wydany przez administratora Roty
  (`python -m api.provision_account issue-api-key <email>`).

## 2. Instalacja dodatku

1. Skopiuj `ELNATH_ROTA_ADDIN.xlam` na komputer użytkownika, np. do
   `%APPDATA%\Microsoft\AddIns\`.
2. W Excelu: **Plik → Opcje → Dodatki → Zarządzaj: Dodatki programu
   Excel → Przejdź…**.
3. **Przeglądaj…**, wskaż skopiowany plik `ELNATH_ROTA_ADDIN.xlam`,
   zaznacz go na liście i zatwierdź.
4. Dodatek jest teraz załadowany przy każdym uruchomieniu Excela —
   ten krok wykonuje się raz, nie przy każdym pliku grafiku.

## 3. Konfiguracja adresu usługi i klucza dostępu

1. W dowolnym otwartym skoroszycie: **Deweloper → Makra** (albo
   `Alt+F8`), wybierz `ElnathRotaAddin.RotaConfigure`, **Uruchom**.
2. Wpisz adres usługi Rota, potem klucz dostępu wydany przez
   administratora.
3. Dane są zapisywane lokalnie dla tego użytkownika Windows (rejestr,
   nigdy w pliku `.xlsx`) — użytkownik nie wpisuje ich ponownie przy
   kolejnych uruchomieniach.

## 4. Przygotowanie pliku grafiku

1. Rozdaj użytkownikowi jego kopię `ELNATH_ROTA_TEMPLATE.xlsx`
   (`excel/ELNATH_ROTA_TEMPLATE.xlsx`) — plik bez makr, zgodny z
   `TEMPLATE_CONTRACT.md`.
2. Na arkuszu `Panel` wpisz raz `Site ID` obiektu (widoczny w Rota) —
   to jedyne pole techniczne, które konfiguruje administrator, nie
   użytkownik.
3. Dodaj przyciski akcji (Deweloper → Wstaw → Przycisk formularza) i
   przypisz im makra:
   - „Przelicz” → `ElnathRotaAddin.RotaPlan`
   - „Pokaż inny wariant” → `ElnathRotaAddin.RotaShowOtherVariant`
   - „Użyj tego grafiku” → `ElnathRotaAddin.RotaUseSelectedCandidate`
   - „Odśwież grafik” → `ElnathRotaAddin.RotaRefreshSchedule`

## 5. Procedura smoke-testu (manualna, po instalacji)

1. Otwórz przygotowany plik grafiku.
2. Uzupełnij cel godzinowy w tabeli `Pracownicy` dla realnych
   pracowników (albo pozostaw puste, jeśli cele są już ustawione w
   samej Rota).
3. Kliknij „Przelicz”. Oczekiwany wynik: komunikat o gotowych
   propozycjach, tabela `Kandydaci` wypełniona wierszami.
4. Skopiuj `candidate_id` wybranego kandydata do komórki wyboru na
   arkuszu `Panel`, kliknij „Użyj tego grafiku”. Oczekiwany wynik:
   komunikat o akceptacji, tabela `Grafik` wypełniona wynikiem.
5. Jeśli którykolwiek krok pokaże błąd — treść komunikatu zawsze mówi
   wprost, co jest nie tak i co zrobić dalej (nigdy samego kodu
   technicznego jako jedynej treści).

To jest jedyny wymagany dowód instalacyjny — automatyzacja całego GUI
Office w CI nie jest wymagana (brief.md sekcja 10).

## 6. Rozwiązywanie problemów

- **„Dodatek nie jest jeszcze skonfigurowany”** — uruchom ponownie
  `RotaConfigure` (krok 3).
- **„Brak połączenia z usługą Rota”** — sprawdź internet i adres
  usługi.
- **„Nieprawidłowy lub unieważniony klucz dostępu”** — poproś
  administratora o nowy klucz (stary mógł zostać unieważniony).
