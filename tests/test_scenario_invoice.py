import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear, create_tax,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import \
    set_fiscalyear_invoice_sequences
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.modules.product import price_digits
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install account_invoice_discount module
        activate_modules('account_invoice_discount')

        # Create company
        _ = create_company()
        company = get_company()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        receivable = accounts['receivable']
        revenue = accounts['revenue']
        expense = accounts['expense']
        account_tax = accounts['tax']

        # Create tax
        tax = create_tax(Decimal('.10'))
        tax.save()

        # Create party
        Party = Model.get('party.party')
        party = Party(name='Party')
        party.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.customer_taxes.append(tax)
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'service'
        template.list_price = Decimal('20')
        template.account_category = account_category
        template.save()
        product, = template.products

        # Create payment term
        PaymentTerm = Model.get('account.invoice.payment_term')
        payment_term = PaymentTerm(name='Term')
        line = payment_term.lines.new(type='percent', ratio=Decimal('.5'))
        line.relativedeltas.new(days=20)
        line = payment_term.lines.new(type='remainder')
        line.relativedeltas.new(days=40)
        payment_term.save()

        # Create invoice
        Invoice = Model.get('account.invoice')
        InvoiceLine = Model.get('account.invoice.line')
        invoice = Invoice()
        invoice.party = party
        invoice.payment_term = payment_term

        # Add line defining Gross Unit Price and Discount (Unit Price is calculated)
        line = InvoiceLine()
        invoice.lines.append(line)
        line.account = revenue
        line.description = 'Test'
        line.quantity = 1
        line.discount = Decimal('0.2577')
        line.gross_unit_price = Decimal('25.153')
        self.assertEqual(line.unit_price, Decimal('18.6711'))
        self.assertEqual(line.amount, Decimal('18.67'))

        # Add line defining Unit Price and Discount, Gross Unit Price is calculated
        line = InvoiceLine()
        invoice.lines.append(line)
        line.product = product
        line.quantity = 5
        line.unit_price = Decimal('17.60')
        line.discount = Decimal('0.12')
        self.assertEqual(line.gross_unit_price, Decimal('20.0000'))
        self.assertEqual(line.amount, Decimal('88.00'))

        # Add line defining a discount of 100%. Despite of the List Price of product,

        # after set the Discount the Unit Price is recomputed to 0.
        line = InvoiceLine()
        invoice.lines.append(line)
        line.product = product
        line.quantity = 2
        line.unit_price = Decimal('20.00000000')
        line.gross_unit_price = Decimal('25.153')
        line.discount = Decimal('1.0')
        self.assertEqual(line.unit_price, Decimal(0))
        invoice.save()
        line = invoice.lines.pop()
        invoice.lines.append(line)
        self.assertEqual(abs(line.gross_unit_price.as_tuple().exponent),
                         price_digits[1])
        self.assertEqual(line.gross_unit_price, Decimal('25.1530'))
        self.assertEqual(line.discount, Decimal('1.0'))
        self.assertEqual(line.unit_price, Decimal(0))

        # Check invoice totals
        self.assertEqual(invoice.untaxed_amount, Decimal('106.67'))
        self.assertEqual(invoice.tax_amount, Decimal('8.80'))
        self.assertEqual(invoice.total_amount, Decimal('115.47'))

        # Post invoice and check again invoice totals and taxes
        invoice.click('post')
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.untaxed_amount, Decimal('106.67'))
        self.assertEqual(invoice.tax_amount, Decimal('8.80'))
        self.assertEqual(invoice.total_amount, Decimal('115.47'))
        receivable.reload()
        self.assertEqual(receivable.debit, Decimal('115.47'))

        self.assertEqual(receivable.credit, Decimal('0.00'))
        revenue.reload()
        self.assertEqual(revenue.debit, Decimal('0.00'))

        self.assertEqual(revenue.credit, Decimal('106.67'))
        account_tax.reload()
        self.assertEqual(account_tax.debit, Decimal('0.00'))

        self.assertEqual(account_tax.credit, Decimal('8.80'))

        # Discounts are copied when crediting the invoice
        credit = Wizard('account.invoice.credit', [invoice])
        credit.form.with_refund = True
        credit.execute('credit')
        credit_invoice, = credit.actions[0]
        self.assertEqual(tuple(l.discount for l in credit_invoice.lines),
                         (Decimal('0.2577'), Decimal('0.12'), Decimal('1.0')))
        self.assertEqual(credit_invoice.untaxed_amount, Decimal('-106.67'))
        self.assertEqual(credit_invoice.tax_amount, Decimal('-8.80'))
        self.assertEqual(credit_invoice.total_amount, Decimal('-115.47'))
