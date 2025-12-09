from __future__ import annotations

import json
from typing import Iterable
from uuid import uuid4

from confluent_kafka import (
    Consumer,
    KafkaException,
    KafkaError,
    TopicPartition,
    OFFSET_BEGINNING,
)


def read_events(
    *,
    bootstrap_server: str,
    topic: str,
    order_id: str | None = None,
) -> list[dict]:
    """Lê todos os eventos do tópico (ou filtra por order_id)."""
    group_id = f"cqrs-replay-{uuid4()}"
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_server,
            "group.id": group_id,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )

    try:
        metadata = consumer.list_topics(topic, timeout=5)
        topic_meta = metadata.topics.get(topic)
        if topic_meta is None:
            raise RuntimeError(f"Tópico {topic} não encontrado.")
        partitions = [
            TopicPartition(topic, partition_id, OFFSET_BEGINNING)
            for partition_id in topic_meta.partitions.keys()
        ]
        consumer.assign(partitions)

        events: list[dict] = []
        idle_iterations = 0
        while idle_iterations < 10:
            msg = consumer.poll(0.5)
            if msg is None:
                idle_iterations += 1
                continue
            idle_iterations = 0
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())
            payload = json.loads(msg.value())
            if order_id is None or payload.get("order_id") == order_id:
                events.append(payload)
        return events
    finally:
        consumer.close()


def stream_events(
    *,
    bootstrap_server: str,
    topic: str,
    poll_timeout: float = 1.0,
) -> Iterable[dict]:
    """Stream contínuo (read_committed) para atualização incremental."""
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_server,
            "group.id": f"cqrs-projection-{uuid4()}",
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([topic])
    try:
        while True:
            msg = consumer.poll(poll_timeout)
            if msg is None:
                return
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())
            yield json.loads(msg.value())
    finally:
        consumer.close()
