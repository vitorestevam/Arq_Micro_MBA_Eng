from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Money(BaseModel):
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
            raise ValueError("Currencies must match.")
        return Money(currency=self.currency, amount=self.amount + other.amount)


class OrderItem(BaseModel):
    sku: str
    quantity: int = Field(ge=1)
    unit_price: Money

    def subtotal(self) -> Money:
        return Money(
            currency=self.unit_price.currency,
            amount=self.unit_price.amount * Decimal(self.quantity),
        )


class OrderAggregate(BaseModel):
    order_id: str
    customer_id: str
    currency: str
    items: list[OrderItem] = Field(default_factory=list)
    total_amount: Money
    created_at: datetime

    def add_item(self, item: OrderItem) -> None:
        if item.unit_price.currency != self.currency:
            raise ValueError("Item currency must match order currency.")
        self.items.append(item)
        self.total_amount = self.total_amount + item.subtotal()


class OrderCreated(BaseModel):
    event_name: Literal["OrderCreated"] = "OrderCreated"
    bounded_context: Literal["Checkout"] = "Checkout"
    order_id: str
    customer_id: str
    currency: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrderItemAdded(BaseModel):
    event_name: Literal["OrderItemAdded"] = "OrderItemAdded"
    bounded_context: Literal["Checkout"] = "Checkout"
    order_id: str
    item: OrderItem
    total_amount: Money
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
