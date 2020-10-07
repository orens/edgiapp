import json
import os
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Condition, RLock
from typing import cast, List, Callable, Optional

from ExecutionSdk.execution import ExecutionSdk
from ExecutionSdk.order import Order

PORT = os.environ.get('EDGIAPP_PORT', 4444)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # noinspection PyBroadException
            try:
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                order = Order(price=data['price'], order=data['order'])
                # would have verified values' types here, but the exercise did not specify any such constraints
            except Exception:
                self.send_error(400, "Request malformed")
                return
            server = cast(AppServer, self.server)
            processor = server.add_order(order)
            response = processor()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(dict(status=response.status)).encode('utf-8'))
        except Exception as reason:
            self.log_error(f'Exception: {reason}')
            self.send_error(500, 'Unexpected error')


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


class ExecutionBatch:
    def __init__(self, batch_size: int):
        self._batch_size = batch_size
        self._condition = Condition()
        self._orders: List[Order] = []
        self._responses: List[Order] = []
        self._is_complete = False
        self._exception_result: Optional[Exception] = None

    def add(self, order: Order) -> int:
        """
        :return: index of order in current batch
        NOTE: this method is single threaded
        """
        assert not self._is_complete, "Can't add an order for an already used batch"
        assert len(self._orders) < self._batch_size, "Unexpected state: too many orders for batch"
        next_index = len(self._orders)
        self._orders.append(order)
        return next_index

    def is_full(self) -> bool:
        return len(self._orders) >= self._batch_size

    def process_execution(self, for_index: int) -> Order:
        """
        :param for_index: The index for which an execution is required
        NOTE: this method is multi-threading safe
        NOTE: this method may have a long wait, internally
        NOTE: two calls to this method should never have the same for_index for the same object
        """
        with self._condition:
            if for_index == self._batch_size - 1:
                assert not self._is_complete, "Can't add an order for an already used batch"
                assert self.is_full(), "Unexpected state: for_index incorrect "
                try:
                    self._responses = ExecutionSdk.execute_orders(self._orders)
                except Exception as reason:
                    self._exception_result = reason
                    self._condition.notify_all()
                    raise
                self._is_complete = True
                self._condition.notify_all()
                return self._responses[for_index]

            self._condition.wait_for(lambda: self._is_complete or self._exception_result is not None)
            if self._exception_result:
                raise self._exception_result
            return self._responses[for_index]


class AppServer(ThreadingSimpleServer):
    BATCH_SIZE = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._curr_batch = ExecutionBatch(self.BATCH_SIZE)
        self._batch_lock = RLock()

    def add_order(self, order: Order) -> Callable:
        """
        :return: a callable object returning the execution result
        """
        with self._batch_lock:
            new_index = self._curr_batch.add(order)
            batch = self._curr_batch
            if self._curr_batch.is_full():
                self._curr_batch = ExecutionBatch(self.BATCH_SIZE)
            return partial(batch.process_execution, new_index)


def run():
    server = AppServer(('0.0.0.0', PORT), Handler)
    server.serve_forever()


if __name__ == '__main__':
    run()
