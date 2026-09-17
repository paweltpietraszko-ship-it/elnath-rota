# Wdrożenie na Railway (ROTA-RAILWAY-DEPLOY)

Jeden serwis Railway, zbudowany z `Dockerfile` w korzeniu repo. Kontener
serwuje jednocześnie API i zbudowany frontend — przeglądarka nie robi
żadnych żądań cross-origin w produkcji. `railway.json` w korzeniu repo
wymusza builder `DOCKERFILE` -- **bez niego, jeśli serwis powstał zanim
Dockerfile istniał w repo, Railway zostaje przy raz wybranym Railpackiem
i cicho ignoruje Dockerfile nawet po jego dodaniu** (dokładnie to się
stało przy pierwszym prawdziwym deployu 2026-09-17: builder pozostał na
`RAILPACK` mimo `Dockerfile` w repo, aż do dodania tego pliku).

## 1. Utwórz serwis

W Railway: **New Project → Deploy from GitHub repo** → wybierz to repo.
Dzięki `railway.json` serwis od razu zbuduje się z `Dockerfile`. Jeśli
zakładasz serwis w istniejącym już projekcie, sprawdź w jego Settings →
Build, że builder to faktycznie "Dockerfile", nie "Railpack".

## 2. Podłącz trwały dysk (Volume) — zanim ktokolwiek się zaloguje

Bez tego kroku **każdy redeploy kasuje wszystkie konta i wszystkie
grafiki** (bazy to pliki SQLite na dysku kontenera, a dysk kontenera jest
tymczasowy).

W zakładce serwisu: **Settings → Volumes → New Volume**, mount path:
`/data`.

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

## Co NIE jest jeszcze zrobione tym Taskiem

- Panel w UI do pobrania szablonu/dodatku Excela i wygenerowania klucza
  API (dziś tylko CLI) — osobny task.
- Ekran awaryjny PWA na telefon — osobny task.
- Samo założenie 10 kont — do zrobienia po tym, jak ten deploy zadziała.
