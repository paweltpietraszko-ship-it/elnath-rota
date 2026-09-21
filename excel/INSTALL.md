# Instalacja dodatku Elnath Rota — dokument dla ADMINISTRATORA

Ten dokument jest dla administratora Roty (budowa instalatora, wydawanie
kluczy, rozwiązywanie problemów). Użytkownik końcowy dostaje tylko dwa
pliki: `ElnathRotaSetup.exe` i osobną, krótką
[`INSTRUKCJA_DLA_UZYTKOWNIKA.md`](INSTRUKCJA_DLA_UZYTKOWNIKA.md) — bez
żadnego żargonu technicznego. Nie wysyłaj mu tego dokumentu.

## 1. Wymagania

- Klasyczny, desktopowy Microsoft Excel (nie Excel Online).
- Dostęp do internetu na tym komputerze.
- Klucz dostępu wydany przez administratora Roty
  (`python -m api.provision_account issue-api-key <email>`) — administrator
  przesyła go użytkownikowi razem z linkiem do instalatora, np. mailem.

## 2. Instalacja (przekaż użytkownikowi `INSTRUKCJA_DLA_UZYTKOWNIKA.md`)

Skrót tego, co widzi użytkownik: pobiera `ElnathRotaSetup.exe`, uruchamia,
wkleja klucz dostępu, klika Dalej/Zainstaluj/Zakończ. Bez okna Dodatki,
bez ręcznego uruchamiania makra.

Instalator kopiuje `ELNATH_ROTA_ADDIN.xlam` do `%APPDATA%\Microsoft\Excel\
XLSTART` — to domyślnie zaufane miejsce startowe Excela, więc dodatek
ładuje się bez monitu o zabezpieczeniach i bez ręcznej rejestracji. Klucz
dostępu i adres usługi zapisuje w tym samym miejscu w rejestrze, którego
używa makro `RotaConfigure` — jakby użytkownik uruchomił je sam.

**Zaflagowane, nie zrobione — decyzja należy do Ciebie:** `ElnathRotaSetup.exe`
nie jest podpisany cyfrowo, więc Windows SmartScreen pokaże niebieskie
ostrzeżenie „Windows chronił Twój komputer” przy pierwszym uruchomieniu
(`INSTRUKCJA_DLA_UZYTKOWNIKA.md` tłumaczy to jako normalny krok). Żeby to
ostrzeżenie zniknęło całkowicie, trzeba by kupić certyfikat do podpisywania
kodu (koszt, decyzja zakupowa) — nie robię tego bez Twojej zgody, na razie
zostawiam jako świadomy, udokumentowany kompromis.

### Jak zbudować `ElnathRotaSetup.exe`

Źródło instalatora: `excel/installer/ElnathRotaSetup.nsi`, zbudowane
narzędziem [NSIS](https://nsis.sourceforge.io/) (darmowe, także
komercyjnie — licencja zlib/libpng, w odróżnieniu od Inno Setup 6.5+,
które od pewnej wersji wymaga płatnej licencji komercyjnej). Instalacja
NSIS: `winget install NSIS.NSIS` albo strona projektu. Budowa:

```
makensis excel\installer\ElnathRotaSetup.nsi
```

Efekt: `excel\installer\ElnathRotaSetup.exe` — jeden plik do przesłania
użytkownikowi. Jeśli adres usługi Rota kiedyś się zmieni, edytuj stałą
`SERVICE_URL_DEFAULT` na górze `.nsi` i zbuduj ponownie.

## 3. Przygotowanie pliku grafiku

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

## 4. Procedura smoke-testu (manualna, po instalacji)

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

## 5. Rozwiązywanie problemów

- **„Dodatek nie jest jeszcze skonfigurowany”** — instalator zwykle się
  tym zajął; jeśli mimo to się pojawia, uruchom ponownie instalator
  (wklej klucz jeszcze raz), albo ręcznie: **Deweloper → Makra** (`Alt+F8`)
  → `ElnathRotaAddin.RotaConfigure` → **Uruchom**.
- **„Brak połączenia z usługą Rota”** — sprawdź internet i adres
  usługi.
- **„Nieprawidłowy lub unieważniony klucz dostępu”** — poproś
  administratora o nowy klucz (stary mógł zostać unieważniony).
