# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools.safe_eval import safe_eval

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestTwoTierCreditLimitView(TestSaleCommon):
    """View-layer coverage for the two-tier credit limit banner.

    Complements test_two_tier_credit_limit.py (model/compute layer) with
    assertions on the xpath-inherited sale.order form view: correct
    Bootstrap alert classes per tier, both banners hidden when the level
    is 'none', and access-rights parity for non-Accounting Sales users
    (AC-ERROR-1 regression guard).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.account_use_credit_limit = True
        cls.partner_a.credit_limit = 100.0
        cls.sales_user = cls.company_data['default_user_salesman']

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

    def _get_credit_warning_divs(self):
        """Return the two xpath-inherited banner divs from the combined
        sale.order form view, keyed by their invisible expression."""
        arch = self.env['sale.order'].get_view(False, 'form')['arch']
        root = etree.fromstring(arch)
        divs = root.xpath("//field[@name='partner_credit_warning']/..")
        divs += root.xpath(
            "//div[.//field[@name='credit_warning_level']]")
        return divs

    def test_view_alert_classes_per_tier(self):
        """The 'over' tier div is alert-danger, the 'approaching' tier
        (new sibling) div is alert-warning, and the combined view is
        valid (no broken xpath - Odoo validates on get_view/install)."""
        arch = self.env['sale.order'].get_view(False, 'form')['arch']
        root = etree.fromstring(arch)

        over_divs = root.xpath("//field[@name='partner_credit_warning']/..")
        self.assertEqual(len(over_divs), 1)
        over_div = over_divs[0]
        self.assertIn('alert-danger', over_div.get('class'))
        self.assertNotIn('alert-warning', over_div.get('class'))
        self.assertEqual(
            over_div.get('invisible'), "credit_warning_level != 'over'")

        approaching_divs = root.xpath(
            "//div[.//field[@name='credit_warning_level']]")
        self.assertEqual(len(approaching_divs), 1)
        approaching_div = approaching_divs[0]
        self.assertIn('alert-warning', approaching_div.get('class'))
        self.assertNotIn('alert-danger', approaching_div.get('class'))
        self.assertEqual(
            approaching_div.get('invisible'),
            "credit_warning_level != 'approaching'")

    def test_view_both_banners_hidden_when_level_none(self):
        """Both divs' invisible expressions evaluate True (hidden) for a
        fresh, comfortably-under-threshold order (credit_warning_level ==
        'none')."""
        order = self._create_order(50.0)
        self.assertEqual(order.credit_warning_level, 'none')

        over_div, approaching_div = self._get_credit_warning_divs()
        eval_context = {'credit_warning_level': order.credit_warning_level}
        self.assertTrue(
            safe_eval(over_div.get('invisible'), eval_context),
            "Over-tier banner should be hidden when level is 'none'")
        self.assertTrue(
            safe_eval(approaching_div.get('invisible'), eval_context),
            "Approaching-tier banner should be hidden when level is 'none'")

    def test_credit_warning_fields_readable_without_accounting_access(self):
        """A Sales user without Accounting access can still read the
        computed credit_warning_level / credit_limit_detail with a
        non-'none' value when the partner is over limit (regression guard
        for AC-ERROR-1: Phase 1's .sudo() elevation must survive Phase 2's
        view changes)."""
        for group in self.partner_a._fields['credit'].groups.split(','):
            self.assertFalse(self.sales_user.has_group(group))

        order = self._create_order(150.0).with_user(self.sales_user)
        self.assertEqual(order.credit_warning_level, 'over')
        self.assertTrue(order.credit_limit_detail)
