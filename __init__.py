# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import company
from . import invoice
from . import purchase
from . import sale

def register():
    Pool.register(
        company.Company,
        invoice.InvoiceLine,
        module='account_invoice_discount', type_='model')
    Pool.register(
        purchase.PurchaseLine,
        module='account_invoice_discount', type_='model',
        depends=['purchase_discount'])
    Pool.register(
        sale.SaleLine,
        module='account_invoice_discount', type_='model',
        depends=['sale_discount'])
