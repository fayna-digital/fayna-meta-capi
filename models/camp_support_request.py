"""Override camp.support.request to fire Meta CAPI Lead event on submission.

Only active when fayna_camp_sales is installed (guard: model existence check).
"""

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class CampSupportRequest(models.Model):
    _inherit = "camp.support.request"

    def action_submit(self):
        result = super().action_submit()
        for rec in self:
            # CAPI failure must NEVER block submission — fully isolated.
            self.env["fayna.meta.capi"].send_lead(
                rec.partner_id,
                source_url="",
            )
        return result
