import json
import time
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Condition, RLock
from time import sleep
from typing import cast, List

from ExecutionSdk.execution import ExecutionSdk
from ExecutionSdk.order import Order

PORT = 4444  # TODO


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))  # TODO error handling
        order = Order(price = data['price'], order= data['order'])
        server = cast(AppServer, self.server)
        processor = server.add_order(order)
        response = processor()
        print(response)
        self.send_response(200)
        self.end_headers()


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


class ExecutionBatch:
    def __init__(self, batch_size):
        self._batch_size = batch_size
        self._cond = Condition()
        self._orders: List[Order] = []
        self._responses: List[Order] = []
        self._is_pending = True

    def add(self, order: Order) -> int:
        """
        :return: index of order in current batch
        NOTE: this method is single threaded
        """
        assert self._is_pending, "Can't add an order for an already used batch"
        next_index = len(self._orders)
        self._orders.append(order)
        return next_index

    def is_full(self):
        return len(self._orders) >= self._batch_size

    def process_execution(self, for_index: int) -> Order:
        """
        :param for_index: The index for which an execution is required
        NOTE: this method is multi-threading safe
        NOTE: this method may have a long wait, internally
        NOTE: two calls to this method should never have the same for_index for the same object
        """
        print(f'process_execution: {for_index}')
        with self._cond:
            if for_index == self._batch_size - 1:
                assert self._is_pending, "Can't add an order for an already used batch"
                assert self.is_full(), "Unexpected state: for_index incorrect "
                self._responses = ExecutionSdk.execute_orders(self._orders)
                self._is_pending = False
                self._cond.notify_all()
                return self._responses[for_index]

            self._cond.wait_for(lambda: not self._is_pending)
            return self._responses[for_index]


class AppServer(ThreadingSimpleServer):
    BATCH_SIZE = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._curr_batch = ExecutionBatch(self.BATCH_SIZE)
        self._batch_lock = RLock()

    def add_order(self, order: Order) -> (ExecutionBatch, int):  # TODO return partial callable?
        """
        :param order:
        :return: a callable object returning the execution result
        """
        with self._batch_lock:
            new_index = self._curr_batch.add(order)
            batch = self._curr_batch
            if self._curr_batch.is_full():
                self._curr_batch = ExecutionBatch(self.BATCH_SIZE)
            return partial(batch.process_execution, new_index)


def run():
    print('run')
    server = AppServer(('0.0.0.0', PORT), Handler)
    server.serve_forever()


if __name__ == '__main__':
    run()
