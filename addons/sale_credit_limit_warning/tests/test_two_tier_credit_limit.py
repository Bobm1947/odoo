# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import formatLang

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestTwoTierCreditLimit(TestSaleCommon):
    """Boundary matrix for sale.order.credit_warning_level /
    credit_limit_detail.

    Mirrors the fixture conventions of
    addons/sale/tests/test_credit_limit.py (post_install tagging,
    TestSaleCommon, company_data['product_order_no']).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.account_use_credit_limit = True
        cls.partner_a.credit_limit = 100.0

    def _create_order(self, price_unit):
        return self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 1,
                'price_unit': price_unit,
                'tax_id': False,
            })],
        })

    def test_no_credit_limit_set(self):
        """No credit_limit on the partner -> level is 'none',
        regardless of amount."""
        self.partner_a.credit_limit = 0.0
        order = self._create_order(150.0)
        self.assertEqual(order.credit_warning_level, 'none')
        self.assertEqual(order.credit_limit_detail, '')

    def test_credit_use_disabled(self):
        """Company-level account_use_credit_limit off -> level is 'none'."""
        self.env.company.account_use_credit_limit = False
        order = self._create_order(150.0)
        self.assertEqual(order.credit_warning_level, 'none')
        self.assertEqual(order.credit_limit_detail, '')

    def test_comfortably_under_threshold(self):
        """50% of limit -> level is 'none'."""
        order = self._create_order(50.0)
        self.assertEqual(order.credit_warning_level, 'none')
        self.assertEqual(order.credit_limit_detail, '')

    def test_exactly_80_percent_is_approaching(self):
        """Exactly 80.0% of limit -> level is 'approaching'
        (inclusive lower bound)."""
        order = self._create_order(80.0)
        self.assertEqual(order.credit_warning_level, 'approaching')
        self.assertTrue(order.credit_limit_detail)

    def test_between_80_and_100_percent_is_approaching(self):
        """90% of limit -> level is 'approaching'."""
        order = self._create_order(90.0)
        self.assertEqual(order.credit_warning_level, 'approaching')
        self.assertTrue(order.credit_limit_detail)

    def test_exactly_100_percent_stays_approaching(self):
        """Exactly 100.0% of limit -> level is still 'approaching',
        NOT 'over'.

        Core's own over-limit trigger (_build_credit_warning_message) is
        a strict `total_credit > credit_limit`, so equality must not tip
        into 'over'.
        """
        order = self._create_order(100.0)
        self.assertEqual(order.credit_warning_level, 'approaching')

    def test_just_over_100_percent_is_over(self):
        """100.01% of limit -> level is 'over'."""
        order = self._create_order(100.01)
        self.assertEqual(order.credit_warning_level, 'over')
        self.assertTrue(order.credit_limit_detail)

    def test_total_credit_parity_with_core_message(self):
        """Divergence tripwire: our total_credit, formatted, must appear
        inside core's own order.partner_credit_warning string when over
        limit."""
        order = self._create_order(150.0)
        figures = order._get_credit_limit_figures()
        self.assertEqual(figures['level'], 'over')
        formatted_total = formatLang(
            self.env, figures['total_credit'],
            currency_obj=self.env.company.currency_id)
        self.assertIn(formatted_total, order.partner_credit_warning)

    def test_invoicing_isolation_guardrail(self):
        """This module must never leak its severity fields onto
        account.move."""
        self.assertNotIn(
            'credit_warning_level', self.env['account.move']._fields)
        self.assertNotIn(
            'credit_limit_detail', self.env['account.move']._fields)
