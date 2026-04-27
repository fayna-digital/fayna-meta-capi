"""
Tests for fayna_meta_capi — Meta Conversions API adapter.

All HTTP calls are mocked via unittest.mock.patch; no real network traffic.
"""

import hashlib
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


def _sha256(val):
    return hashlib.sha256(val.strip().lower().encode()).hexdigest()


class TestFaynaCAPIEventLog(TransactionCase):
    """Tests covering FaynaCAPIService logic and fayna.capi.event.log creation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Enable the feature flag for most tests
        cls.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.active", "True")
        cls.env["ir.config_parameter"].sudo().set_param(
            "fayna_meta_capi.pixel_id", "TEST_PIXEL_123"
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "fayna_meta_capi.access_token", "TEST_TOKEN_ABC"
        )
        cls.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.test_event_code", "")

    def _make_order(self, email="test@example.com", phone="+48 123 456 789"):
        """Create a minimal sale.order with a confirmed partner."""
        partner = self.env["res.partner"].create(
            {"name": "Test Partner", "email": email, "phone": phone}
        )
        product = self.env["product.product"].create(
            {"name": "Camp Ticket", "type": "service", "list_price": 500.0}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "price_unit": 500.0,
                        },
                    )
                ],
            }
        )
        return order

    def _mock_response(self, status_code=200, text="{}"):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.text = text
        return mock_resp

    # --- Test 1: status=sent when HTTP 200 ---
    def test_01_log_created_status_sent_on_http_200(self):
        order = self._make_order()
        with patch("fayna_meta_capi.models.fayna_capi_service.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(200)
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log, "Log record must be created")
        self.assertEqual(log.status, "sent")
        self.assertEqual(log.http_status, 200)
        self.assertFalse(log.error_message)

    # --- Test 2: status=failed when HTTP 400 ---
    def test_02_log_created_status_failed_on_http_400(self):
        order = self._make_order()
        with patch("fayna_meta_capi.models.fayna_capi_service.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(400, "Bad Request")
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, "failed")
        self.assertEqual(log.http_status, 400)
        self.assertIn("Bad Request", log.error_message)

    # --- Test 3: status=failed when requests.post raises exception ---
    def test_03_log_created_status_failed_on_network_exception(self):
        import requests as req_lib

        order = self._make_order()
        with patch("fayna_meta_capi.models.fayna_capi_service.requests.post") as mock_post:
            mock_post.side_effect = req_lib.RequestException("Connection refused")
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, "failed")
        self.assertEqual(log.http_status, 0)
        self.assertIn("Connection refused", log.error_message)

    # --- Test 4: skipped when active=False ---
    def test_04_send_purchase_skipped_when_inactive(self):
        self.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.active", "False")
        try:
            order = self._make_order()
            with patch("fayna_meta_capi.models.fayna_capi_service.requests.post") as mock_post:
                order.action_confirm()
                mock_post.assert_not_called()

            log = self.env["fayna.capi.event.log"].search(
                [("sale_order_id", "=", order.id)], limit=1
            )
            self.assertTrue(log)
            self.assertEqual(log.status, "skipped")
        finally:
            self.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.active", "True")

    # --- Test 5: skipped when pixel_id is empty ---
    def test_05_send_purchase_skipped_when_pixel_id_empty(self):
        self.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.pixel_id", "")
        try:
            order = self._make_order()
            with patch("fayna_meta_capi.models.fayna_capi_service.requests.post") as mock_post:
                order.action_confirm()
                mock_post.assert_not_called()

            log = self.env["fayna.capi.event.log"].search(
                [("sale_order_id", "=", order.id)], limit=1
            )
            self.assertTrue(log)
            self.assertEqual(log.status, "skipped")
        finally:
            self.env["ir.config_parameter"].sudo().set_param(
                "fayna_meta_capi.pixel_id", "TEST_PIXEL_123"
            )

    # --- Test 6: skipped when access_token is empty ---
    def test_06_send_purchase_skipped_when_access_token_empty(self):
        self.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.access_token", "")
        try:
            order = self._make_order()
            with patch("fayna_meta_capi.models.fayna_capi_service.requests.post") as mock_post:
                order.action_confirm()
                mock_post.assert_not_called()

            log = self.env["fayna.capi.event.log"].search(
                [("sale_order_id", "=", order.id)], limit=1
            )
            self.assertTrue(log)
            self.assertEqual(log.status, "skipped")
        finally:
            self.env["ir.config_parameter"].sudo().set_param(
                "fayna_meta_capi.access_token", "TEST_TOKEN_ABC"
            )

    # --- Test 7: _build_user_data hashes email with SHA-256 ---
    def test_07_build_user_data_hashes_email(self):
        from fayna_meta_capi.models.fayna_capi_service import FaynaCAPIService

        partner = self.env["res.partner"].create(
            {"name": "Hash Test", "email": "User@Example.COM", "phone": False}
        )
        svc = FaynaCAPIService(self.env)
        data = svc._build_user_data(partner)

        self.assertIn("em", data)
        expected = _sha256("User@Example.COM")
        self.assertEqual(data["em"], [expected])
        self.assertNotIn("ph", data)

    # --- Test 8: _build_user_data handles missing email gracefully ---
    def test_08_build_user_data_missing_email(self):
        from fayna_meta_capi.models.fayna_capi_service import FaynaCAPIService

        partner = self.env["res.partner"].create(
            {"name": "No Email Partner", "email": False, "phone": False}
        )
        svc = FaynaCAPIService(self.env)
        data = svc._build_user_data(partner)

        self.assertNotIn("em", data)
        self.assertNotIn("ph", data)

    # --- Test 9: _build_user_data normalizes phone before hashing ---
    def test_09_build_user_data_normalizes_phone(self):
        from fayna_meta_capi.models.fayna_capi_service import FaynaCAPIService

        partner = self.env["res.partner"].create(
            {"name": "Phone Test", "email": False, "phone": "+48 123-456 789"}
        )
        svc = FaynaCAPIService(self.env)
        data = svc._build_user_data(partner)

        self.assertIn("ph", data)
        # Normalized: '+48123456789'
        normalized = "+48123456789"
        expected = _sha256(normalized)
        self.assertEqual(data["ph"], [expected])

    # --- Test 10: action_confirm triggers send_purchase and creates log ---
    def test_10_action_confirm_triggers_send_purchase(self):
        order = self._make_order(email="confirm@test.com", phone="+1 555 000 111")
        with patch("fayna_meta_capi.models.fayna_capi_service.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(200)
            order.action_confirm()

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            # Verify the URL contains our pixel id
            url = call_kwargs[0][0]
            self.assertIn("TEST_PIXEL_123", url)
            # Verify the payload event_name
            payload = call_kwargs[1]["json"]
            self.assertEqual(payload["data"][0]["event_name"], "Purchase")

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, "sent")
        self.assertEqual(log.event_name, "Purchase")
