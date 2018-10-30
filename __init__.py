# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import commission
from . import invoice


def register():
    Pool.register(
        invoice.InvoiceLine,
        commission.Commission,
        module='account_invoice_discount', type_='model')
