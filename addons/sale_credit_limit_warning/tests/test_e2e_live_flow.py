# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.fields import Command
from odoo.tests import Form, tagged
from odoo.tools.safe_eval import safe_eval

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestE2ELiveCreditLimitFlow(TestSaleCommon):
    """End-to-end regression guard for the two-tier credit limit banner.

    Complements test_two_tier_credit_limit.py (model boundary matrix) and
    test_view_and_access.py (static view assertions) with a live,
    onchange-driven walk of the full entry-to-success flow: editing an
    unsaved quotation's order lines across both thresholds, confirming an
    over-limit order, and reading tier-distinguishing text/ARIA role
    straight from the rendered view arch. Mirrors the Form()-driven style
    of addons/sale/tests/test_credit_limit.py::test_credit_limit_multicurrency
    and this addon's own test_view_and_access.py::_get_credit_warning_divs.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.account_use_credit_limit = True
        cls.partner_a.credit_limit = 100.0
        cls.sales_user = cls.company_data['default_user_salesman']

    def _get_credit_warning_divs(self):
        """Return the (over_div, approaching_div) xpath-inherited banner
        divs from the combined sale.order form view, mirroring
        test_view_and_access.py's helper of the same name."""
        arch = self.env['sale.order'].get_view(False, 'form')['arch']
        root = etree.fromstring(arch)
        over_divs = root.xpath("//field[@name='partner_credit_warning']/..")
        approaching_divs = root.xpath(
            "//div[.//field[@name='credit_warning_level']]")
        return over_divs[0], approaching_divs[0]

    def test_live_flow_crosses_thresholds_without_save(self):
        """AC-LIVE-1: editing order lines on an unsaved quotation crosses
        80%, then 100%, then drops back below 80% - and at each step the
        banner's live-computed fields update with no save required.

        Also asserts the yellow (approaching) and red (over) divs share
        the same structural wrapper shape (an <i> icon + the two banner
        fields), so the tier swap is a pure visibility/class toggle and
        never a reflow-causing structural change.
        """
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })

        with Form(order) as order_form:
            # Step 1: comfortably under the 80% threshold (50/100).
            with order_form.order_line.new() as sol:
                sol.product_id = self.company_data['product_order_no']
                sol.product_uom_qty = 1
                sol.price_unit = 50.0
                sol.tax_id.clear()
            self.assertEqual(order_form.credit_warning_level, 'none')
            self.assertFalse(order_form.credit_limit_detail)

            # Step 2: cross the 80% "approaching" threshold (90/100), still
            # unsaved.
            with order_form.order_line.edit(0) as sol:
                sol.price_unit = 90.0
            self.assertEqual(order_form.credit_warning_level, 'approaching')
            self.assertIn(
                "approaching its credit limit", order_form.credit_limit_detail)

            # Step 3: cross the 100% "over" threshold (150/100), still
            # unsaved.
            with order_form.order_line.edit(0) as sol:
                sol.price_unit = 150.0
            self.assertEqual(order_form.credit_warning_level, 'over')
            self.assertNotIn(
                "approaching its credit limit", order_form.credit_limit_detail)

            # Step 4: back down under the 80% threshold (40/100), proving
            # the live recompute is bidirectional, not one-way.
            with order_form.order_line.edit(0) as sol:
                sol.price_unit = 40.0
            self.assertEqual(order_form.credit_warning_level, 'none')
            self.assertFalse(order_form.credit_limit_detail)

        over_div, approaching_div = self._get_credit_warning_divs()
        # Same structural shape: one decorative icon + the two banner
        # fields, so switching tiers never changes the box's markup
        # skeleton (and therefore never reflows the surrounding form).
        self.assertEqual(len(over_div.xpath('.//i')), 1)
        self.assertEqual(len(approaching_div.xpath('.//i')), 1)
        self.assertEqual(
            len(over_div.xpath(".//field[@name='credit_limit_detail']")), 1)
        self.assertEqual(
            len(approaching_div.xpath(
                ".//field[@name='credit_limit_detail']")),
            1)

    def test_confirm_never_blocked_and_banner_absent_after_confirm(self):
        """AC-NAV-1: an over-limit quotation's action_confirm() succeeds
        (the banner is advisory only, never a blocker), and once state ==
        'sale' the banner is gone: credit_warning_level resets to 'none'
        and both view divs' invisible conditions evaluate True.

        Run as a non-Accounting Sales user (rather than the privileged
        default test user) so this also regression-guards the .sudo()
        elevation in _get_credit_limit_figures(): the pre-confirm 'over'
        read must succeed for this restricted user, and action_confirm()
        must not raise AccessError for them either.
        """
        for group in self.partner_a._fields['credit'].groups.split(','):
            self.assertFalse(self.sales_user.has_group(group))

        order = self.env['sale.order'].with_user(self.sales_user).create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 1,
                'price_unit': 150.0,
                'tax_id': False,
            })],
        })
        self.assertEqual(order.state, 'draft')
        self.assertEqual(order.credit_warning_level, 'over')

        # Must not raise AccessError / must not be blocked by the
        # over-limit banner, even for this restricted user.
        order.action_confirm()

        self.assertEqual(order.state, 'sale')
        self.assertEqual(order.credit_warning_level, 'none')
        self.assertFalse(order.credit_limit_detail)

        over_div, approaching_div = self._get_credit_warning_divs()
        eval_context = {'credit_warning_level': order.credit_warning_level}
        self.assertTrue(
            safe_eval(over_div.get('invisible'), eval_context),
            "Over-tier banner should be hidden once the order is confirmed")
        self.assertTrue(
            safe_eval(approaching_div.get('invisible'), eval_context),
            "Approaching-tier banner should be hidden once the order is "
            "confirmed")

    def test_tier_distinguishable_by_text_and_aria_role(self):
        """AC-A11Y-1: each tier is legible from text alone (the
        tier-specific verb phrase) AND carries the correct ARIA role -
        role="status" (polite) on the approaching div, role="alert"
        (assertive) on the over div - read straight from the view arch,
        so a future view edit that drops either cue fails this test."""
        over_div, approaching_div = self._get_credit_warning_divs()
        self.assertEqual(approaching_div.get('role'), 'status')
        self.assertEqual(over_div.get('role'), 'alert')

        approaching_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 1,
                'price_unit': 90.0,
                'tax_id': False,
            })],
        })
        self.assertEqual(approaching_order.credit_warning_level, 'approaching')
        self.assertIn(
            "approaching its credit limit",
            approaching_order.credit_limit_detail)
        self.assertNotIn(
            "has reached its credit limit",
            approaching_order.credit_limit_detail)

        over_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 1,
                'price_unit': 150.0,
                'tax_id': False,
            })],
        })
        self.assertEqual(over_order.credit_warning_level, 'over')
        self.assertIn(
            "has reached its credit limit", over_order.partner_credit_warning)
        self.assertNotIn(
            "approaching its credit limit", over_order.credit_limit_detail)
