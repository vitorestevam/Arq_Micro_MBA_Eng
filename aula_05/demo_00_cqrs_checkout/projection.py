from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from kafka_events import read_events

DB_PATH = Path(__file__).with_name("read_model.db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recria o read model a partir do tópico Kafka."
    )
    parser.add_argument(
        "--bootstrap-server",
        default="localhost:9092",
        help="Bootstrap server Kafka (default: localhost:9092)",
    )
    parser.add_argument(
        "--topic",
        default="cqrs.checkout-events",
        help="Tópico contendo os eventos do domínio.",
    )
    return parser.parse_args()


def setup_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders_read (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            currency TEXT NOT NULL,
            items_count INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("DELETE FROM orders_read")
    conn.commit()


def rebuild_projection(args: argparse.Namespace) -> None:
    events = read_events(
        bootstrap_server=args.bootstrap_server,
        topic=args.topic,
    )
    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)
    for event in events:
        if event["event_name"] == "OrderCreated":
            conn.execute(
                """
                INSERT OR REPLACE INTO orders_read
                (order_id, customer_id, currency, items_count, total_amount, updated_at)
                VALUES (?, ?, ?, 0, 0, ?)
                """,
                (
                    event["order_id"],
                    event["customer_id"],
                    event["currency"],
                    event["occurred_at"],
                ),
            )
        elif event["event_name"] == "OrderItemAdded":
            conn.execute(
                """
                UPDATE orders_read
                SET items_count = items_count + 1,
                    total_amount = ?,
                    updated_at = ?
                WHERE order_id = ?
                """,
                (
                    float(event["total_amount"]["amount"]),
                    event["occurred_at"],
                    event["order_id"],
                ),
            )
    conn.commit()
    conn.close()
    print(f"[Projection] Processados {len(events)} eventos.")


if __name__ == "__main__":
    rebuild_projection(parse_args())
