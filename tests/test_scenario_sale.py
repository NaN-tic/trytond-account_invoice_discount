from decimal import Decimal
import unittest
from proteus import Model
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.modules.account.tests.tools import create_chart, get_accounts
from trytond.tests.tools import activate_modules
from trytond.tests.test_tryton import drop_db


class Test(unittest.TestCase):
    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test_account_invoice_discount(self):
        activate_modules(['sale_discount', 'account_invoice_discount'])

        create_company()
        company = get_company()

        create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create parties
        Party = Model.get('party.party')
        party = Party(name="Party")
        party.save()

        # Create product
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])

        ProductTemplate = Model.get('product.template')

        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.account_category = account_category
        template.salable = True
        template.save()
        product, = template.products

        # Create a sale
        Sale = Model.get('sale.sale')
        sale = Sale()
        sale.party = party
        sale.invoice_method = 'order'

        line = sale.lines.new()
        line.product = product
        line.quantity = 1

        line.base_price = Decimal('10.0000')
        line.discount_rate = Decimal('0.1')
        self.assertEqual(line.unit_price, Decimal('9.0000'))

        sale.click('quote')
        sale.click('confirm')

        self.assertEqual(sale.state, 'processing')

        invoice, = sale.invoices
        iline, = invoice.lines

        self.assertEqual(iline.base_price, Decimal('10.0000'))
        self.assertEqual(iline.unit_price, Decimal('9.0000'))
        self.assertEqual(iline.discount_amount, Decimal('1.0000'))
        self.assertEqual(iline.discount, '10%')

