from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from .discount import DiscountFormatMixin


class SaleLine(DiscountFormatMixin, metaclass=PoolMeta):
    __name__ = 'sale.line'

    def get_invoice_line(self):
        lines = super().get_invoice_line()
        for line in lines:
            line.base_price = self.base_price
        return lines

    @fields.depends(
        'sale', '_parent_sale.company', '_parent_sale.currency',
        methods=['on_change_with_discount_rate',
            'on_change_with_discount_amount'])
    def on_change_with_discount(self, name=None):
        pool = Pool()
        Lang = pool.get('ir.lang')
        lang = Lang.get()
        company = self.sale and self.sale.company
        discount_format = company and company.discount_format
        rate = self.on_change_with_discount_rate()
        amount = self.on_change_with_discount_amount()
        currency = self.sale and self.sale.currency or self.currency
        if discount_format == 'percentage':
            return (self.format_discount_percentage(lang, rate)
                if rate else
                self.format_discount_amount(lang, amount, currency))
        if discount_format == 'amount':
            return self.format_discount_amount(lang, amount, currency)
        return super().on_change_with_discount(name=name)
