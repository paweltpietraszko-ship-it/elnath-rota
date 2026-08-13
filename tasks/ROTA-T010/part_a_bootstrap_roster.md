# ROTA-T010-A — pierwsza konfiguracja i bieżąca obsada

STATUS: DRAFT FOR CODEX AUDIT

Jedna ścieżka application layer obsługuje pierwszy zapis i późniejszą edycję tych samych danych: `Coordinator -> SiteProfile -> Site -> CoordinatorSiteAssociation`. Bez osobnego onboardingu i bez UI.

Użyć istniejących `save_coordinator`, `save_site_profile`, `save_site`, `save_coordinator_site_association`. Później używać istniejących T009: `update_site_profile`, `update_employee`, `update_membership`, `set_target_hours`. Nie tworzyć kopii danych.

Dodać jedną małą operację `save_configuration_context(...)` (nazwa równoważna dozwolona). Gdy nie ma aktywnego Association, może utworzyć lub wznowić pierwszy kontekst i wykorzystuje częściowe rekordy o tych samych identyfikatorach. Nie zapisuje flagi onboardingu ani numeru kroku. Konflikt z innym kontekstem oznacza odmowę. Gdy aktywne Association istnieje, ta sama operacja wymaga `require_active_coordinator_context()`.

Dodać odczyt aplikacyjny wyliczany z istniejących danych: brak pierwszego kontekstu / konfiguracja częściowa / obiekt skonfigurowany + lista brakujących elementów. Statusu nie zapisujemy w DB. Podstawowy obiekt jest skonfigurowany, gdy istnieją aktywne Coordinator, SiteProfile, Site, Association, co najmniej jedna standardowa zmiana i co najmniej jeden aktywny LOCAL SiteMembership.

Bieżąca obsada: odczyt Employee z `SiteMembership.enabled=true`. Usunięcie z obsady = `enabled=false`; bez DELETE Employee i bez kasowania historii. Ponowne dodanie = włączenie tego samego membership.

Testy: pusta baza; wznowienie częściowej konfiguracji bez duplikacji; istniejący kontekst wymaga autoryzacji; konkurencyjny bootstrap odrzucony; poprawny odczyt stanu; `enabled=false` usuwa z bieżącej obsady i eligibility, lecz zachowuje historię.

FAIL za osobny stan onboardingu, równoległe źródło konfiguracji, fizyczne kasowanie pracownika albo ogólne osłabienie kontroli kontekstu.