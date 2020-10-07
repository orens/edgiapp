from random import random

from ExecutionSdk.execution import ExecutionSdk
from ExecutionSdk.order import Order
from appserver.server import run as run_server


def main():
    # orders = [Order(random(), random()) for _ in range(2)]
    # print('Orders\n' + '\n'.join(str(x) for x in orders))
    # approved = ExecutionSdk.execute_orders(orders)
    # print('Approved Orders\n' + '\n'.join(str(x) for x in approved))
    run_server()


if __name__ == '__main__':
    main()
