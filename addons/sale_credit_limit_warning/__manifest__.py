# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sales Credit Limit Warning (Two-Tier)",
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Two-tier (approaching / exceeded) customer "
               "credit limit banner on Sales Orders",
    'description': """
Adds an 'approaching credit limit' tier to the Sales Order credit warning.

Odoo core shows a single yellow banner only once a customer has already
exceeded its credit limit. This module adds a second, earlier tier and
differentiates the two visually:

  * yellow  - the customer is at or above 80% of its credit limit
  * red     - the customer is over 100% of its credit limit

Both banners break the figure down into the credit limit, the outstanding
receivables and the current order's contribution.

The 80% threshold is configurable via the system parameter
'sale_credit_limit_warning.approaching_ratio'.

This module never modifies the Invoicing (account.move) credit warning.
    """,
    'depends': ['sale'],
    'data': [
        'data/ir_config_parameter.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
