# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .commission import *
from .invoice import *


def register():
    Pool.register(
        InvoiceLine,
        Commission,
        module='account_invoice_discount', type_='model')
