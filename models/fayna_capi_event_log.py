import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


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

    sale_order_id = fields.Many2one("sale.order", ondelete="set null", index=True)
    order_amount = fields.Float("Order total")
    currency_code = fields.Char("Currency")
