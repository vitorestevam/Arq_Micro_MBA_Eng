"""Demo de DDD usando Pydantic + Kafka.

Executa o cenário "OrderItemAdded" e produz eventos no tópico configurado.
"""

from __future__ import annotations

import argparse
import json
from typing import Iterable

from confluent_kafka import Producer

from order_domain import Money, Order


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Produz eventos OrderItemAdded usando o aggregate Order."
    )
    parser.add_argument(
        "--bootstrap-server",
        default="localhost:9092",
        help="Bootstrap server para o Kafka (default: localhost:9092)",
    )
    parser.add_argument(
        "--topic",
        default="checkout.order-events",
        help="Tópico onde os eventos serão publicados.",
    )
    parser.add_argument(
        "--order-id",
        default="ORDER-2024-0001",
        help="Identificador do aggregate Order.",
    )
    parser.add_argument(
        "--customer-id",
        default="CUSTOMER-42",
        help="Identificador da entidade Customer.",
    )
    parser.add_argument(
        "--currency",
        default="BRL",
        help="Moeda utilizada no bounded context Checkout.",
    )
    return parser.parse_args()


def demo_items(currency: str) -> Iterable[dict]:
    """Itens de exemplo com Value Objects Money."""
    return [
        {"sku": "SKU-CHECKOUT-FOUNDATIONS", "quantity": 1, "unit_price": Money(currency=currency, amount="199.90")},
        {"sku": "SKU-SERVICE-SHIPPING", "quantity": 1, "unit_price": Money(currency=currency, amount="39.90")},
        {"sku": "SKU-SERVICE-INSURANCE", "quantity": 1, "unit_price": Money(currency=currency, amount="14.99")},
    ]


def publish_events(args: argparse.Namespace) -> None:
    order = Order(
        order_id=args.order_id,
        customer_id=args.customer_id,
        currency=args.currency,
        total_amount=Money(currency=args.currency, amount=0),
    )

    producer = Producer({"bootstrap.servers": args.bootstrap_server})

    def delivery_report(err, msg) -> None:
        if err:
            print(f"[Kafka] Falha ao enviar evento: {err}")
            return
        print(
            f"[Kafka] Evento gravado | topic={msg.topic()} partition={msg.partition()} offset={msg.offset()}"
        )

    for item in demo_items(args.currency):
        event = order.add_item(**item)
        payload = event.model_dump(mode="json")
        print(
            f"[Aggregate:Order] item={item['sku']} total={payload['total_amount']['amount']} event_id={payload['event_id']}"
        )
        producer.produce(
            topic=args.topic,
            key=order.order_id,
            value=json.dumps(payload).encode("utf-8"),
            on_delivery=delivery_report,
        )
        producer.poll(0)

    producer.flush()


if __name__ == "__main__":
    publish_events(parse_args())
