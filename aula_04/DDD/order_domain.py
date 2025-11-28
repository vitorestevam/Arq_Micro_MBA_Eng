from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class Money(BaseModel):
    """Value Object que representa valores monetários com validação de moeda."""

    currency: str = Field(min_length=3, max_length=3)
    amount: Decimal = Field(ge=0)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("amount", mode="before")
    @classmethod
    def decimalize(cls, value: Decimal | float | int | str) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Currencies must match to add values.")
        return Money(currency=self.currency, amount=self.amount + other.amount)

    def multiply(self, factor: int) -> "Money":
        return Money(currency=self.currency, amount=self.amount * Decimal(factor))


class OrderItem(BaseModel):
    """Value Object representando um item de pedido."""

    sku: str
    quantity: int = Field(ge=1)
    unit_price: Money

    def subtotal(self) -> Money:
        return self.unit_price.multiply(self.quantity)


class Order(BaseModel):
    """Aggregate Root Order. Controla invariantes e emite eventos de domínio."""

    order_id: str
    customer_id: str
    currency: str = Field(min_length=3, max_length=3)
    items: list[OrderItem] = Field(default_factory=list)
    total_amount: Money

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    def add_item(self, *, sku: str, quantity: int, unit_price: Money) -> "OrderItemAdded":
        if unit_price.currency != self.currency:
            raise ValueError("Item currency must match order currency.")
        item = OrderItem(sku=sku, quantity=quantity, unit_price=unit_price)
        self.items.append(item)
        self.total_amount = self.total_amount + item.subtotal()
        return OrderItemAdded(
            order_id=self.order_id,
            customer_id=self.customer_id,
            item=item,
            total_amount=self.total_amount,
        )


class OrderItemAdded(BaseModel):
    """Domain Event emitido pelo aggregate Order."""

    event_name: Literal["OrderItemAdded"] = "OrderItemAdded"
    bounded_context: Literal["Checkout"] = "Checkout"
    order_id: str
    customer_id: str
    item: OrderItem
    total_amount: Money
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = Field(default_factory=lambda: str(uuid4()))
