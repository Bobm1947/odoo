# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.tools import formatLang

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    DEFAULT_APPROACHING_RATIO = 0.8

    credit_warning_level = fields.Selection(
        selection=[
            ('none', "None"),
            ('approaching', "Approaching"),
            ('over', "Over"),
        ],
        compute='_compute_credit_limit_warning_tier',
        default='none',
    )
    credit_limit_detail = fields.Text(
        compute='_compute_credit_limit_warning_tier')

    @api.depends(
        'company_id', 'partner_id', 'amount_total', 'currency_rate',
        'state')
    def _compute_credit_limit_warning_tier(self):
        for order in self:
            figures = order._get_credit_limit_figures()
            order.credit_warning_level = figures['level']
            order.credit_limit_detail = (
                order._build_credit_limit_detail(figures)
                if figures['level'] != 'none' else ''
            )

    def _get_credit_warning_ratio(self):
        """Return the "approaching" ratio, fail-soft validated to (0, 1].

        Reads the 'sale_credit_limit_warning.approaching_ratio' system
        parameter. On an unparseable or out-of-range value, falls back to
        DEFAULT_APPROACHING_RATIO and logs a warning with the raw parameter
        value and the fallback used - never the customer's financial
        figures.
        """
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'sale_credit_limit_warning.approaching_ratio',
            self.DEFAULT_APPROACHING_RATIO)
        try:
            ratio = float(raw)
        except (TypeError, ValueError):
            ratio = 0.0
        if not 0.0 < ratio <= 1.0:
            _logger.warning(
                "Invalid sale_credit_limit_warning.approaching_ratio %r; "
                "falling back to %s",
                raw, self.DEFAULT_APPROACHING_RATIO)
            return self.DEFAULT_APPROACHING_RATIO
        return ratio

    def _get_credit_limit_figures(self):
        """Return the credit figures for this order, in COMPANY currency.

        All partner credit fields (credit, credit_limit, credit_to_invoice)
        are restricted to account.group_account_invoice /
        account.group_account_readonly, so this reads them sudo'd -
        mirroring addons/sale/models/sale_order.py's own
        _compute_partner_credit_warning - to keep the banner visible to
        Sales users without Accounting access.
        """
        self.ensure_one()
        empty = {
            'credit_limit': 0.0, 'receivables': 0.0, 'current_amount': 0.0,
            'total_credit': 0.0, 'ratio': 0.0, 'level': 'none',
        }
        if (self.state not in ('draft', 'sent')
                or not self.company_id.account_use_credit_limit):
            return empty
        # sudo() -> read protected credit fields; with_company() ->
        # credit_limit is company_dependent and must be read in the
        # order's own company.
        order = self.sudo().with_company(self.company_id)
        partner = order.partner_id.commercial_partner_id
        credit_limit = partner.credit_limit
        if not credit_limit:
            return empty
        receivables = partner.credit + partner.credit_to_invoice
        current_amount = order.amount_total / (order.currency_rate or 1.0)
        total_credit = receivables + current_amount
        ratio = total_credit / credit_limit
        if total_credit > credit_limit:
            level = 'over'
        elif ratio >= order._get_credit_warning_ratio():
            level = 'approaching'
        else:
            level = 'none'
        return {
            'credit_limit': credit_limit, 'receivables': receivables,
            'current_amount': current_amount, 'total_credit': total_credit,
            'ratio': ratio, 'level': level,
        }

    def _build_credit_limit_detail(self, figures):
        """Render the tier-appropriate breakdown text.

        For the 'approaching' tier this includes a headline sentence and
        the total; for the 'over' tier those are omitted since core's own
        partner_credit_warning headline (rendered alongside, in the same
        banner) already covers them.
        """
        self.ensure_one()
        currency = self.company_id.currency_id

        def fmt(v):
            return formatLang(self.env, v, currency_obj=currency)

        lines = []
        if figures['level'] == 'approaching':
            lines.append(_(
                "%(partner_name)s is approaching its credit limit of "
                "%(credit_limit)s (%(ratio)s%% used).",
                partner_name=self.partner_id.commercial_partner_id.name,
                credit_limit=fmt(figures['credit_limit']),
                ratio=round(figures['ratio'] * 100),
            ))
        lines.append(_(
            "Outstanding receivables: %(amount)s",
            amount=fmt(figures['receivables'])))
        lines.append(_(
            "This order: %(amount)s",
            amount=fmt(figures['current_amount'])))
        if figures['level'] == 'approaching':
            lines.append(_(
                "Total amount due: %(amount)s",
                amount=fmt(figures['total_credit'])))
        return "\n".join(lines)
