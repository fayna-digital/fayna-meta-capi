"""Override website_sale product page controller to fire ViewContent CAPI event.

Inherits WebsiteSale.product() from odoo/addons/website_sale/controllers/main.py.
The event fires after the normal page is rendered — CAPI errors are swallowed so
they can never break the shop.
"""

import logging

from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request

_logger = logging.getLogger(__name__)


class FaynaMetaCapiWebsiteSale(WebsiteSale):
    """Inject ViewContent CAPI event on camp product page visits."""

    @http.route(inherit=True)
    def product(self, product, category="", search="", **kwargs):
        response = super().product(product, category=category, search=search, **kwargs)
        try:
            partner = request.env.user.partner_id
            source_url = request.httprequest.url
            request.env["fayna.meta.capi"].send_view_content(
                partner, product, source_url, http_request=request
            )
        except Exception:
            _logger.exception(
                "Meta CAPI ViewContent failed for product %s", getattr(product, "id", "?")
            )
        return response
