# PLAN — fayna_meta_capi (план реалізації)

> Друга черга після [docs/TZ.md](TZ.md). Dependency graph + фази + checkpoints
> (skill `planning-and-task-breakdown`).
> Що ВЖЕ зроблено — у [CHANGELOG.md](../CHANGELOG.md). Модуль на `17.0.3.1.3`, **Production-ready**.

---

## Overview

Базовий функціонал (надсилання Purchase/Lead/ViewContent, хешування PII, журнал подій,
retry-cron, AddToCart/InitiateCheckout API) — **готовий**. Модуль чекає лише
production-gate: усі модулі стека на Hetzner staging + human QA green.

---

## Dependency graph

```
[base, sale, event, website_sale, base_setup]  ── Odoo core / addons
        │
        ▼
[fayna.meta.capi service]  ── AbstractModel, ядро
        │
   ┌────┼─────────────────────────────┐
   ▼    ▼                             ▼
[sale_order]  [controllers/         [camp_support_request]
 → Purchase    website_sale]         → Lead
               → ViewContent         (потребує fayna_camp_sales)
        │
        ▼
[fayna.capi.event.log]  ── журнал + retry cron (30хв, max 3)
        │
        ▼
[fayna_rodo_compliance]  ── узгодження згоди на трекінг (RODO)
```

Незалежні гілки: Purchase, ViewContent — стартують будь-коли. Lead — лише коли
`camp.support.request` присутній у реєстрі (Odoo тихо пропускає `_inherit` для відсутньої моделі).

---

## Phases & Checkpoints

### Phase 0 — Scaffold ✅ (17.0.0.1.0)
- [x] Інсталюється інертним, feature flag `False`, CI green, canonical tooling.
- **Checkpoint:** модуль встановлюється без зміни поведінки.

### Phase 1 — Core service + базові події ✅ (17.0.1.0.0)
- [x] AbstractModel `fayna.meta.capi`: `send_event`/`send_purchase`/`send_lead`/`send_view_content`.
- [x] Hooks: `sale_order.action_confirm` → Purchase; `camp_support_request.action_submit` → Lead;
  controller `/shop/<product>` → ViewContent.
- [x] Settings UI (Pixel ID / Access Token / API Version / Test Event Code) + кнопка тесту.
- [x] Журнал `fayna.capi.event.log`; SHA-256 хешування PII; 22 тести.
- **Checkpoint:** тестова подія долітає до Meta (HTTP 200), `access_token` не в логах.

### Phase 2 — Payload/response audit ✅ (17.0.2.0.0)
- [x] Поля `payload` + `response` у журналі (payload без `access_token`).
- [x] +5 security/round-trip тестів; README українською.
- **Checkpoint:** повний аудит запиту/відповіді в журналі без витоку токена.

### Phase 3 — Retry + розширені події ✅ (17.0.3.1.3)
- [x] Cron `cron_retry_failed_events` (30 хв, max 3 спроби); поля `retry_count`/`next_retry_at`.
- [x] Події AddToCart + InitiateCheckout (публічний API).
- [x] Sale-order linkage у журналі (`sale_order_id`/`order_amount`/`currency_code`).
- **Checkpoint:** failed-події автоматично ретраяться; permanent failure лишається в журналі.

### Phase 4 — Production gate ⏳ (відкрито)
- [ ] Усі модулі стека CampScout на Hetzner staging.
- [ ] Human QA green (Test Events підтверджені у Meta Events Manager на staging).
- [ ] Узгодження з `fayna_rodo_compliance` — трекінг лише за наявності згоди.
- [ ] Увімкнути `fayna_meta_capi.enabled` на проді (Ask first).
- **Gate:** не вмикати на проді до зеленого human QA на staging (`feedback_prod_deploy_gate.md` ЗАКОН).

---

## Backlog / можливі покращення

- [ ] Автоматичні hooks для AddToCart / InitiateCheckout (зараз лише публічний API).
- [ ] Dashboard статистики подій (зараз tree-журнал).
- [ ] Дедуплікація browser-pixel ↔ server-event через спільний `event_id` (частково є).
- [ ] Алерти при застряганні failed-черги > N годин.

---

## Зв'язки

[docs/TZ.md](TZ.md) · [CHANGELOG.md](../CHANGELOG.md) · [[REPO_STANDARD]] · Master TZ `CAMPSCOUT_MASTER_TZ.md §16`
