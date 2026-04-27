"""
Meta Conversions API service — AbstractModel so env is available everywhere.

Usage (from any Odoo context):
    self.env["fayna.meta.capi"].send_event("Purchase", user_data, custom_data, url)
    self.env["fayna.meta.capi"].send_purchase(order)
    self.env["fayna.meta.capi"].send_lead(partner, source_url)
    self.env["fayna.meta.capi"].send_view_content(partner, product, source_url)
"""

import hashlib
import logging
from datetime import datetime

import requests
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

_GRAPH_URL = "https://graph.facebook.com/{api_version}/{pixel_id}/events"


class FaynaMetaCapiService(models.AbstractModel):
    """Meta Conversions API service.

    AbstractModel so it lives inside Odoo env and can be called from any model
    via ``self.env["fayna.meta.capi"]``.  All HTTP calls are isolated behind
    ``requests.post``; tests mock that single symbol.
    """

    _name = "fayna.meta.capi"
    _description = "Meta Conversions API service"

    # ── Public API ──────────────────────────────────────────────────────────

    @api.model
    def send_event(
        self,
        event_name: str,
        user_data: dict,
        custom_data: dict,
        event_source_url: str = "",
        event_id: str | None = None,
    ) -> bool:
        """Send one conversion event to Meta CAPI.

        Returns True on HTTP-200, False otherwise (including disabled/skip).
        NEVER raises — callers must not catch anything.
        """
        try:
            return self._send_event_inner(
                event_name, user_data, custom_data, event_source_url, event_id
            )
        except Exception:
            _logger.exception("Meta CAPI send_event(%s) unhandled error", event_name)
            return False

    @api.model
    def send_purchase(self, order) -> bool:
        """Send Purchase event for a confirmed sale.order."""
        try:
            partner = order.partner_id
            event_id = f"purchase_{order.id}_{int(order.date_order.timestamp())}"
            user_data = self._build_user_data(partner)
            product_name = ""
            product_ids = []
            if order.order_line:
                first_line = order.order_line[0]
                product_name = first_line.product_id.name or ""
                product_ids = [str(first_line.product_id.id)]
            custom_data = {
                "currency": order.currency_id.name,
                "value": order.amount_total,
                "order_id": order.name,
                "content_name": product_name,
                "content_ids": product_ids,
                "content_type": "product",
            }
            return self._send_event_inner(
                "Purchase",
                user_data,
                custom_data,
                event_source_url="",
                event_id=event_id,
                order=order,
            )
        except Exception:
            _logger.exception("Meta CAPI send_purchase failed for order %s", order.name)
            return False

    @api.model
    def send_lead(self, partner, source_url: str = "") -> bool:
        """Send Lead event when a support request or inquiry is submitted."""
        try:
            event_id = f"lead_{partner.id}_{int(datetime.now().timestamp())}"
            user_data = self._build_user_data(partner)
            custom_data = {
                "content_name": "Support Request",
                "content_type": "lead",
            }
            return self._send_event_inner(
                "Lead",
                user_data,
                custom_data,
                event_source_url=source_url,
                event_id=event_id,
            )
        except Exception:
            _logger.exception("Meta CAPI send_lead failed for partner %s", partner.id)
            return False

    @api.model
    def send_view_content(self, partner, product, source_url: str = "") -> bool:
        """Send ViewContent event when a visitor views a camp product page."""
        try:
            event_id = f"view_{product.id}_{int(datetime.now().timestamp())}"
            user_data = {}
            if partner and partner != self.env.ref("base.public_partner", raise_if_not_found=False):
                user_data = self._build_user_data(partner)
            custom_data = {
                "content_name": product.name or "",
                "content_ids": [str(product.id)],
                "content_type": "product",
                "currency": self.env.company.currency_id.name,
                "value": product.list_price,
            }
            return self._send_event_inner(
                "ViewContent",
                user_data,
                custom_data,
                event_source_url=source_url,
                event_id=event_id,
            )
        except Exception:
            _logger.exception("Meta CAPI send_view_content failed for product %s", product.id)
            return False

    @api.model
    def action_send_test_event(self) -> dict:
        """Wizard-style button: send a test ViewContent event and return result notification."""
        cfg = self._get_config()
        if not cfg["enabled"]:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Meta CAPI"),
                    "message": _("Feature flag is disabled. Enable it first."),
                    "type": "warning",
                    "sticky": False,
                },
            }
        if not cfg["pixel_id"] or not cfg["access_token"]:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Meta CAPI"),
                    "message": _("Pixel ID and Access Token must be set before testing."),
                    "type": "warning",
                    "sticky": False,
                },
            }
        ok = self.send_view_content(
            self.env.user.partner_id,
            self.env["product.product"].search([], limit=1),
            source_url="https://campscout.eu/shop",
        )
        if ok:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Meta CAPI"),
                    "message": _("Test ViewContent event sent successfully."),
                    "type": "success",
                    "sticky": False,
                },
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Meta CAPI"),
                "message": _("Test event failed — check the Event Log for details."),
                "type": "danger",
                "sticky": False,
            },
        }

    # ── Config helper ───────────────────────────────────────────────────────

    @api.model
    def _get_config(self) -> dict:
        """Return CAPI config from ir.config_parameter."""
        params = self.env["ir.config_parameter"].sudo()
        enabled_raw = params.get_param("fayna_meta_capi.enabled", "False")
        return {
            "pixel_id": params.get_param("fayna_meta_capi.pixel_id", ""),
            "access_token": params.get_param("fayna_meta_capi.access_token", ""),
            "api_version": params.get_param("fayna_meta_capi.api_version", "v19.0"),
            "test_event_code": params.get_param("fayna_meta_capi.test_event_code", ""),
            "enabled": enabled_raw.strip().lower() == "true",
        }

    # ── Hash helper ─────────────────────────────────────────────────────────

    @api.model
    def _hash_value(self, value: str) -> str:
        """SHA-256 hash of a normalized (stripped + lowercased) PII string."""
        if not value:
            return ""
        return hashlib.sha256(value.strip().lower().encode()).hexdigest()

    # ── Internal ────────────────────────────────────────────────────────────

    @api.model
    def _is_configured(self, cfg: dict) -> bool:
        return bool(cfg["pixel_id"] and cfg["access_token"] and cfg["enabled"])

    @api.model
    def _build_user_data(self, partner) -> dict:
        """Build hashed user_data dict from res.partner."""
        data: dict = {}
        if partner and partner.email:
            hashed = self._hash_value(partner.email)
            if hashed:
                data["em"] = [hashed]
        if partner and partner.phone:
            # Normalize: keep digits and leading '+' only
            phone_normalized = "".join(c for c in partner.phone if c.isdigit() or c == "+")
            hashed = self._hash_value(phone_normalized)
            if hashed:
                data["ph"] = [hashed]
        return data

    @api.model
    def _send_event_inner(
        self,
        event_name: str,
        user_data: dict,
        custom_data: dict,
        event_source_url: str = "",
        event_id: str | None = None,
        order=None,
    ) -> bool:
        cfg = self._get_config()

        if not self._is_configured(cfg):
            reason = "not configured or inactive"
            _logger.debug(
                "Meta CAPI %s skipped: %s (pixel_id=%r enabled=%r)",
                event_name,
                reason,
                bool(cfg["pixel_id"]),
                cfg["enabled"],
            )
            self._write_log(event_name, event_id, "skipped", 0, reason, order)
            return False

        event_payload = {
            "event_name": event_name,
            "event_time": int(datetime.now().timestamp()),
            "action_source": "website",
            "user_data": user_data,
            "custom_data": custom_data,
        }
        if event_id:
            event_payload["event_id"] = event_id
        if event_source_url:
            event_payload["event_source_url"] = event_source_url

        payload: dict = {
            "data": [event_payload],
            "access_token": cfg["access_token"],
        }
        if cfg["test_event_code"]:
            payload["test_event_code"] = cfg["test_event_code"]

        url = _GRAPH_URL.format(api_version=cfg["api_version"], pixel_id=cfg["pixel_id"])
        try:
            resp = requests.post(url, json=payload, timeout=10)
            success = resp.status_code == 200
            status = "sent" if success else "failed"
            error = None if success else resp.text[:500]
            _logger.info(
                "Meta CAPI %s → %s (HTTP %s)", event_name, status, resp.status_code
            )
            self._write_log(event_name, event_id, status, resp.status_code, error, order)
            return success
        except requests.RequestException as exc:
            msg = str(exc)[:500]
            _logger.warning(
                "Meta CAPI HTTP error for pixel %s event %s: %s",
                cfg["pixel_id"],
                event_name,
                msg,
            )
            self._write_log(event_name, event_id, "failed", 0, msg, order)
            return False

    @api.model
    def _write_log(
        self,
        event_name: str,
        event_id,
        status: str,
        http_status: int,
        error,
        order=None,
    ) -> None:
        vals = {
            "event_name": event_name,
            "event_time": fields.Datetime.now(),
            "external_id": event_id,
            "status": status,
            "http_status": http_status,
            "error_message": error,
        }
        if order:
            vals.update(
                {
                    "sale_order_id": order.id,
                    "order_amount": order.amount_total,
                    "currency_code": order.currency_id.name,
                }
            )
        self.env["fayna.capi.event.log"].sudo().create(vals)


# ---------------------------------------------------------------------------
# Backward-compatible plain-class alias (kept so old callsites in tests
# that do FaynaCAPIService(env) still work).
# ---------------------------------------------------------------------------


class FaynaCAPIService:
    """Legacy plain-class wrapper — delegates to the AbstractModel.

    Preserved for test backward-compatibility.  New code should use
    ``env["fayna.meta.capi"].send_purchase(order)`` instead.
    """

    def __init__(self, env):
        self._svc = env["fayna.meta.capi"]

    def send_purchase(self, order):
        return self._svc.send_purchase(order)

    def _build_user_data(self, partner):
        return self._svc._build_user_data(partner)

    def _is_configured(self):
        cfg = self._svc._get_config()
        return self._svc._is_configured(cfg)
