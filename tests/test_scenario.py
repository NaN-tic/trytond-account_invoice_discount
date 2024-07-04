from decimal import Decimal
import unittest
from proteus import Model
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.modules.account.tests.tools import create_chart, get_accounts
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):
    def test_account_invoice_discount(self):
        activate_modules('account_invoice_discount')
        
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
        template.save()
        product, = template.products
        
        # Create a purchase
        Invoice = Model.get('account.invoice')
        invoice = Invoice()
        invoice.party = party
        line = invoice.lines.new()
        line.product = product
        line.quantity = 1
        self.assertEqual(line.base_price, None)
        self.assertEqual(line.unit_price, None)
        
        # Set a discount of 10%
        line.base_price = Decimal('10.0000')
        line.discount_rate = Decimal('0.1')
        self.assertEqual(line.unit_price, Decimal('9.0000'))
        self.assertEqual(line.discount_amount, Decimal('1.0000'))
        self.assertEqual(line.discount, '10%')
    
        invoice.save()
        line, = invoice.lines
        self.assertEqual(line.unit_price, Decimal('9.0000'))
        self.assertEqual(line.discount_amount, Decimal('1.0000'))
        self.assertEqual(line.discount, '10%')
        
        # Set a discount amount
        line.discount_amount = Decimal('3.3333')
        self.assertEqual(line.unit_price, Decimal('6.6667'))
        self.assertEqual(line.discount_rate, Decimal('0.3333'))
        self.assertEqual(line.discount, '$3.3333')

