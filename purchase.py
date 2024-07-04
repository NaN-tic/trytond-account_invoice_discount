from trytond.pool import PoolMeta


class PurchaseLine(metaclass=PoolMeta):
    __name__ = 'purchase.line'

    def get_invoice_line(self):
        lines = super().get_invoice_line()
        for line in lines:
            line.base_price = self.base_price
        return lines
            

