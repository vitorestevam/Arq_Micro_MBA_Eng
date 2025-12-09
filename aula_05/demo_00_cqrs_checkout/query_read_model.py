from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("read_model.db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consulta o read model (orders_read)."
    )
    parser.add_argument("--order-id", help="Order específico (opcional).")
    return parser.parse_args()


def query(order_id: str | None) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if order_id:
        rows = conn.execute(
            "SELECT * FROM orders_read WHERE order_id = ?", (order_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM orders_read ORDER BY updated_at DESC"
        ).fetchall()
    conn.close()
    if not rows:
        print("Nenhum registro encontrado.")
        return
    for row in rows:
        print(
            f"order_id={row['order_id']} customer={row['customer_id']} "
            f"items={row['items_count']} total={row['total_amount']} updated_at={row['updated_at']}"
        )


if __name__ == "__main__":
    args = parse_args()
    query(args.order_id)
