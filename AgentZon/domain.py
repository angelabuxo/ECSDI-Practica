from dataclasses import dataclass


@dataclass(frozen=True)
class SearchCriteria:
    text: str = ""
    category: str = ""
    brand: str = ""
    min_price: float | None = None
    max_price: float | None = None


@dataclass(frozen=True)
class ProductRecord:
    product_id: str
    name: str
    description: str
    category: str
    brand: str
    price: float
    weight: float


@dataclass(frozen=True)
class UserShippingData:
    user_id: str
    user_name: str
    street_address: str
    city: str
    priority: str
    payment_method: str


@dataclass(frozen=True)
class OrderRecord:
    order_id: str
    user_id: str
    user_name: str
    products: list[ProductRecord]
    shipping_data: UserShippingData


@dataclass(frozen=True)
class TransportOffer:
    lot_id: str
    transport_id: str
    transport_name: str
    city: str
    delivery_date: str
    price: float

