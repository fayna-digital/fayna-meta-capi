{
    "name": "Fayna Meta Conversions API",
    "version": "17.0.3.1.3",
    "category": "Tools/Camp Management",
    "summary": "Meta Conversions API (server-side pixel) — Purchase/Lead/ViewContent events from Odoo",
    "description": """
Fayna Meta Conversions API
==========================

Phase 4 of the Fayna Camp vertical stack (Strangler Fig decomposition
per CAMPSCOUT_MASTER_TZ.md §16).

Sends server-side conversion events to Meta (Facebook/Instagram) Ads Manager:

* **Purchase** — fired when a sale.order is confirmed
* **Lead** — fired when a camp.support.request is submitted
* **ViewContent** — fired when a visitor views a /shop/<product> page

Server-side CAPI is more accurate than pixel-only tracking because it
survives ad blockers and iOS 14.5+ privacy restrictions.

Feature flag ``fayna_meta_capi.enabled`` (default ``False``) keeps the module
inert until explicitly enabled via Settings → Meta CAPI.

Author: Fayna Digital — Volodymyr Shevchenko
License: LGPL-3
TZ: fayna-digital-docs/contributing/CAMPSCOUT_MASTER_TZ.md §16 Phase 4
    """,
    "author": "Fayna Digital — Volodymyr Shevchenko",
    "website": "https://fayna.agency",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale",
        "event",
        "website_sale",
        "base_setup",
        "fayna_camp_sales",
        "fayna_rodo_compliance",
    ],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "data/cron_retry.xml",
        "views/fayna_capi_settings_views.xml",
        "views/fayna_capi_event_log_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
