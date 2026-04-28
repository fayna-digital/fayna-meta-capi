# fayna_meta_capi — Meta Conversions API для Odoo 17

![Odoo Version](https://img.shields.io/badge/Odoo-17.0%20Community-purple)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Phase](https://img.shields.io/badge/Phase-4-orange)
![License](https://img.shields.io/badge/License-LGPL--3-green.svg)
![Status](https://img.shields.io/badge/Status-Production--ready-brightgreen)
![Version](https://img.shields.io/badge/Version-17.0.2.0.0-blue)

**Розроблено [Fayna Digital](https://www.fayna.agency) для платформи CampScout.**
**Автор: Volodymyr Shevchenko**

---

## Що це і навіщо

Модуль надсилає конверсії з Odoo напряму до Meta (Facebook/Instagram) через **Conversions API (CAPI)** — серверний піксель.

Чому це краще за звичайний браузерний піксель:
- **Не блокується** AdBlock, uBlock Origin, Brave Shield
- **Працює після iOS 14.5+** (Apple обмежила трекінг браузерами)
- **Точніші дані** для оптимізації реклами — Meta бачить продажі, а не кліки

Модуль є частиною **Phase 4** плану декомпозиції CampScout (`CAMPSCOUT_MASTER_TZ.md §16`).

---

## Що відстежується

| Подія | Коли спрацьовує |
|---|---|
| **Purchase** | Підтвердження замовлення (`sale.order.action_confirm`) |
| **Lead** | Відправка форми звернення (`camp.support.request.action_submit`) |
| **ViewContent** | Перегляд сторінки товару на сайті (`/shop/<product>`) |

---

## Архітектура

```
fayna_meta_capi/
├── __manifest__.py                        # залежності, версія 17.0.2.0.0
├── models/
│   ├── fayna_capi_service.py              # AbstractModel "fayna.meta.capi"
│   │                                      # send_purchase / send_lead / send_view_content
│   ├── fayna_capi_event_log.py            # модель "fayna.capi.event.log" — журнал
│   ├── res_config_settings.py             # поля у Налаштуваннях Odoo
│   ├── sale_order.py                      # hook на action_confirm → Purchase
│   └── camp_support_request.py            # hook на action_submit → Lead (потребує fayna_camp_sales)
├── controllers/
│   └── website_sale.py                    # hook на /shop/<product> → ViewContent
├── views/
│   ├── fayna_capi_settings_views.xml      # блок у Налаштуваннях (admin-only)
│   └── fayna_capi_event_log_views.xml     # журнал подій (tree + form + search + menu)
├── data/ir_config_parameter.xml           # початкові значення параметрів (enabled=False)
├── security/ir.model.access.csv           # доступ до журналу (admin rw, user ro)
├── i18n/uk_UA.po                          # переклад українською
├── i18n/pl_PL.po                          # переклад польською
├── tests/
│   ├── test_fayna_meta_capi.py            # 22 тести (мок requests.post)
│   └── test_scaffold.py                   # 5 smoke-тестів встановлення
├── docs/TZ.md
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
└── pyproject.toml
```

---

## Встановлення

```bash
cd /opt/campscout/custom-addons
sudo -u \#1000 git clone https://github.com/VladSh77/fayna-meta-capi.git fayna_meta_capi

docker exec campscout_web odoo -c /etc/odoo/odoo.conf -d campscout \
    -i fayna_meta_capi --stop-after-init --no-http

docker restart campscout_web
```

Модуль встановлюється **інертним** (feature flag `False`). Жодної зміни поведінки до явного увімкнення.

---

## Налаштування

Відкрити: **Налаштування → Meta CAPI**

| Поле | Де знайти у Meta |
|---|---|
| **Pixel ID** | Events Manager → Data Sources → <ваш піксель> → Settings |
| **Access Token** | Events Manager → Settings → Conversions API → Generate Access Token |
| **Test Event Code** | Events Manager → Test Events (тільки для тестування, на проді — порожньо) |
| **API Version** | За замовчуванням `v19.0` |

Після збереження — натиснути **"Надіслати тестову подію"** і перевірити у вкладці Test Events у Meta Events Manager (може зайняти до 60 секунд).

---

## Безпека

- `access_token` зберігається в `ir.config_parameter` (admin-only, не відображається в UI через `password="True"`)
- У журнал подій (`fayna.capi.event.log`) **токен не пишеться** — зберігається лише payload без `access_token`
- SHA-256 хешування email і телефону перед передачею до Meta
- Журнал доступний тільки адміністраторам (`base.group_system`)

---

## Журнал подій

**Налаштування → Технічне → Meta CAPI → Журнал подій**

Кожен виклик до Meta API фіксується:

| Поле | Зміст |
|---|---|
| Дата | Коли відправлено |
| Подія | Purchase / Lead / ViewContent |
| Статус | `sent` / `failed` / `skipped` |
| HTTP код | 200 = успіх, 4xx/5xx = помилка Meta |
| Замовлення | Посилання на `sale.order` (якщо є) |
| Payload (JSON) | Що саме відправлено до Meta |
| Відповідь Meta (JSON) | Що Meta повернула |
| Деталі помилки | Текст помилки (якщо є) |

---

## Тести

```bash
# Запустити на staging:
docker exec campscout_web odoo -c /etc/odoo/odoo.conf -d campscout \
    --test-enable --stop-after-init --no-http -u fayna_meta_capi
```

27 тестів (22 основних + 5 smoke). Всі HTTP-виклики мокуються — мережа не потрібна.

---

## Ліцензія

LGPL-3 — see [LICENSE](LICENSE).

---

*Розроблено [Fayna Digital](https://www.fayna.agency) · Volodymyr Shevchenko*
