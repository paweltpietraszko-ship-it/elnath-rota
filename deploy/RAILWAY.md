# Wdrożenie na Railway (ROTA-RAILWAY-DEPLOY)

Jeden serwis Railway, zbudowany z `Dockerfile` w korzeniu repo. Kontener
serwuje jednocześnie API i zbudowany frontend — przeglądarka nie robi
żadnych żądań cross-origin w produkcji. **Od 2026-10-16 konfiguracja serwisu
żyje w `.railway/railway.ts` (Infrastructure as Code)**, w tym builder
`DOCKERFILE` ustawiony na stałe na serwisie; dawny `railway.json` usunięto
(Railway wycofuje go 2026-12-01). Bez jawnego buildera serwis, który powstał
zanim Dockerfile istniał w repo, zostaje przy Railpacku i cicho ignoruje
Dockerfile — dokładnie to się stało przy pierwszym prawdziwym deployu
2026-09-17.

## 1. Utwórz serwis

W Railway: **New Project → Deploy from GitHub repo** → wybierz to repo.
Nowy serwis: po utworzeniu ustaw builder przez `.railway/railway.ts`
(`railway config plan` → `railway config apply`) albo w Settings → Build
wybierz "Dockerfile", nie "Railpack".

## 2. Podłącz trwały dysk (Volume) — zanim ktokolwiek się zaloguje

Bez tego kroku **każdy redeploy kasuje wszystkie konta i wszystkie
grafiki** (bazy to pliki SQLite na dysku kontenera, a dysk kontenera jest
tymczasowy).

Volume NIE jest zakładką w ustawieniach serwisu — zakłada się go z poziomu
canvasu całego projektu:

1. Kliknij prawym przyciskiem na **pusty obszar canvasu projektu** (tam,
   gdzie widać kafelki serwisów) → wybierz opcję dodania Volume (albo
   `Ctrl+K`/`Cmd+K` → paleta poleceń → wpisz "volume").
2. Railway zapyta, do którego serwisu podłączyć — wybierz serwis Rota.
3. W ustawieniach nowego Volume ustaw **mount path**: `/data`.

## 3. Zmienne środowiskowe

Ustaw w **Settings → Variables**:

| Zmienna | Wartość | Po co |
|---|---|---|
| `ROTA_CENTRAL_KEK` | 64 znaki hex (32 bajty) — patrz niżej | włącza tryb CENTRAL_SERVICE (logowanie, izolacja kont) i szyfruje dane w bazach |
| `ROTA_AUTH_SECRET` | dowolny losowy sekret — patrz niżej | podpisuje sesje logowania (JWT) |
| `ROTA_DB_PATH` | `/data/rota_dev.db` | główna baza (obiekt bez konta = brak, w CENTRAL_SERVICE każde konto ma swoją bazę w `ROTA_ACCOUNTS_DB_DIR`) |
| `ROTA_AUTH_DB_PATH` | `/data/rota_auth.db` | baza kont/logowań |
| `ROTA_ACCOUNTS_DB_DIR` | `/data/accounts` | katalog z bazą każdego konta |
| `ROTA_ALLOWED_ORIGINS` | `https://<twoj-adres>.up.railway.app` | pozwala przeglądarce łączyć się z API (ustaw PO pierwszym deployu, gdy już znasz adres) |

**Strefa czasowa (ROTA-CLOUD-REVIEW-FIXES F5):** `Dockerfile` ustawia
`TZ=Europe/Warsaw` i instaluje `tzdata`, bo cała Rota liczy w polskim czasie
ściennym (ochrona rozpoczętej służby, domyślne „Obowiązuje od"). **Nie
ustawiaj zmiennej `TZ` w panelu Railway** — nadpisałaby tę z obrazu.
Sprawdzenie: `railway variables --kv | grep -i "^TZ="` ma nic nie zwracać;
po wdrożeniu `railway ssh date` (albo podgląd czasu w logach) pokazuje czas
polski (CET zimą, CEST latem).

**Nigdy nie wpisuj tych wartości do repo/gita** — tylko w panelu Railway.
Wygeneruj każdy sekret osobno lokalnie:

```
# ROTA_CENTRAL_KEK -- musi być DOKŁADNIE 64 znaki hex (32 bajty), inaczej
# rota/persistence/pii_crypto.py odrzuci go przy starcie (KeyProtectionUnavailable):
python -c "import secrets; print(secrets.token_hex(32))"

# ROTA_AUTH_SECRET -- format dowolny, wystarczy losowy ciąg:
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 4. Pierwszy deploy

Railway zbuduje i uruchomi kontener automatycznie po pushu na `main`
(albo ręcznie z panelu). Health check: `https://<adres>/api/health` →
`{"status": "ok"}`.

## 5. Załóż konta (dopiero po działającym deployu + Volume)

Z lokalnego repo, z ustawionymi tymi samymi zmiennymi co na Railway
(albo przez `railway run`, jeśli masz zainstalowane Railway CLI i
podłączony projekt):

```
railway run python -m api.provision_account create <email> <haslo> <coordinator_id> <plik_bazy>
```

`plik_bazy` musi być unikalny dla każdego konta (np. `uzytkownik_001.db`)
— to granica izolacji między kontami, patrz `api/provision_account.py`.

## Migracja z railway.json (ROTA-CLOUD-REVIEW-FIXES R, termin: przed 2026-12-01)

Railway wycofuje `railway.json` (Config as Code) — działa do **2026-12-01**. Następca:
`.railway/railway.ts` (Infrastructure as Code, opis w `.railway/README.md`).

**Stan sprawdzony 2026-10-16 (`railway config pull --json`, bez wartości sekretów):**
serwis `elnath-rota`, repo `paweltpietraszko-ship-it/elnath-rota` gałąź `main`, dysk
`elnath-rota-volume` pod `/data` (5000 MB), region `us-east4-eqdc4a`, 1 replika, domena
`elnath-rota-production.up.railway.app`, 6 zmiennych `ROTA_*`. **Builder samego serwisu to
RAILPACK** — Dockerfile wymusza dziś wyłącznie `railway.json`.

**Pułapki znalezione podglądem (`railway config plan`, nic nie zastosowano):**
1. Plik z `railway config migrate` zostawia Dockerfile tylko jako komentarz → po wyłączeniu
   `railway.json` serwis budowałby się Railpackiem (bez czcionek PDF, strefy czasu i frontu).
2. Ten sam plik pomija zmienne, dysk i repo → plan: **usuń 6 zmiennych (w tym
   `ROTA_CENTRAL_KEK` — klucz szyfrujący dane osobowe), odepnij `/data`, odepnij repo**.
   Pominięte pole = usuń, nie „zostaw”.

Gotowy `.railway/railway.ts` (import `config pull` + jawny Dockerfile) daje plan:
`0 to add, 1 to change, 0 to destroy` — tylko `build.builder → DOCKERFILE`.

**Wykonane 2026-10-16 (zgoda Ownera: „migracje trzeba zrobić już”):**
1. `railway config plan` → `0 to add, 1 to change, 0 to destroy` (tylko `build.builder → DOCKERFILE`).
2. `railway config apply --yes` (bez `--confirm-destructive`) → zastosowane; samoczynny redeploy
   zbudował się z Dockerfile, `/api/health` → ok; ponowny plan: „already up to date”.
3. Wyczyszczono ustawienie Config as Code na serwisie (`railway config migrate --apply --force`
   — nadpisany plik lokalny od razu przywrócony z gita, plan nadal „up to date”).
4. Usunięto `railway.json` z repo.

**Zmiany konfiguracji od teraz:** edycja `.railway/railway.ts` → `railway config plan` (każda linia
„Delete variable”, zmiana `volumeAttachments` albo `source` = STOP) → zgoda Ownera →
`railway config apply --yes`. Push na `main` niczego tu nie stosuje. Nigdy nie generuj tego pliku
od nowa przez `railway config migrate` — pomija zmienne/dysk/repo i plan usunąłby sekrety.

## Co NIE jest jeszcze zrobione tym Taskiem

- Panel w UI do pobrania szablonu/dodatku Excela i wygenerowania klucza
  API (dziś tylko CLI) — osobny task.
- Ekran awaryjny PWA na telefon — osobny task.
- Samo założenie 10 kont — do zrobienia po tym, jak ten deploy zadziała.
