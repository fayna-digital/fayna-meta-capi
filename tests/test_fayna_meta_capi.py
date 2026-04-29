"""
Tests for fayna_meta_capi — Meta Conversions API adapter.

All HTTP calls are mocked via unittest.mock.patch; no real network traffic.
Tests cover: AbstractModel API, payload construction, hashing, feature-flag
gating, Purchase/Lead/ViewContent events, timeout handling, log creation,
external_id in user_data, retry cron logic.
"""

import hashlib
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


def _sha256(val: str) -> str:
    return hashlib.sha256(val.strip().lower().encode()).hexdigest()


_PATCH = "fayna_meta_capi.models.fayna_capi_service.requests.post"


class TestFaynaCAPIBase(TransactionCase):
    """Shared setUp for all CAPI tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        params = cls.env["ir.config_parameter"].sudo()
        params.set_param("fayna_meta_capi.enabled", "True")
        params.set_param("fayna_meta_capi.pixel_id", "TEST_PIXEL_123")
        params.set_param("fayna_meta_capi.access_token", "TEST_TOKEN_ABC")
        params.set_param("fayna_meta_capi.api_version", "v19.0")
        params.set_param("fayna_meta_capi.test_event_code", "")

    def _make_order(self, email="test@example.com", phone="+48 123 456 789"):
        partner = self.env["res.partner"].create(
            {"name": "Test Partner", "email": email, "phone": phone}
        )
        product = self.env["product.product"].create(
            {"name": "Camp Ticket", "type": "service", "list_price": 500.0}
        )
        return self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 1, "price_unit": 500.0})
                ],
            }
        )

    @staticmethod
    def _mock_response(status_code=200, text="{}"):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.text = text
        return mock_resp


# ── Test 1: log status=sent on HTTP 200 ─────────────────────────────────────


class TestPurchaseEvent(TestFaynaCAPIBase):
    def test_01_log_created_status_sent_on_http_200(self):
        order = self._make_order()
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log, "Log record must be created")
        self.assertEqual(log.status, "sent")
        self.assertEqual(log.http_status, 200)
        self.assertFalse(log.error_message)

    # ── Test 2: log status=failed on HTTP 400 ───────────────────────────────

    def test_02_log_created_status_failed_on_http_400(self):
        order = self._make_order()
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(400, "Bad Request")
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, "failed")
        self.assertEqual(log.http_status, 400)
        self.assertIn("Bad Request", log.error_message)

    # ── Test 3: log status=failed on network exception ───────────────────────

    def test_03_log_created_status_failed_on_network_exception(self):
        import requests as req_lib

        order = self._make_order()
        with patch(_PATCH) as mock_post:
            mock_post.side_effect = req_lib.RequestException("Connection refused")
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, "failed")
        self.assertEqual(log.http_status, 0)
        self.assertIn("Connection refused", log.error_message)

    # ── Test 4: skipped when enabled=False ───────────────────────────────────

    def test_04_send_purchase_skipped_when_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.enabled", "False")
        try:
            order = self._make_order()
            with patch(_PATCH) as mock_post:
                order.action_confirm()
                mock_post.assert_not_called()

            log = self.env["fayna.capi.event.log"].search(
                [("sale_order_id", "=", order.id)], limit=1
            )
            self.assertTrue(log)
            self.assertEqual(log.status, "skipped")
        finally:
            self.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.enabled", "True")

    # ── Test 5: skipped when pixel_id is empty ──────────────────────────────

    def test_05_send_purchase_skipped_when_pixel_id_empty(self):
        self.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.pixel_id", "")
        try:
            order = self._make_order()
            with patch(_PATCH) as mock_post:
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

    # ── Test 6: skipped when access_token is empty ──────────────────────────

    def test_06_send_purchase_skipped_when_access_token_empty(self):
        self.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.access_token", "")
        try:
            order = self._make_order()
            with patch(_PATCH) as mock_post:
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

    # ── Test 7: action_confirm → correct pixel_id in URL + event_name ───────

    def test_07_action_confirm_triggers_send_purchase(self):
        order = self._make_order(email="confirm@test.com", phone="+1 555 000 111")
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            order.action_confirm()

            mock_post.assert_called_once()
            url = mock_post.call_args[0][0]
            self.assertIn("TEST_PIXEL_123", url)
            payload = mock_post.call_args[1]["json"]
            self.assertEqual(payload["data"][0]["event_name"], "Purchase")

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, "sent")
        self.assertEqual(log.event_name, "Purchase")


# ── Test 8–11: hashing helpers ───────────────────────────────────────────────


class TestHashingHelpers(TestFaynaCAPIBase):
    def _svc(self):
        return self.env["fayna.meta.capi"]

    def test_08_hash_value_lowercases_and_strips(self):
        svc = self._svc()
        result = svc._hash_value("  User@Example.COM  ")
        self.assertEqual(result, _sha256("user@example.com"))

    def test_09_hash_value_empty_returns_empty_string(self):
        svc = self._svc()
        self.assertEqual(svc._hash_value(""), "")
        self.assertEqual(svc._hash_value(None), "")

    def test_10_build_user_data_hashes_email(self):
        svc = self._svc()
        partner = self.env["res.partner"].create(
            {"name": "Hash Test", "email": "User@Example.COM", "phone": False}
        )
        data = svc._build_user_data(partner)
        self.assertIn("em", data)
        self.assertEqual(data["em"], [_sha256("User@Example.COM")])
        self.assertNotIn("ph", data)

    def test_11_build_user_data_normalizes_phone(self):
        svc = self._svc()
        partner = self.env["res.partner"].create(
            {"name": "Phone Test", "email": False, "phone": "+48 123-456 789"}
        )
        data = svc._build_user_data(partner)
        self.assertIn("ph", data)
        # Normalized: '+48123456789' then SHA-256 with lower+strip
        normalized = "+48123456789"
        self.assertEqual(data["ph"], [_sha256(normalized)])

    def test_12_build_user_data_missing_email_and_phone(self):
        svc = self._svc()
        partner = self.env["res.partner"].create(
            {"name": "No Contact Partner", "email": False, "phone": False}
        )
        data = svc._build_user_data(partner)
        self.assertNotIn("em", data)
        self.assertNotIn("ph", data)


# ── Test 13: Lead event ───────────────────────────────────────────────────────


class TestLeadEvent(TestFaynaCAPIBase):
    def test_13_send_lead_creates_log_with_status_sent(self):
        partner = self.env["res.partner"].create(
            {"name": "Lead Partner", "email": "lead@campscout.eu"}
        )
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            result = self.env["fayna.meta.capi"].send_lead(partner, "https://campscout.eu/contact")

        self.assertTrue(result)
        log = self.env["fayna.capi.event.log"].search(
            [("event_name", "=", "Lead")], order="id desc", limit=1
        )
        self.assertTrue(log)
        self.assertEqual(log.status, "sent")


# ── Test 14: ViewContent event ────────────────────────────────────────────────


class TestViewContentEvent(TestFaynaCAPIBase):
    def test_14_send_view_content_creates_log_with_status_sent(self):
        partner = self.env["res.partner"].create({"name": "Viewer", "email": "view@campscout.eu"})
        product = self.env["product.product"].create(
            {"name": "Camp PSH", "type": "service", "list_price": 1200.0}
        )
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            result = self.env["fayna.meta.capi"].send_view_content(
                partner, product, "https://campscout.eu/shop/cs-psh-26"
            )

        self.assertTrue(result)
        log = self.env["fayna.capi.event.log"].search(
            [("event_name", "=", "ViewContent")], order="id desc", limit=1
        )
        self.assertTrue(log)
        self.assertEqual(log.status, "sent")


# ── Test 15: get_config returns correct keys ─────────────────────────────────


class TestGetConfig(TestFaynaCAPIBase):
    def test_15_get_config_returns_all_keys(self):
        cfg = self.env["fayna.meta.capi"]._get_config()
        self.assertIn("pixel_id", cfg)
        self.assertIn("access_token", cfg)
        self.assertIn("api_version", cfg)
        self.assertIn("test_event_code", cfg)
        self.assertIn("enabled", cfg)
        self.assertEqual(cfg["pixel_id"], "TEST_PIXEL_123")
        self.assertEqual(cfg["api_version"], "v19.0")
        self.assertTrue(cfg["enabled"])


# ── Test 16: test_event_code injected into payload ───────────────────────────


class TestTestEventCode(TestFaynaCAPIBase):
    def test_16_test_event_code_injected_into_payload(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "fayna_meta_capi.test_event_code", "TEST99999"
        )
        try:
            order = self._make_order(email="tec@test.com")
            with patch(_PATCH) as mock_post:
                mock_post.return_value = self._mock_response(200)
                order.action_confirm()
                payload = mock_post.call_args[1]["json"]
                self.assertEqual(payload.get("test_event_code"), "TEST99999")
        finally:
            self.env["ir.config_parameter"].sudo().set_param("fayna_meta_capi.test_event_code", "")


# ── Test 17: send_event generic API ──────────────────────────────────────────


class TestSendEventGenericAPI(TestFaynaCAPIBase):
    def test_17_send_event_returns_true_on_200(self):
        svc = self.env["fayna.meta.capi"]
        partner = self.env["res.partner"].create({"name": "Generic", "email": "generic@test.com"})
        user_data = svc._build_user_data(partner)
        custom_data = {"currency": "PLN", "value": 100.0}
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            result = svc.send_event("Purchase", user_data, custom_data, "https://example.com")
        self.assertTrue(result)


# ── Test 18-20: payload + response stored in log ──────────────────────────────


class TestLogPayloadAndResponse(TestFaynaCAPIBase):
    def test_18_log_stores_payload_json_on_success(self):
        """Log record must contain the JSON payload sent to Meta (without access_token)."""
        import json as _json

        order = self._make_order(email="payload@test.com")
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200, '{"events_received": 1}')
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertTrue(log.payload, "payload field must be set")
        parsed = _json.loads(log.payload)
        # access_token must NOT be stored in log (security)
        self.assertNotIn("access_token", parsed)
        # data array must contain the Purchase event
        self.assertIn("data", parsed)
        self.assertEqual(parsed["data"][0]["event_name"], "Purchase")

    def test_19_log_stores_response_text_on_success(self):
        """Log record must contain the raw response body from Meta API."""
        order = self._make_order(email="response@test.com")
        meta_response = '{"events_received": 1, "fbtrace_id": "ABC123"}'
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200, meta_response)
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.response, meta_response)

    def test_20_log_stores_payload_on_network_error(self):
        """Even on network error, the payload we tried to send must be in the log."""
        import json as _json  # noqa: PLC0415, I001
        import requests as req_lib  # noqa: PLC0415

        order = self._make_order(email="neterr@test.com")
        with patch(_PATCH) as mock_post:
            mock_post.side_effect = req_lib.ConnectionError("timeout")
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, "failed")
        self.assertTrue(log.payload, "payload must be stored even on network error")
        parsed = _json.loads(log.payload)
        self.assertNotIn("access_token", parsed)
        self.assertIsNone(log.response)


# ── Test 21: settings config round-trip ──────────────────────────────────────


class TestSettingsConfigRoundTrip(TestFaynaCAPIBase):
    def test_21_config_params_round_trip(self):
        """ir.config_parameter values must survive write → read cycle."""
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("fayna_meta_capi.pixel_id", "999888777666555")
        icp.set_param("fayna_meta_capi.access_token", "EAATestTokenRoundTrip")
        icp.set_param("fayna_meta_capi.test_event_code", "TESTRT42")
        icp.set_param("fayna_meta_capi.api_version", "v18.0")
        icp.set_param("fayna_meta_capi.enabled", "True")
        try:
            cfg = self.env["fayna.meta.capi"]._get_config()
            self.assertEqual(cfg["pixel_id"], "999888777666555")
            self.assertEqual(cfg["access_token"], "EAATestTokenRoundTrip")
            self.assertEqual(cfg["test_event_code"], "TESTRT42")
            self.assertEqual(cfg["api_version"], "v18.0")
            self.assertTrue(cfg["enabled"])
        finally:
            icp.set_param("fayna_meta_capi.pixel_id", "TEST_PIXEL_123")
            icp.set_param("fayna_meta_capi.access_token", "TEST_TOKEN_ABC")
            icp.set_param("fayna_meta_capi.test_event_code", "")
            icp.set_param("fayna_meta_capi.api_version", "v19.0")


# ── Test 22: access_token never appears in URL ────────────────────────────────


class TestSecurityInvariants(TestFaynaCAPIBase):
    def test_22_access_token_not_in_request_url(self):
        """access_token must go in JSON body only, never in the URL."""
        order = self._make_order(email="sec@test.com")
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            order.action_confirm()

            url = mock_post.call_args[0][0]
            self.assertNotIn("TEST_TOKEN_ABC", url)
            # access_token must be present in body json
            body = mock_post.call_args[1]["json"]
            self.assertEqual(body["access_token"], "TEST_TOKEN_ABC")


# ── Test 23: external_id (SHA-256 of partner.id) present in user_data ─────────


class TestExternalIdInUserData(TestFaynaCAPIBase):
    def test_23_external_id_hashed_partner_id_in_user_data(self):
        """user_data must include external_id = SHA-256(str(partner.id))."""
        svc = self.env["fayna.meta.capi"]
        partner = self.env["res.partner"].create(
            {"name": "ExtID Test", "email": "extid@campscout.eu"}
        )
        data = svc._build_user_data(partner)
        self.assertIn("external_id", data)
        expected = _sha256(str(partner.id))
        self.assertEqual(data["external_id"], [expected])

    def test_24_external_id_present_in_purchase_payload(self):
        """Purchase payload sent to Meta must contain user_data.external_id."""
        order = self._make_order(email="extid_purchase@test.com")
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            order.action_confirm()

        payload = mock_post.call_args[1]["json"]
        user_data = payload["data"][0]["user_data"]
        self.assertIn("external_id", user_data)
        self.assertTrue(user_data["external_id"], "external_id must be non-empty list")


# ── Test 25–26: retry cron logic ──────────────────────────────────────────────


class TestRetryCron(TestFaynaCAPIBase):
    def test_25_failed_log_retry_count_increments(self):
        """action_retry_failed must increment retry_count on the log record."""
        import requests as req_lib

        order = self._make_order(email="retry@test.com")
        with patch(_PATCH) as mock_post:
            mock_post.side_effect = req_lib.RequestException("timeout")
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, "failed")
        self.assertEqual(log.retry_count, 0)

        # Now retry — mock success
        with patch(_PATCH) as mock_post2:
            mock_post2.return_value = self._mock_response(200)
            log.action_retry_failed()

        self.assertEqual(log.retry_count, 1)

    def test_26_cron_retry_stops_after_max_retries(self):
        """cron must not retry a log record that already hit retry_count=3."""
        import requests as req_lib

        order = self._make_order(email="maxretry@test.com")
        with patch(_PATCH) as mock_post:
            mock_post.side_effect = req_lib.RequestException("timeout")
            order.action_confirm()

        log = self.env["fayna.capi.event.log"].search([("sale_order_id", "=", order.id)], limit=1)
        self.assertTrue(log)
        # Fast-forward retry_count to max
        log.sudo().write({"retry_count": 3})

        with patch(_PATCH) as mock_post2:
            self.env["fayna.capi.event.log"].cron_retry_failed_events()
            # Must not have been called — already at max retries
            mock_post2.assert_not_called()


# ── Test 27–29: AddToCart event ───────────────────────────────────────────────


class TestAddToCartEvent(TestFaynaCAPIBase):
    def _make_order_line(self, email="atc@example.com"):
        partner = self.env["res.partner"].create(
            {"name": "ATC Partner", "email": email}
        )
        product = self.env["product.product"].create(
            {"name": "Camp Slot", "type": "service", "list_price": 750.0}
        )
        order = self.env["sale.order"].create({"partner_id": partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": 1,
                "price_unit": 750.0,
            }
        )
        return line

    def test_27_send_add_to_cart_returns_true_on_200(self):
        """send_add_to_cart must return True when Meta API responds 200."""
        line = self._make_order_line()
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            result = self.env["fayna.meta.capi"].send_add_to_cart(line)
        self.assertTrue(result)

    def test_28_send_add_to_cart_creates_log_with_event_name(self):
        """send_add_to_cart must create a log record with event_name='AddToCart'."""
        line = self._make_order_line(email="atc2@example.com")
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            self.env["fayna.meta.capi"].send_add_to_cart(line)

        log = self.env["fayna.capi.event.log"].search(
            [("event_name", "=", "AddToCart")], order="id desc", limit=1
        )
        self.assertTrue(log, "Log record must be created for AddToCart event")
        self.assertEqual(log.status, "sent")
        self.assertEqual(log.event_name, "AddToCart")

    def test_29_send_add_to_cart_payload_contains_product_id(self):
        """AddToCart payload must include content_ids with the product id."""
        line = self._make_order_line(email="atc3@example.com")
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            self.env["fayna.meta.capi"].send_add_to_cart(line)

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        custom_data = payload["data"][0]["custom_data"]
        self.assertIn("content_ids", custom_data)
        self.assertEqual(custom_data["content_ids"], [str(line.product_id.id)])
        self.assertEqual(custom_data["currency"], line.currency_id.name)


# ── Test 30–31: InitiateCheckout event ───────────────────────────────────────


class TestInitiateCheckoutEvent(TestFaynaCAPIBase):
    def test_30_send_initiate_checkout_returns_true_on_200(self):
        """send_initiate_checkout must return True when Meta API responds 200."""
        order = self._make_order(email="checkout@example.com")
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            result = self.env["fayna.meta.capi"].send_initiate_checkout(order)
        self.assertTrue(result)

    def test_31_send_initiate_checkout_payload_structure(self):
        """InitiateCheckout payload must contain event_name, num_items, content_ids."""
        order = self._make_order(email="checkout2@example.com")
        with patch(_PATCH) as mock_post:
            mock_post.return_value = self._mock_response(200)
            result = self.env["fayna.meta.capi"].send_initiate_checkout(order)

        self.assertTrue(result)
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        event = payload["data"][0]
        self.assertEqual(event["event_name"], "InitiateCheckout")
        custom_data = event["custom_data"]
        self.assertIn("num_items", custom_data)
        self.assertIn("content_ids", custom_data)
        self.assertIn("value", custom_data)
        self.assertIn("currency", custom_data)
        self.assertEqual(custom_data["num_items"], len(order.order_line))
        self.assertEqual(
            custom_data["content_ids"],
            [str(line.product_id.id) for line in order.order_line],
        )
