# ROTA-T030 — Panel sterowania → Obiekt: katalog zmian standardowych

Status: **DRAFT — plan, not yet implemented**

## 1. Cel

Dziś każdy nowo utworzony obiekt ma pusty katalog zmian
(`SiteProfile.standard_shifts=[]`) i nie istnieje żaden ekran ani endpoint,
żeby to uzupełnić — obiekt na stałe zostaje w stanie "Konfiguracja niepełna"
("Profil zmianowy nie ma zdefiniowanej żadnej zmiany standardowej"), bez
sposobu, by koordynator to naprawił. Zakładka "Obiekt" w Panelu sterowania
już istnieje jako wyszarzony placeholder — to jej docelowa zawartość.

Wcześniej zidentyfikowane jako pozycja D-2 w audycie
`tasks/CURSOR_AUDIT_2026-08-23_backend_ui_coverage/round_01/tests/tests_r1.txt`.

## 2. Zweryfikowane fakty o backendzie (już istnieje, sprawdzone w kodzie)

- `rota/persistence/site_profile_repository.py::get_site_profile(conn, profile_id)`
  — odczyt całego profilu wraz z `standard_shifts`.
- `rota/application/durable_inputs.py::update_site_profile(conn, *, coordinator_id,
  site_id, profile: SiteProfile, ...)` — zapis całego profilu, z pełnym
  audytem (`SITE_PROFILE_CHANGED`), sprawdza że `profile.profile_id` należy
  do `site_id`.
- `rota/planning/shift_catalog.py::validate_standard_shift_shape` /
  `validate_standard_shift` — walidacja pojedynczego wiersza zmiany: pełne
  godziny (bez minut), niepuste i unikalne dni tygodnia (1–7), zgodność
  `catalog_kind` (24h/12h/INNY) z realnym czasem trwania,
  `required_primary_count > 0`.
- `rota.domain.StandardShift` pola: `kind` (D/N), `start_time`, `end_time`,
  `end_next_day`, `required_primary_count`, `catalog_kind` (opcjonalne,
  auto-wykrywane z czasu trwania), `required_rest_hours` (domyślnie 11),
  `active_weekdays` (domyślnie wszystkie dni).
- **"12h czy 24h" nie jest osobnym przełącznikiem** —
  `rota/planning/eligibility.py::is_all_24h_profile` wylicza to automatycznie
  z zawartości `standard_shifts` (profil jest "all-24h" tylko jeśli KAŻDA
  zmiana ma 24h czasu trwania). Formularz więc dodaje wiersze zmian, nie
  ustawia trybu obiektu wprost.

**Brakuje wyłącznie:** cienkiego API routera nad `update_site_profile`/
`get_site_profile`, i zawartości frontendowej zakładki "Obiekt" (dziś
wyłączony placeholder w `ControlPanel.tsx`).

## 3. Zakres poza tym zadaniem (świadomie, D2 owner decision 2026-08-22)

Pozostałe pola `SiteProfile` (`training_s_enabled`, `external_support_enabled`,
`day_only_blocks_n`) zostają wyłącznie do odczytu / nietykane — te przełączniki
są na stałe poza UI (patrz `arch/T021_owner_decisions_2026-08-22.md`). Zapis
przez `update_site_profile` musi wysyłać PEŁNY, niezmieniony profil poza
listą zmian, żeby ich przypadkiem nie nadpisać.

## 4. Do decyzji właściciela przed implementacją

1. Czy koordynator może USUWAĆ wiersz zmiany, czy tylko dodawać/edytować
   (co się dzieje z istniejącym grafikiem, jeśli usunie zmianę, na której
   ktoś już pracuje)?
2. Czy `required_rest_hours`/`active_weekdays` mają być widoczne i
   edytowalne w tym formularzu, czy zostają na wartościach domyślnych na
   start (uproszczenie), z edycją dodaną później?
3. Format wpisywania godzin (proste `<input type="time">` wystarczy, czy
   potrzebny wybór z listy typowych wzorców, np. "06:00–18:00")?

## 5. Weryfikacja (po implementacji)

- Pełna regresja Pythona.
- Nowy test integracyjny: utworzenie obiektu → dodanie zmiany przez nowy
  endpoint → `coordinator_context_completeness` przestaje zgłaszać brak
  zmiany standardowej.
- Build frontendu, ręczna weryfikacja na żywo.
