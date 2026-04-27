{
    "name": "Fayna Meta Conversions API",
    "version": "17.0.1.0.0",
    "category": "Tools/Camp Management",
    "summary": "Meta Conversions API (server-side pixel) — purchase/lead events from Odoo",
    "description": """
Fayna Meta Conversions API
==========================

Phase 4 of the Fayna Camp vertical stack (Strangler Fig decomposition
per CAMPSCOUT_MASTER_TZ.md §16).

Extracted from campscout_management.models.meta_capi; sends Purchase/Lead events to Meta.

Current status: scaffold — installable but inert. Feature flag
`fayna_meta_capi.active` defaults to `False`; implementation lands in incremental
milestones defined in docs/TZ.md.

Author: Fayna Digital — Volodymyr Shevchenko
License: LGPL-3
TZ: fayna-digital-docs/contributing/CAMPSCOUT_MASTER_TZ.md §16 Phase 4
    """,
    "author": "Fayna Digital — Volodymyr Shevchenko",
    "website": "https://fayna.agency",
    "license": "LGPL-3",
    "depends": ["base", "sale", "event", "website_sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "views/fayna_capi_event_log_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
