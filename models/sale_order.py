import logging

from odoo import models

from .fayna_capi_service import FaynaCAPIService

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            try:
                FaynaCAPIService(self.env).send_purchase(order)
            except Exception:
                _logger.exception("Meta CAPI send_purchase failed for order %s", order.name)
        return result
