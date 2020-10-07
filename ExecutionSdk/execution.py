import random
from typing import List

from .order import Order


class ExecutionSdk:
    @staticmethod
    def execute_orders(orders: List[Order]):
        orders = orders.copy()
        for order in orders:
            order.status = random.choice(['approved', 'declined'])
        return orders
