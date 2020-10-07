import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Condition
from time import sleep
from typing import cast, List

from ExecutionSdk.order import Order

PORT = 4444  # TODO


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        print(f'do_POST {time.ctime()}')
        data = self.rfile.read(int(self.headers["Content-Length"]))
        print(f'data: {json.loads(data)}')
        sleep(3)  # TODO
        self.send_response(200)
        self.end_headers()
        server = cast(AppServer, self.server)
        print(server.x)
        print(f'do_POST Done {time.ctime()}')


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


class ExecutionBatch:
    BATCH_SIZE = 10

    def __init__(self):
        self._cond = Condition()
        self._curr_batch: List[Order] = []
        self._responses: List[Order] = []
        self._is_pending = True

    def add(self, order: Order) -> bool:
        """
        :return: index of order in current batch
        NOTE: this method is single threaded
        """
        assert(self._is_pending, "Can't add an order for an already used batch")
        next_index = len(self._curr_batch)
        self._curr_batch.append(order)
        return next_index

    def is_full(self):
        return len(self._curr_batch) >= self.BATCH_SIZE

    def process_execution(self, for_index: int):
        """
        :param for_index: The index for which an execution is required
        NOTE: this method is multi-threading safe
        NOTE: this method may have a long wait, internally
        NOTE: two calls to this method should never have the same for_index for the same object
        """
        with self._cond:
            if for_index == self.BATCH_SIZE:
                assert(self._is_pending, "Can't add an order for an already used batch")
                assert(self._is_full(), "Unexpected state: for_index incorrect ")
                # TODO make the request
                self._cond.notify_all()
            else:
                self._cond.wait_for(lambda: not self._is_pending)
        return self._responses[for_index]


class AppServer(ThreadingSimpleServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._curr_batch =


def run():
    print('run')
    server = AppServer(('0.0.0.0', PORT), Handler)
    server.serve_forever()


if __name__ == '__main__':
    run()
