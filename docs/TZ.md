# fayna_meta_capi — Per-module TZ

Scope: master TZ §16 Phase 4. Owner: Fayna Digital (Volodymyr Shevchenko).
Версія модуля: `17.0.3.1.3`. License: LGPL-3.

> Специфікація за REPO_STANDARD — **6 обов'язкових областей** (Objective, Commands,
> Project Structure, Code Style, Testing, Boundaries) + Success Criteria + Open Questions.
> Історичні milestones збережено нижче.

---

## Objective

Серверний піксель **Meta Conversions API (CAPI)** для Odoo 17 на платформі CampScout.

**Що будуємо:** AbstractModel `fayna.meta.capi`, який надсилає конверсійні події з Odoo
напряму до Meta (Facebook/Instagram) Ads Manager — серверним каналом, не браузерним.

**Для кого:** маркетинг CampScout — точніша оптимізація реклами (Meta бачить реальні
продажі/ліди, а не лише кліки).

**Чому серверний CAPI:** виживає після AdBlock / uBlock / Brave Shield та обмежень iOS 14.5+,
де браузерний піксель губить дані.

**Події:**

| Подія | Тригер |
|---|---|
| **Purchase** | `sale.order.action_confirm()` |
| **Lead** | `camp.support.request.action_submit()` (за наявності `fayna_camp_sales`) |
| **ViewContent** | контролер `/shop/<product>` |
| **AddToCart** | `send_add_to_cart(order_line)` |
| **InitiateCheckout** | `send_initiate_checkout(order)` |

**Що = успіх:** подія долітає до Meta (HTTP 200, видно у Test Events), `access_token`
ніколи не покидає сервер у логах/payload, помилка CAPI ніколи не ламає checkout.

---

## Commands

```bash
# Lint / format / security (єдине джерело правди — .pre-commit-config.yaml)
pre-commit run --all-files
ruff check .
ruff format --check .

# Тести (на staging, у Docker; HTTP мокується — мережа не потрібна)
docker exec campscout_web odoo -c /etc/odoo/odoo.conf -d campscout \
    --test-enable --stop-after-init --no-http -u fayna_meta_capi

# Встановлення (інертне — feature flag False)
docker exec campscout_web odoo -c /etc/odoo/odoo.conf -d campscout \
    -i fayna_meta_capi --stop-after-init --no-http

# Update після зміни моделей/views/data
docker exec campscout_web odoo -u fayna_meta_capi --stop-after-init --no-http -d campscout

# Deploy (#4ZONES)
git push origin main
ssh prod 'cd /opt/campscout/custom-addons/fayna_meta_capi && git pull && sudo chmod -R o+rX . \
    && docker restart campscout_web'
```

---

## Project Structure

```
fayna_meta_capi/
  __manifest__.py             # depends, версія 17.0.3.1.3, external python: requests
  models/
    fayna_capi_service.py     # AbstractModel "fayna.meta.capi" — send_event/send_purchase/
                              #   send_lead/send_view_content/send_add_to_cart/
                              #   send_initiate_checkout/_build_user_data/_hash_value/_get_config
    fayna_capi_event_log.py   # "fayna.capi.event.log" — журнал + retry (cron_retry_failed_events)
    res_config_settings.py    # поля Pixel ID / Access Token / API Version / Test Event Code
    sale_order.py             # _inherit sale.order: action_confirm → Purchase
    camp_support_request.py   # _inherit camp.support.request: action_submit → Lead
  controllers/website_sale.py # _inherit WebsiteSale.product → ViewContent
  views/
    fayna_capi_settings_views.xml    # блок у Налаштуваннях (admin-only)
    fayna_capi_event_log_views.xml   # журнал: tree + form + search + menu
  data/
    ir_config_parameter.xml   # enabled=False, api_version=v19.0
    cron_retry.xml            # ir.cron — ретрай failed-подій кожні 30 хв
  security/ir.model.access.csv
  i18n/uk_UA.po, i18n/pl_PL.po
  tests/test_fayna_meta_capi.py, tests/test_scaffold.py
  docs/TZ.md, docs/PLAN.md
```

Код → `models/` + `controllers/`. Тести → `tests/`. Docs → `docs/`. Конфіг/cron → `data/`.

---

## Code Style

Odoo/OCA конвенції; ruff + ruff-format як gate. Сервісні методи — `@api.model`, type hints
на публічному API, виклики CAPI **ніколи не кидають винятків**:

```python
@api.model
def send_purchase(self, order) -> bool:
    """Send Purchase event for a confirmed sale.order."""
    try:
        partner = order.partner_id
        event_id = f"purchase_{order.id}_{int(order.date_order.timestamp())}"
        user_data = self._build_user_data(partner)
        custom_data = {
            "currency": order.currency_id.name,
            "value": order.amount_total,
            "order_id": order.name,
            "content_type": "product",
        }
        return self._send_event_inner(
            "Purchase", user_data, custom_data, event_id=event_id, order=order,
        )
    except Exception:
        _logger.exception("Meta CAPI send_purchase failed for order %s", order.name)
        return False
```

Конвенції:
- **PII → SHA-256** через `_hash_value` (strip + lower); phone — лише цифри + провідний `+`.
- `access_token` додається в payload лише безпосередньо перед `requests.post`; у журнал
  пишеться `payload_for_log` **без** токена (security invariant).
- `sudo()` для `ir.config_parameter` та запису в `fayna.capi.event.log`.
- Логування: `_logger.info` на успіх/skip, `_logger.exception` на помилку; payload — не в prod UI.
- Усі публічні точки входу (`sale_order`, `controllers`, `camp_support_request`) обгортають
  виклик CAPI у try/except — feature isolation.

---

## Testing

- **Фреймворк:** Odoo `TransactionCase` (`--test-enable`).
- **Де:** `tests/test_fayna_meta_capi.py` (основні) + `tests/test_scaffold.py` (smoke встановлення).
- **Мережа:** усі HTTP мокують `requests.post` — тести детерміновані, без мережі.
- **Покриття:** усі типи подій (Purchase/Lead/ViewContent/AddToCart/InitiateCheckout),
  хешування PII, gating feature flag, timeout/network error, створення журналу,
  payload без `access_token`, round-trip config-параметрів, retry-логіка. Ціль ≥70%
  критичних шляхів (per master TZ §4.6 ЗАКОН).
- **Security-тести:** `access_token` ніколи не в URL і не в журналі.

---

## Boundaries

**Always:**
- Будь-який виклик CAPI обгортати у try/except — помилка не ламає бізнес-потік.
- Хешувати PII перед відправкою; тримати `access_token` лише в `ir.config_parameter`.
- Логувати кожен виклик у `fayna.capi.event.log`.
- Один bump версії на сесію; запис у CHANGELOG.

**Ask first:**
- Увімкнення feature flag `fayna_meta_capi.enabled` на проді.
- Додавання нової події/типу конверсії (вплив на маркетингову атрибуцію).
- Зміна API-версії Meta Graph (`fayna_meta_capi.api_version`).
- Production-деплой до того, як усі модулі стека на Hetzner staging з human QA green.

**Never:**
- Працювати напряму на сервері (#4ZONES).
- Писати `access_token` у код, UI, лог, журнал чи git.
- Дозволяти винятку CAPI пробитися в `action_confirm` / `action_submit` / контролер.
- Комітити секрети (`.env`, `*.key`, `*_token*`).

---

## Success Criteria

- [ ] Тестова подія долітає до Meta (HTTP 200, видно у Test Events).
- [ ] `access_token` відсутній у журналі подій та в URL (security-тест зелений).
- [ ] Помилка CAPI не блокує підтвердження замовлення / submit форми / рендер сторінки.
- [ ] Feature flag `False` → модуль повністю інертний (жодного виклику до Meta).
- [ ] Failed-події ретраяться cron-ом ≤3 рази; permanent failure лишається в журналі.
- [ ] pre-commit gates зелені; тести ≥70% критичних шляхів.

---

## Open Questions

- Чи додавати дедуплікацію browser-pixel ↔ server-event через спільний `event_id`/`external_id` (частково є)?
- Чи потрібен окремий dashboard статистики подій (зараз лише tree-журнал)?
- Чи виносити AddToCart/InitiateCheckout у автоматичні hooks (зараз лише публічний API)?

---

## Non-goals

- Будь-що поза Phase 4 scope per master TZ.
- Production deployment до того, як усі модулі стека на Hetzner staging з human QA green
  (`feedback_prod_deploy_gate.md` — ЗАКОН).
- Браузерний піксель (це інший канал; тут лише серверний CAPI).

---

## Incremental milestones (історія)

### M.0 Scaffold ✅ (2026-04-24)
Empty module, installable, feature flag seeded `False`, CI green.

### M.1 Core service + події ✅ (2026-04-27)
`fayna.meta.capi` AbstractModel; Purchase/Lead/ViewContent; settings UI; журнал подій; 22 тести.

### M.2 Payload/response logging ✅ (2026-04-28)
`payload` + `response` поля журналу (без `access_token`); +5 тестів; README українською.

### M.3 Retry + extra events ✅ (до 17.0.3.1.3)
Cron ретраю failed-подій (30 хв, max 3); AddToCart + InitiateCheckout; retry-tracking поля.

---

## Rollback

- Flip `fayna_meta_capi.enabled` → `False` (модуль стає інертним).
- Якщо все ще збоїть — uninstall; core-таблиці Odoo лишаються незмінними.

---

## Reference

- Master TZ `CAMPSCOUT_MASTER_TZ.md §16 Phase 4`
- REPO_STANDARD (fayna-digital-docs/contributing)
- Sister modules per `__manifest__.py` depends
