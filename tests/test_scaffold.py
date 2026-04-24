from odoo.tests.common import TransactionCase


class TestScaffold(TransactionCase):
    """Placeholder tests proving the module installs and the feature flag
    is seeded correctly. Real behaviour arrives in Phase 4 increments
    per master TZ §16."""

    def test_feature_flag_seeded_as_disabled(self):
        param = self.env["ir.config_parameter"].sudo().get_param("fayna_meta_capi.active")
        self.assertEqual(param, "False")

    def test_module_installed(self):
        mod = self.env["ir.module.module"].search([("name", "=", "fayna_meta_capi")], limit=1)
        self.assertTrue(mod)
        self.assertIn(mod.state, ("installed", "to upgrade"))
