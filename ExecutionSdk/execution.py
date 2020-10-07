from time import sleep
from typing import List
from .order import Order


class ExecutionSdk:
    @staticmethod
    def execute_orders(orders: List[Order]):
        orders = orders.copy()
        sleep(10)  # TODO
        for order in orders:
            order.status = 'approved'
        return orders
