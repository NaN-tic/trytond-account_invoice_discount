from trytond.modules.account_invoice.tests.tools import set_fiscalyear_invoice_sequences
from trytond.modules.account.tests.tools import create_fiscalyear, create_chart, get_accounts, create_tax
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.tools import activate_modules
from proteus import Model, Wizard
from decimal import Decimal
import unittest
from trytond.tests.test_tryton import drop_db


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):
        # Activate account_invoice_discount module
        activate_modules(['account_invoice_discount'])

        # Create company::
        _ = create_company()
        company = get_company()

        # Create fiscal year::
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts::
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']
        receivable = accounts['receivable']

        # Create tax::
        tax = create_tax(Decimal('.10'))
        tax.save()

        # Create party::
        Party = Model.get('party.party')
        party = Party(name='Party')
        party.save()

        # Create account category::
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.customer_taxes.append(tax)
        account_category.save()

        # Create product::
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

        # Create payment term::
        PaymentTerm = Model.get('account.invoice.payment_term')
        payment_term = PaymentTerm(name='Term')
        line = payment_term.lines.new(type='percent', ratio=Decimal('.5'))
        line.relativedeltas.new(days=20)
        line = payment_term.lines.new(type='remainder')
        line.relativedeltas.new(days=40)
        payment_term.save()

        # Create invoice::
        Invoice = Model.get('account.invoice')
        InvoiceLine = Model.get('account.invoice.line')
        invoice = Invoice()
        invoice.party = party
        invoice.payment_term = payment_term

        # Add line defining Gross Unit Price and Discount::
        line = InvoiceLine()
        invoice.lines.append(line)
        line.product = product
        line.account = revenue
        line.description = 'Test'
        line.quantity = 1
        line.base_price = Decimal('10.0000')
        line.discount_rate = Decimal('0.1')
        self.assertEqual(line.unit_price, Decimal('9.0000'))

        # Post invoice and check again invoice totals and taxes::
        invoice.click('post')
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.untaxed_amount, Decimal('9.00'))
        self.assertEqual(invoice.tax_amount, Decimal('0.90'))
        self.assertEqual(invoice.total_amount, Decimal('9.90'))
        receivable.reload()
        self.assertEqual(receivable.debit, Decimal('9.90'))
        self.assertEqual(receivable.credit, Decimal('0.00'))
        revenue.reload()
        self.assertEqual(revenue.debit, Decimal('0.00'))
        self.assertEqual(revenue.credit, Decimal('9.00'))
        line, = invoice.lines

        # Credit the invoice
        credit = Wizard('account.invoice.credit', [invoice])
        credit.form.with_refund = True
        credit.execute('credit')
        credit_invoice, = Invoice.find([('lines.origin', '=', line)])
        self.assertEqual(len(invoice.lines), len(credit_invoice.lines))
        credit_line, = credit_invoice.lines
        self.assertEqual(line.base_price, credit_line.base_price)
        self.assertEqual(line.unit_price, credit_line.unit_price)
