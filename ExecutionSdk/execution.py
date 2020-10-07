from typing import List
from .order import Order


class ExecutionSdk:
    @staticmethod
    def execute_orders(orders: List[Order]):
        orders = orders.copy()
        for order in orders:
            # print(f'-->> {order}')
            order.status = 'approved'
            # print(f'++>> {order}')
        return orders
