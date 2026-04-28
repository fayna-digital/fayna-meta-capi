from odoo.tests.common import TransactionCase


class TestScaffold(TransactionCase):
    """Smoke tests: module installs, feature flag seeded correctly."""

    def test_feature_flag_param_exists(self):
        """fayna_meta_capi.enabled param must exist (seeded by data/ir_config_parameter.xml)."""
        # The param exists — we don't assert the exact value here because other
        # test classes (e.g. TestFaynaCAPIBase) modify it in setUpClass.
        # The default is "False" per ir_config_parameter.xml.
        param = self.env["ir.config_parameter"].sudo().get_param("fayna_meta_capi.enabled")
        self.assertIsNotNone(param)
        self.assertIn(param, ("False", "True"), "enabled must be a boolean string")

    def test_module_installed(self):
        mod = self.env["ir.module.module"].search([("name", "=", "fayna_meta_capi")], limit=1)
        self.assertTrue(mod)
        self.assertIn(mod.state, ("installed", "to upgrade"))

    def test_abstract_model_registered(self):
        """fayna.meta.capi AbstractModel must be accessible via env."""
        svc = self.env["fayna.meta.capi"]
        self.assertIsNotNone(svc)

    def test_event_log_model_registered(self):
        self.assertIn("fayna.capi.event.log", self.env)

    def test_config_parameters_all_seeded(self):
        """All 5 ir.config_parameter keys must exist after module install."""
        icp = self.env["ir.config_parameter"].sudo()
        keys = [
            "fayna_meta_capi.enabled",
            "fayna_meta_capi.pixel_id",
            "fayna_meta_capi.access_token",
            "fayna_meta_capi.api_version",
            "fayna_meta_capi.test_event_code",
        ]
        for key in keys:
            val = icp.get_param(key)
            self.assertIsNotNone(val, f"ir.config_parameter {key!r} must be seeded")
