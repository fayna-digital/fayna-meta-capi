# Fayna Meta CAPI — CLAUDE.md

> 🚫 **#4ZONES — НІКОЛИ не працювати напряму на сервері.**
> Єдиний шлях: **локально → GitHub (push) → staging → prod (pull)**. Жодних правок файлів на сервері (nano/vim/scp/docker exec з редагуванням), жодних тимчасових чи ingest-скриптів на проді — спершу локально, коміт, push, тоді pull на сервер. Зміни «на сервері» зникають при наступному `git pull`/rebuild. Git — єдине джерело правди. ([[meta/golden-rules-developer]] #3)

> 🔐 **Секрети** (Pixel ID, **Access Token**, Test Event Code) — лише в `ir.config_parameter` (admin-only). Ніколи в коді, UI, логах чи git. `access_token` НІКОЛИ не пишеться в журнал подій і не виводиться в чат.

> Як працювати з репо. **Що** будуємо — у [docs/TZ.md](docs/TZ.md) (6 областей за REPO_STANDARD). План реалізації — у [docs/PLAN.md](docs/PLAN.md).

## Призначення

Серверний піксель Meta (Facebook/Instagram) **Conversions API (CAPI)** для Odoo 17. Надсилає конверсії напряму з Odoo до Meta Ads Manager — точніше за браузерний піксель (виживає після AdBlock та iOS 14.5+).

Частина **Phase 4** декомпозиції CampScout (`CAMPSCOUT_MASTER_TZ.md §16`, Strangler Fig).

**Версія:** `17.0.3.1.3` | Модуль: `fayna_meta_capi` | License: LGPL-3
**Depends:** `base`, `sale`, `event`, `website_sale`, `base_setup`, `fayna_camp_sales`, `fayna_rodo_compliance`
**External:** python `requests`

## Події, що відстежуються

| Подія | Тригер |
|---|---|
| **Purchase** | `sale.order.action_confirm()` |
| **Lead** | `camp.support.request.action_submit()` (тільки якщо `fayna_camp_sales` встановлено) |
| **ViewContent** | контролер `/shop/<product>` (`WebsiteSale.product`) |
| **AddToCart** | `send_add_to_cart(order_line)` (публічний API) |
| **InitiateCheckout** | `send_initiate_checkout(order)` (публічний API) |

Усі виклики CAPI **повністю ізольовані** — помилка ніколи не блокує checkout/submit/render. Feature flag `fayna_meta_capi.enabled` (default `False`) тримає модуль інертним до явного увімкнення.

## Структура модуля

```
fayna_meta_capi/
  models/
    fayna_capi_service.py     # AbstractModel "fayna.meta.capi" — головний сервіс
    fayna_capi_event_log.py   # "fayna.capi.event.log" — журнал + retry-логіка
    res_config_settings.py    # поля у Налаштуваннях Odoo (admin-only)
    sale_order.py             # hook action_confirm → Purchase
    camp_support_request.py   # hook action_submit → Lead
  controllers/website_sale.py # hook /shop/<product> → ViewContent
  views/                      # settings + event_log (tree/form/search/menu)
  data/                       # ir_config_parameter (enabled=False) + cron_retry (30хв)
  security/ir.model.access.csv
  i18n/                       # uk_UA.po + pl_PL.po
  tests/                      # test_fayna_meta_capi.py + test_scaffold.py
  docs/                       # TZ.md + PLAN.md
```

## Deploy — #4ZONES (Mac → GitHub → staging → prod)

```bash
git push origin main
ssh prod 'cd /opt/campscout/custom-addons/fayna_meta_capi && git pull && sudo chmod -R o+rX .'
# Python-only fix → достатньо рестарту:
ssh prod 'docker restart campscout_web'
# Зміна моделей/views/data → update:
ssh prod 'docker exec campscout_web odoo -u fayna_meta_capi --stop-after-init --no-http -d campscout && docker restart campscout_web'
```

## Налаштування

**Налаштування → Meta CAPI** (admin-only): Pixel ID, Access Token, Test Event Code, API Version (default `v19.0`). Кнопка «Надіслати тестову подію» → перевірка у Meta Events Manager → Test Events.

## Coding conventions

- PII (email, phone, partner.id) → SHA-256 (`_hash_value`), нормалізація (strip + lower) перед хешем. Phone — лише цифри + провідний `+`.
- `send_event()` та всі `send_*()` — **NEVER raise**: помилка логується через `_logger.exception` і повертає `False`.
- `access_token` додається в payload лише перед `requests.post`; у журнал пишеться `payload_for_log` БЕЗ токена.
- Кожен виклик до Meta → запис у `fayna.capi.event.log` (status: `sent` / `failed` / `skipped`).
- Failed-події ретраяться cron-ом кожні 30 хв, максимум 3 спроби (`_MAX_RETRIES`).
- Odoo/OCA: `@api.model` на сервісних методах, `sudo()` для `ir.config_parameter` та запису в журнал, type hints на публічному API.
- Semantic Versioning Odoo `17.0.MAJOR.MINOR.PATCH`: одна сесія = один bump.

## Якість

- pre-commit gates зелені на кожному коміті (ruff + ruff-format + OCA + bandit + gitleaks + base hooks).
- Тести: усі HTTP-виклики мокують `requests.post` — мережа не потрібна.

```bash
docker exec campscout_web odoo -c /etc/odoo/odoo.conf -d campscout \
    --test-enable --stop-after-init --no-http -u fayna_meta_capi
```

## Зв'язки

Стандарт: [[REPO_STANDARD]] · Master TZ: `CAMPSCOUT_MASTER_TZ.md §16 Phase 4` · Memory: [[claude-memory/MEMORY]] · Golden rules: [[meta/golden-rules-developer]]
