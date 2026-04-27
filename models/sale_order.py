"""Override sale.order to fire Meta CAPI Purchase event on confirmation."""

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            # CAPI failure must NEVER block checkout — fully isolated.
            self.env["fayna.meta.capi"].send_purchase(order)
        return result
