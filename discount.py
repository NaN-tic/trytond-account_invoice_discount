# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from decimal import Decimal
from trytond.modules.product import price_digits


class DiscountFormatMixin:
    __slots__ = ()

    def format_discount_amount(self, lang, amount, currency):
        if amount:
            if currency:
                return lang.currency(amount, currency, digits=price_digits[1])
            return lang.format_number(
                amount, digits=price_digits[1], monetary=True)

    def format_discount_percentage(self, lang, rate):
        if rate is not None:
            digits = self.__class__.discount_rate.digits[1]
            rate = rate.quantize(Decimal(1) / 10 ** digits)
            return lang.format_number(rate * 100, digits=digits) + '%'
