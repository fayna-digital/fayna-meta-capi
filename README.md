# Meta CAPI — Meta Conversions API dla Odoo 17

![Odoo Version](https://img.shields.io/badge/Odoo-17.0%20Community-purple)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Phase](https://img.shields.io/badge/Phase-4-orange)
![License](https://img.shields.io/badge/License-LGPL--3-green.svg)
![Status](https://img.shields.io/badge/Status-Production--ready-brightgreen)
![Version](https://img.shields.io/badge/Version-17.0.3.1.3-blue)

**Opracowane przez [Fayna Digital](https://www.fayna.agency) dla platformy CampScout.**
**Autor: Volodymyr Shevchenko**

---

## Co to jest i po co

Moduł wysyła konwersje z Odoo bezpośrednio do Meta (Facebook/Instagram) przez **Conversions API (CAPI)** — piksel po stronie serwera.

Dlaczego to lepsze niż zwykły piksel przeglądarkowy:
- **Nie jest blokowany** przez AdBlock, uBlock Origin, Brave Shield
- **Działa po iOS 14.5+** (Apple ograniczyło śledzenie przez przeglądarki)
- **Dokładniejsze dane** do optymalizacji reklam — Meta widzi sprzedaż, a nie kliknięcia

Moduł jest częścią **Phase 4** planu dekompozycji CampScout (`CAMPSCOUT_MASTER_TZ.md §16`).

---

## Co faktycznie robi ten kod

Poniższy opis pochodzi z bezpośredniej analizy plików (`models/`, `controllers/`, `data/`, `tests/`).

### Serwis (`models/fayna_capi_service.py`, 498 linii)

`fayna.meta.capi` to **AbstractModel** — żyje wewnątrz env Odoo i można go wywołać z dowolnego modelu przez `self.env["fayna.meta.capi"]`. Publiczne API:
- `send_event(event_name, user_data, custom_data, event_source_url, event_id)` — wysyła jedną konwersję; zwraca `True` przy HTTP-200, `False` w przeciwnym razie (w tym przy wyłączonym/skip). **NIGDY nie rzuca wyjątków** — wywołujący nie muszą nic łapać.
- `send_purchase(order)` — zdarzenie **Purchase**.
- `send_lead(partner, source_url)` — zdarzenie **Lead**.
- `send_view_content(partner, product, source_url)` — zdarzenie **ViewContent**.

Wszystkie wywołania HTTP są odizolowane za `requests.post` do `https://graph.facebook.com/{api_version}/{pixel_id}/events`; testy mockują ten pojedynczy symbol.

### Zdarzenia i hooki

| Zdarzenie | Kiedy odpala | Hook w kodzie |
|---|---|---|
| **Purchase** | Potwierdzenie zamówienia | `models/sale_order.py` — hook na `action_confirm` |
| **Lead** | Wysłanie formularza zapytania | `models/camp_support_request.py` — hook na `action_submit` (wymaga `fayna_camp_sales`) |
| **ViewContent** | Otwarcie strony produktu | `controllers/website_sale.py` — hook na `/shop/<product>` |

### Retry (`data/cron_retry.xml`)

Moduł zawiera cron retry dla nieudanych wysyłek (przejściowe błędy sieci / odpowiedzi Meta).

### Bezpieczeństwo

- `access_token` przechowywany w `ir.config_parameter` (admin-only, nie wyświetlany w UI przez `password="True"`).
- Do dziennika zdarzeń (`fayna.capi.event.log`) **token nie jest zapisywany** — tylko payload bez `access_token`.
- SHA-256 hashowanie emaila i telefonu przed wysłaniem do Meta.
- Dziennik dostępny tylko dla administratorów (`base.group_system`).

### Feature flag

Moduł instaluje się **inertnie** (`fayna_meta_capi.enabled`, domyślnie `False`). Żadnej zmiany zachowania do jawnego włączenia przez **Settings → Meta CAPI**.

---

## Struktura repozytorium

```
fayna_meta_capi/
├── __manifest__.py                        # zależności, wersja 17.0.3.1.3, LGPL-3
├── models/
│   ├── fayna_capi_service.py              # AbstractModel "fayna.meta.capi"
│   │                                      #   send_purchase / send_lead / send_view_content
│   ├── fayna_capi_event_log.py            # model "fayna.capi.event.log" — dziennik
│   ├── res_config_settings.py             # pola w Ustawieniach Odoo
│   ├── sale_order.py                      # hook na action_confirm → Purchase
│   └── camp_support_request.py            # hook na action_submit → Lead (wymaga fayna_camp_sales)
├── controllers/
│   └── website_sale.py                    # hook na /shop/<product> → ViewContent
├── views/
│   ├── fayna_capi_settings_views.xml      # blok w Ustawieniach (admin-only)
│   └── fayna_capi_event_log_views.xml     # dziennik zdarzeń (tree + form + search + menu)
├── data/
│   ├── ir_config_parameter.xml            # początkowe wartości parametrów (enabled=False)
│   └── cron_retry.xml                     # cron retry nieudanych wysyłek
├── security/ir.model.access.csv           # dostęp do dziennika (admin rw, user ro)
├── i18n/uk_UA.po                          # tłumaczenie ukraińskie
├── i18n/pl_PL.po                          # tłumaczenie polskie
├── tests/
│   ├── test_fayna_meta_capi.py            # 36 testów (mock requests.post)
│   └── test_scaffold.py                   # 5 smoke-testów instalacji
├── docs/TZ.md
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
└── pyproject.toml
```

---

## Instalacja

```bash
cd /opt/campscout/custom-addons
sudo -u \#1000 git clone https://github.com/fayna-digital/fayna-meta-capi.git fayna_meta_capi

docker exec campscout_web odoo -c /etc/odoo/odoo.conf -d campscout \
    -i fayna_meta_capi --stop-after-init --no-http

docker restart campscout_web
```

Moduł instaluje się **inertnie** (feature flag `False`). Żadnej zmiany zachowania do jawnego włączenia.

---

## Konfiguracja

Otwórz: **Ustawienia → Meta CAPI**

| Pole | Gdzie znaleźć w Meta |
|---|---|
| **Pixel ID** | Events Manager → Data Sources → <twój piksel> → Settings |
| **Access Token** | Events Manager → Settings → Conversions API → Generate Access Token |
| **Test Event Code** | Events Manager → Test Events (tylko do testów, na prodzie — puste) |
| **API Version** | Domyślnie `v19.0` |

Po zapisaniu — kliknij **"Wyślij zdarzenie testowe"** i sprawdź w zakładce Test Events w Meta Events Manager (może zająć do 60 sekund).

---

## Dziennik zdarzeń

**Ustawienia → Techniczne → Meta CAPI → Dziennik zdarzeń**

Każde wywołanie do Meta API jest rejestrowane:

| Pole | Zawartość |
|---|---|
| Data | Kiedy wysłano |
| Zdarzenie | Purchase / Lead / ViewContent |
| Status | `sent` / `failed` / `skipped` |
| Kod HTTP | 200 = sukces, 4xx/5xx = błąd Meta |
| Zamówienie | Link do `sale.order` (jeśli jest) |
| Payload (JSON) | Co dokładnie wysłano do Meta |
| Odpowiedź Meta (JSON) | Co Meta zwróciła |
| Szczegóły błędu | Tekst błędu (jeśli jest) |

---

## Testy

```bash
# Uruchom na staging:
docker exec campscout_web odoo -c /etc/odoo/odoo.conf -d campscout \
    --test-enable --stop-after-init --no-http -u fayna_meta_capi
```

41 testów (36 głównych + 5 smoke). Wszystkie wywołania HTTP są mockowane — sieć nie jest potrzebna.

---

## Dokumentacja

- [docs/TZ.md](docs/TZ.md) — techniczne zadanie
- [docs/PLAN.md](docs/PLAN.md) — graf zależności + fazy + checkpointy
- [CHANGELOG.md](CHANGELOG.md) — historia zmian
- Master TZ: `CAMPSCOUT_MASTER_TZ.md §16 Phase 4`
