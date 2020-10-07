from dataclasses import dataclass


@dataclass
class Order:
    price: float
    order: float
    status: str = None
