import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


class FaynaCAPIEventLog(models.Model):
    _name = "fayna.capi.event.log"
    _description = "Meta Conversions API event log"
    _order = "create_date desc"
    _rec_name = "event_name"

    event_name = fields.Char("Event name", required=True)
    event_time = fields.Datetime("Event time", required=True)
    external_id = fields.Char("Event ID (deduplicate)")
    status = fields.Selection(
        [
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("skipped", "Skipped"),
        ],
        required=True,
        default="sent",
        index=True,
    )
    http_status = fields.Integer("HTTP status code")
    payload = fields.Text("Request payload (JSON)")
    response = fields.Text("Meta API response (JSON)")
    error_message = fields.Text("Error detail")

    # ── Retry tracking ───────────────────────────────────────────────────────
    retry_count = fields.Integer(
        "Retry count",
        default=0,
        help="Number of retry attempts made for this event (max 3).",
    )
    next_retry_at = fields.Datetime(
        "Next retry at",
        index=True,
        help="Earliest datetime at which the retry cron should attempt this event again.",
    )

    # ── Sale order linkage ───────────────────────────────────────────────────
    sale_order_id = fields.Many2one("sale.order", ondelete="set null", index=True)
    order_amount = fields.Float("Order total")
    currency_code = fields.Char("Currency")

    # ── Cron: retry failed events ────────────────────────────────────────────

    def action_retry_failed(self):
        """Retry a single failed log record (called manually from UI or by cron)."""
        self.ensure_one()
        if self.status != "failed" or self.retry_count >= _MAX_RETRIES:
            return False
        if not self.payload:
            return False
        import json

        try:
            payload_data = json.loads(self.payload)
        except (ValueError, TypeError):
            return False

        events = payload_data.get("data", [])
        if not events:
            return False
        event = events[0]
        svc = self.env["fayna.meta.capi"]
        ok = svc.send_event(
            event.get("event_name", self.event_name),
            event.get("user_data", {}),
            event.get("custom_data", {}),
            event.get("event_source_url", ""),
            event.get("event_id"),
        )
        # Update this record to reflect the retry attempt count
        self.sudo().write({"retry_count": self.retry_count + 1})
        _logger.info(
            "Meta CAPI retry #%d for log %d (%s): %s",
            self.retry_count,
            self.id,
            self.event_name,
            "ok" if ok else "failed",
        )
        return ok

    def cron_retry_failed_events(self):
        """Scheduled action: retry all failed events up to _MAX_RETRIES times.

        Called by ir.cron every 30 minutes.  Records that have already been
        retried _MAX_RETRIES times are left as-is (permanent failure).
        """
        domain = [
            ("status", "=", "failed"),
            ("retry_count", "<", _MAX_RETRIES),
        ]
        failed = self.sudo().search(domain)
        _logger.info("Meta CAPI cron_retry: %d failed events eligible for retry", len(failed))
        for rec in failed:
            rec.action_retry_failed()
