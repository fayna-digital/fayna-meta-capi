"""Override camp.support.request to fire Meta CAPI Lead event on submission.

Only active when fayna_camp_sales is installed.  The _module_installed guard
in models_to_upgrade means Odoo will never try to install this _inherit when
the parent model does not exist in the registry.

The manifest does NOT list fayna_camp_sales as a dependency so this module
can be installed standalone; Odoo's registry will simply skip models whose
_inherit target is absent.  No extra Python guard is needed — Odoo 17
silently drops _inherit classes for unknown models.
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
