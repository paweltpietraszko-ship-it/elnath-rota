# Instalacja dodatku Elnath Rota — dokument dla ADMINISTRATORA

Ten dokument jest dla administratora Roty (budowa instalatora, wydawanie
kluczy, rozwiązywanie problemów). Użytkownik końcowy dostaje tylko dwa
pliki: `ElnathRotaSetup.exe` i osobną, krótką
[`INSTRUKCJA_DLA_UZYTKOWNIKA.md`](INSTRUKCJA_DLA_UZYTKOWNIKA.md) — bez
żadnego żargonu technicznego. Nie wysyłaj mu tego dokumentu.

## 1. Wymagania

- Klasyczny, desktopowy Microsoft Excel (nie Excel Online).
- Dostęp do internetu na tym komputerze.
- Konto w Rota (login/hasło) — to jest jedyny wymagany "dostęp"; klucz i
  instalator użytkownik pobiera sam z panelu **Excel** w aplikacji.

**Klient bez własnego administratora IT?** Nic się nie zmienia — panel
Excel (ROTA-EXCEL-UI-PANEL, `api/routers/excel_downloads.py` +
`Workspace.tsx`) jest samoobsługowy dla każdego zalogowanego
koordynatora: sam generuje klucz, sam pobiera instalator, sam czyta
instrukcję (`INSTRUKCJA_DLA_UZYTKOWNIKA.md`, wyświetlaną w panelu). Nikt
u klienta nie musi być "administratorem" — jedyny prawdziwy administrator
w tym systemie to Ty (operator Roty): to Ty budujesz `.exe` i wgrywasz go
do repo, ale to jednorazowa/rzadka czynność, nie coś, co robisz per
klient. CLI (`python -m api.provision_account issue-api-key <email>`)
zostaje tylko jako narzędzie awaryjne (np. gdy ktoś nie ma jeszcze konta
w Rota w ogóle, albo trzeba unieważnić klucz — `revoke-api-key` nie ma
odpowiednika w panelu).

## 2. Instalacja (użytkownik robi to sam, z panelu Excel w Rota)

Panel Excel w aplikacji (widoczny tylko dla `CENTRAL_SERVICE`) ma 3
przyciski w kolejności użycia: **„1. Wygeneruj klucz dostępu”**, **„2.
Pobierz instalator”**, **„Instrukcja instalacji”** (renderuje
`INSTRUKCJA_DLA_UZYTKOWNIKA.md` na żywo — `GET /api/excel/install-guide`).
Osobne przyciski „Pobierz sam szablon”/„Pobierz sam dodatek” zostały —
przydatne, gdy ktoś potrzebuje świeżej kopii samego szablonu bez
przechodzenia całej instalacji ponownie.

Skrót tego, co widzi użytkownik: generuje klucz, pobiera
`ElnathRotaSetup.exe` (serwowany przez `POST /api/excel/installer` z
`excel/installer/ElnathRotaSetup.exe`), uruchamia, wkleja klucz dostępu,
klika Dalej/Zainstaluj/Zakończ. Bez okna Dodatki, bez ręcznego
uruchamiania makra, bez proszenia kogokolwiek o cokolwiek.

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

Efekt: `excel\installer\ElnathRotaSetup.exe` — commituj go do repo pod
tą samą ścieżką (tak jak `ELNATH_ROTA_ADDIN.xlam`/`ELNATH_ROTA_TEMPLATE.
xlsx` już są), panel serwuje go bezpośrednio z dysku, nic więcej nie
trzeba wdrażać. **Zbuduj i podmień ponownie za każdym razem, gdy zmienia
się** `ELNATH_ROTA_ADDIN.xlam`, `ELNATH_ROTA_TEMPLATE.xlsx` albo sam
`.nsi` — instalator ma te pliki wbudowane w środku, stary `.exe` po
takiej zmianie instalowałby nieaktualną wersję. Jeśli adres usługi Rota
kiedyś się zmieni, edytuj stałą `SERVICE_URL_DEFAULT` na górze `.nsi`.

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
- **„Nieprawidłowy lub unieważniony klucz dostępu”** — użytkownik
  wygeneruje sobie nowy klucz sam w panelu Excel (stary przestaje
  działać po wygenerowaniu nowego). Jeśli konieczne jest wymuszone
  unieważnienie starego klucza bez czekania na to — to jedyny krok, do
  którego nadal potrzebna jest Twoja interwencja: `python -m
  api.provision_account revoke-api-key <key_id>`.
