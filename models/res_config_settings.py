"""Extend res.config.settings with Meta CAPI configuration fields."""

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ── Feature flag ────────────────────────────────────────────────────────
    fayna_capi_enabled = fields.Boolean(
        string="Enable Meta CAPI",
        config_parameter="fayna_meta_capi.enabled",
    )

    # ── Credentials ─────────────────────────────────────────────────────────
    fayna_capi_pixel_id = fields.Char(
        string="Pixel ID",
        config_parameter="fayna_meta_capi.pixel_id",
    )
    fayna_capi_access_token = fields.Char(
        string="Access Token",
        config_parameter="fayna_meta_capi.access_token",
        password=True,
    )
    fayna_capi_api_version = fields.Char(
        string="API Version",
        config_parameter="fayna_meta_capi.api_version",
        default="v19.0",
    )
    fayna_capi_test_event_code = fields.Char(
        string="Test Event Code",
        config_parameter="fayna_meta_capi.test_event_code",
    )

    # ── Test button ─────────────────────────────────────────────────────────

    def action_send_test_capi_event(self):
        """Send a test ViewContent event via Meta CAPI and display result."""
        return self.env["fayna.meta.capi"].action_send_test_event()
