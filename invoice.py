# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.modules.currency.fields import Monetary
from trytond.modules.product import price_digits, round_price

STATES = {
    'invisible': Eval('type') != 'line',
    'required': Eval('type') == 'line',
    'readonly': Eval('invoice_state') != 'draft',
    }


class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'

    base_price = Monetary(
        "Base Price", currency='currency', digits=price_digits,
        states={
            'invisible': Eval('type') != 'line',
            'readonly': Eval('invoice_state') != 'draft',
            })

    discount_rate = fields.Function(fields.Numeric(
            "Discount Rate", digits=(16, 4),
            states={
                'invisible': Eval('type') != 'line',
                'readonly': Eval('invoice_state') != 'draft',
                }),
        'on_change_with_discount_rate', setter='set_discount_rate')
    discount_amount = fields.Function(Monetary(
            "Discount Amount", currency='currency', digits=price_digits,
            states={
                'invisible': Eval('type') != 'line',
                'readonly': Eval('invoice_state') != 'draft',
                }),
        'on_change_with_discount_amount', setter='set_discount_amount')

    discount = fields.Function(fields.Char(
            "Discount",
            states={
                'invisible': ~Eval('discount'),
                }),
        'on_change_with_discount')

    @classmethod
    def __register__(cls, module_name):
        # Rename gross_unit_price to base_price
        table = cls.__table_handler__(module_name)
        if table.column_exist('gross_unit_price') and not table.column_exist('base_price'):
            table.column_rename('gross_unit_price', 'base_price')
        super().__register__(module_name)

    @fields.depends(methods=['on_change_with_discount_rate',
            'on_change_with_discount_amount', 'on_change_with_discount'])
    def on_change_product(self):
        super().on_change_product()
        if self.product:
            self.discount_rate = self.on_change_with_discount_rate()
            self.discount_amount = self.on_change_with_discount_amount()
            self.discount = self.on_change_with_discount()

    @fields.depends('unit_price', 'base_price')
    def on_change_with_discount_rate(self, name=None):
        if self.unit_price is None or not self.base_price:
            return
        rate = 1 - self.unit_price / self.base_price
        return rate.quantize(
            Decimal(1) / 10 ** self.__class__.discount_rate.digits[1])

    @fields.depends('base_price', 'discount_rate',
        methods=['on_change_with_discount_amount', 'on_change_with_discount',
            'on_change_with_amount'])
    def on_change_discount_rate(self):
        if self.base_price is not None and self.discount_rate is not None:
            self.unit_price = round_price(
                self.base_price * (1 - self.discount_rate))
            self.discount_amount = self.on_change_with_discount_amount()
            self.discount = self.on_change_with_discount()
            self.amount = self.on_change_with_amount()

    @classmethod
    def set_discount_rate(cls, lines, name, value):
        pass

    @fields.depends('unit_price', 'base_price')
    def on_change_with_discount_amount(self, name=None):
        if self.unit_price is None or self.base_price is None:
            return
        return round_price(self.base_price - self.unit_price)

    @fields.depends(
        'base_price', 'discount_amount',
        methods=['on_change_with_discount_rate', 'on_change_with_discount',
            'on_change_with_amount'])
    def on_change_discount_amount(self):
        if self.base_price is not None and self.discount_amount is not None:
            self.unit_price = round_price(
                self.base_price - self.discount_amount)
            self.discount_rate = self.on_change_with_discount_rate()
            self.discount = self.on_change_with_discount()
            self.amount = self.on_change_with_amount()

    @classmethod
    def set_discount_amount(cls, lines, name, value):
        pass

    @fields.depends('invoice', 'currency', '_parent_invoice.currency',
        methods=[
            'on_change_with_discount_rate', 'on_change_with_discount_amount'])
    def on_change_with_discount(self, name=None):
        pool = Pool()
        Lang = pool.get('ir.lang')
        lang = Lang.get()
        rate = self.on_change_with_discount_rate()
        if not rate or rate % Decimal('0.01'):
            amount = self.on_change_with_discount_amount()
            currency = self.invoice and self.invoice.currency or self.currency
            if amount and currency:
                return lang.currency(amount, currency, digits=price_digits[1])
        else:
            return lang.format('%i', rate * 100) + '%'

    def _credit(self):
        line = super()._credit()
        if self.base_price is not None:
            line.base_price = self.base_price
        return line

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('/form//label[@id="discount"]', 'states', {
                'invisible': Eval('type') != 'line',
                }, ['type']),
            ]
