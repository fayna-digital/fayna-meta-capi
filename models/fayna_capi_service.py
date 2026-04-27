import hashlib
import logging

import requests
from odoo import fields

_logger = logging.getLogger(__name__)


class FaynaCAPIService:
    """
    Stateless helper — reads config from ir.config_parameter and posts
    events to Meta Conversions API (Graph API v19.0).

    Usage:
        svc = FaynaCAPIService(env)
        svc.send_purchase(order)
    """

    GRAPH_API_URL = "https://graph.facebook.com/v19.0/{pixel_id}/events"

    def __init__(self, env):
        self.env = env
        params = env["ir.config_parameter"].sudo()
        self.pixel_id = params.get_param("fayna_meta_capi.pixel_id", "")
        self.access_token = params.get_param("fayna_meta_capi.access_token", "")
        self.active = params.get_param("fayna_meta_capi.active", "False").strip().lower() == "true"
        self.test_event_code = params.get_param("fayna_meta_capi.test_event_code", "")

    def _is_configured(self):
        return bool(self.pixel_id and self.access_token and self.active)

    def send_purchase(self, order):
        """Send Purchase event for a confirmed sale.order."""
        if not self._is_configured():
            reason = "not configured or inactive"
            _logger.debug("Meta CAPI send_purchase skipped for order %s: %s", order.name, reason)
            self._log(
                "Purchase",
                None,
                "skipped",
                0,
                reason,
                order,
            )
            return {"status": "skipped", "reason": reason}

        partner = order.partner_id
        event_id = f"purchase_{order.id}_{int(order.date_order.timestamp())}"

        payload = {
            "data": [
                {
                    "event_name": "Purchase",
                    "event_time": int(order.date_order.timestamp()),
                    "event_id": event_id,
                    "action_source": "website",
                    "user_data": self._build_user_data(partner),
                    "custom_data": {
                        "currency": order.currency_id.name,
                        "value": order.amount_total,
                        "order_id": order.name,
                    },
                }
            ],
            "access_token": self.access_token,
        }
        if self.test_event_code:
            payload["test_event_code"] = self.test_event_code

        return self._post_events(payload, event_id, "Purchase", order)

    def _build_user_data(self, partner):
        def sha256(val):
            if not val:
                return None
            return hashlib.sha256(val.strip().lower().encode()).hexdigest()

        data = {}
        if partner.email:
            hashed = sha256(partner.email)
            if hashed:
                data["em"] = [hashed]
        if partner.phone:
            # Normalize: keep digits and leading '+' only
            phone = "".join(c for c in partner.phone if c.isdigit() or c == "+")
            hashed = sha256(phone)
            if hashed:
                data["ph"] = [hashed]
        return data

    def _post_events(self, payload, event_id, event_name, order=None):
        url = self.GRAPH_API_URL.format(pixel_id=self.pixel_id)
        try:
            resp = requests.post(url, json=payload, timeout=10)
            status = "sent" if resp.status_code == 200 else "failed"
            error = None if status == "sent" else resp.text[:500]
            self._log(event_name, event_id, status, resp.status_code, error, order)
            return {"status": status, "http_status": resp.status_code}
        except requests.RequestException as exc:
            msg = str(exc)[:500]
            _logger.warning(
                "Meta CAPI HTTP error for pixel %s event %s: %s",
                self.pixel_id,
                event_name,
                msg,
            )
            self._log(event_name, event_id, "failed", 0, msg, order)
            return {"status": "failed", "error": msg}

    def _log(self, event_name, event_id, status, http_status, error, order=None):
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
