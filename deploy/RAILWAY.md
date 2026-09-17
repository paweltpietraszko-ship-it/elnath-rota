# Wdrożenie na Railway (ROTA-RAILWAY-DEPLOY)

Jeden serwis Railway, zbudowany z `Dockerfile` w korzeniu repo (Railway
wykrywa go automatycznie). Kontener serwuje jednocześnie API i zbudowany
frontend — przeglądarka nie robi żadnych żądań cross-origin w produkcji.

## 1. Utwórz serwis

W Railway: **New Project → Deploy from GitHub repo** → wybierz to repo.
Railway samo znajdzie `Dockerfile` i zbuduje kontener. Nic więcej nie
trzeba klikać w ustawieniach builda.

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
| `ROTA_CENTRAL_KEK` | wygeneruj sam (patrz niżej) | włącza tryb CENTRAL_SERVICE (logowanie, izolacja kont) i szyfruje dane w bazach |
| `ROTA_AUTH_SECRET` | wygeneruj sam (patrz niżej) | podpisuje sesje logowania (JWT) |
| `ROTA_DB_PATH` | `/data/rota_dev.db` | główna baza (obiekt bez konta = brak, w CENTRAL_SERVICE każde konto ma swoją bazę w `ROTA_ACCOUNTS_DB_DIR`) |
| `ROTA_AUTH_DB_PATH` | `/data/rota_auth.db` | baza kont/logowań |
| `ROTA_ACCOUNTS_DB_DIR` | `/data/accounts` | katalog z bazą każdego konta |
| `ROTA_ALLOWED_ORIGINS` | `https://<twoj-adres>.up.railway.app` | pozwala przeglądarce łączyć się z API (ustaw PO pierwszym deployu, gdy już znasz adres) |

**Nigdy nie wpisuj tych wartości do repo/gita** — tylko w panelu Railway.
Wygeneruj każdy sekret osobno lokalnie:

```
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
