# Konfiguracja Railway w kodzie (`.railway/railway.ts`)

Ten folder opisuje JEDEN istniejący serwis `elnath-rota` (projekt `truthful-freedom`).
Zastępuje przestarzały `railway.json`, który Railway obsługuje tylko do **2026-12-01**.

- Pakiet `railway` (SDK) jest zainstalowany **tylko tutaj** (`.railway/package.json`,
  `package-lock.json`), nie w aplikacji. Instalacja: `cd .railway && npm ci`.
- **Push na `main` niczego tu nie stosuje.** Zmiany na żywym serwisie robi wyłącznie CLI
  (`railway config plan` → zgoda Ownera → `railway config apply`).
- Pole pominięte w pliku NIE znaczy „zostaw bez zmian”: plan pokazał, że brak `env`,
  `volumeMounts` albo `source` usuwa sekrety, odpina dysk `/data` i repo. Dlatego plik
  odwzorowuje cały obecny stan, a sekrety są tylko jako `preserve()` (wartości zostają na Railway).
- Windows: SDK wywołuje `railway --version` bez powłoki i nie znajduje nakładki npm.
  Przed `plan`/`apply` w PowerShellu ustaw ścieżkę do natywnego pliku:
  `$env:_ = "$env:APPDATA\npm\node_modules\@railway\cli\bin\railway.exe"`.

Kolejność przejścia z `railway.json`: `deploy/RAILWAY.md`, sekcja „Migracja z railway.json”.
