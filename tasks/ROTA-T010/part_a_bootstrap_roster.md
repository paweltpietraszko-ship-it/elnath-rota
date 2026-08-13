# ROTA-T010-A — pierwsza konfiguracja i bieżąca obsada

STATUS: DRAFT FOR CODEX AUDIT

Jedna ścieżka application layer obsługuje pierwszy zapis i późniejszą edycję tych samych danych: `Coordinator -> SiteProfile -> Site -> CoordinatorSiteAssociation`. Bez osobnego onboardingu i bez UI.

Użyć istniejących `save_coordinator`, `save_site_profile`, `save_site`, `save_coordinator_site_association`. Później używać istniejących T009: `update_site_profile`, `update_employee`, `update_membership`, `set_target_hours`. Nie tworzyć kopii danych.

Dodać jedną małą operację zapisu pierwszego/istniejącego kontekstu. Gdy nie ma aktywnego Association, może utworzyć lub wznowić pierwszy kontekst i wykorzystuje częściowe rekordy o tych samych identyfikatorach. Nie zapisuje flagi onboardingu ani numeru kroku. Konflikt z innym kontekstem oznacza odmowę. Gdy aktywne Association istnieje, zwykła edycja wymaga `require_active_coordinator_context()`.

## Dwa odczyty, dwa znaczenia

Nie wolno jednym statusem mieszać stałej konfiguracji obiektu z gotowością konkretnego miesiąca.

1. **Kompletność kontekstu obiektu** — wyliczana z trwałych danych niezależnych od miesiąca. Wymaga aktywnych Coordinator, SiteProfile, Site i Association, co najmniej jednej poprawnej standardowej zmiany, wymaganych stałych parametrów profilu oraz co najmniej jednego aktywnego LOCAL SiteMembership z istniejącym Employee.
2. **Gotowość do PLAN dla wskazanego miesiąca** — wymaga kompletnego kontekstu oraz pełnego `CalendarDay` dla każdego dnia tego konkretnego miesiąca. Zwraca listę brakujących dni/danych.

Brak `target_hours` nie blokuje gotowości do PLAN. Jest zgłaszany jako brak danych dla istniejącego SOFT/bilansu, zgodnie z T009, ale nie zmienia statusu miesięcznej gotowości na niedostępny.

Gotowość jest liczona osobno dla każdego miesiąca: ten sam Site może być gotowy dla miesiąca A i niegotowy dla miesiąca B.

Bieżąca obsada: odczyt Employee z `SiteMembership.enabled=true`. Usunięcie z obsady = `enabled=false`; bez DELETE Employee i bez kasowania historii. Ponowne dodanie = włączenie tego samego membership.

Testy obowiązkowe: pusta baza; wznowienie częściowej konfiguracji bez duplikacji; istniejący kontekst wymaga autoryzacji; konkurencyjny bootstrap odrzucony; kompletny kontekst bez kalendarza; kalendarz niepełny; kalendarz pełny; brak target_hours nie blokuje; miesiąc A gotowy / miesiąc B niegotowy; `enabled=false` usuwa z bieżącej obsady i eligibility, lecz zachowuje historię.

FAIL za osobny stan onboardingu, równoległe źródło konfiguracji, fizyczne kasowanie pracownika, ogólne osłabienie kontroli kontekstu albo status „skonfigurowany” ignorujący miesiąc przy pytaniu o gotowość do PLAN.