from __future__ import annotations

import argparse
import json
import sys

from confluent_kafka import Producer

from domain import Money, OrderAggregate, OrderCreated, OrderItem, OrderItemAdded
from kafka_events import read_events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Command-side CQRS demo (Checkout)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create_cmd = sub.add_parser("create-order", help="Cria um aggregate Order.")
    create_cmd.add_argument("--order-id", required=True)
    create_cmd.add_argument("--customer-id", required=True)
    create_cmd.add_argument("--currency", default="BRL")

    add_item_cmd = sub.add_parser("add-item", help="Adiciona item a um Order.")
    add_item_cmd.add_argument("--order-id", required=True)
    add_item_cmd.add_argument("--sku", required=True)
    add_item_cmd.add_argument("--quantity", type=int, default=1)
    add_item_cmd.add_argument("--unit-price", type=str, required=True)
    add_item_cmd.add_argument("--currency", default="BRL")

    parser.add_argument(
        "--bootstrap-server",
        default="localhost:9092",
        help="Bootstrap server Kafka (default: localhost:9092)",
    )
    parser.add_argument(
        "--topic",
        default="cqrs.checkout-events",
        help="Tópico usado como event store.",
    )
    return parser.parse_args()


def load_aggregate(args: argparse.Namespace) -> OrderAggregate | None:
    events = read_events(
        bootstrap_server=args.bootstrap_server,
        topic=args.topic,
        order_id=args.order_id,
    )
    aggregate: OrderAggregate | None = None
    for event in events:
        if event["event_name"] == "OrderCreated":
            aggregate = OrderAggregate(
                order_id=event["order_id"],
                customer_id=event["customer_id"],
                currency=event["currency"],
                items=[],
                total_amount=Money(currency=event["currency"], amount=0),
                created_at=event["occurred_at"],
            )
        elif event["event_name"] == "OrderItemAdded" and aggregate:
            item = OrderItem.model_validate(event["item"])
            aggregate.add_item(item)
    return aggregate


def cmd_create_order(args: argparse.Namespace, producer: Producer) -> None:
    if load_aggregate(args):
        print(f"[Command] Order {args.order_id} já existe.", file=sys.stderr)
        sys.exit(1)
    event = OrderCreated(
        order_id=args.order_id,
        customer_id=args.customer_id,
        currency=args.currency,
    )
    payload = event.model_dump(mode="json")
    producer.produce(
        topic=args.topic,
        key=args.order_id,
        value=(json.dumps(payload)).encode("utf-8"),
    )
    producer.flush()
    print(f"[Command] OrderCreated -> order={args.order_id}")


def cmd_add_item(args: argparse.Namespace, producer: Producer) -> None:
    aggregate = load_aggregate(args)
    if not aggregate:
        print(f"[Command] Order {args.order_id} não encontrado.", file=sys.stderr)
        sys.exit(1)
    item = OrderItem(
        sku=args.sku,
        quantity=args.quantity,
        unit_price=Money(currency=args.currency, amount=args.unit_price),
    )
    aggregate.add_item(item)
    event = OrderItemAdded(
        order_id=args.order_id,
        item=item,
        total_amount=aggregate.total_amount,
    )
    payload = event.model_dump(mode="json")
    producer.produce(
        topic=args.topic,
        key=args.order_id,
        value=json.dumps(payload).encode("utf-8"),
    )
    producer.flush()
    print(
        f"[Command] OrderItemAdded -> order={args.order_id} "
        f"sku={item.sku} total={aggregate.total_amount.amount}"
    )


def main() -> None:
    args = parse_args()
    producer = Producer({"bootstrap.servers": args.bootstrap_server})
    if args.command == "create-order":
        cmd_create_order(args, producer)
    elif args.command == "add-item":
        cmd_add_item(args, producer)


if __name__ == "__main__":
    main()
