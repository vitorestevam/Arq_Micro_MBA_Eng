from __future__ import annotations

import argparse
import random
import time
from datetime import datetime

from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import MessageField, SerializationContext
from faker import Faker

# Configuração Schema Registry
schema_registry_conf = {'url': 'http://localhost:8082'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

# Carregar schema Avro
with open("schemas/order.avsc", "r") as f:
    schema_str = f.read()

avro_serializer = AvroSerializer(schema_registry_client, schema_str)

# Configuração Producer
producer_conf = {'bootstrap.servers': 'localhost:9092'}
producer = Producer(producer_conf)
topic = 'demo-orders'

# Configuração Faker
fake = Faker('pt_BR')
statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
products = [
    'Notebook Dell Inspiron', 'Mouse Logitech MX', 'Teclado Mecânico',
    'Monitor LG 27"', 'Webcam Full HD', 'Headset Gamer',
    'SSD Samsung 1TB', 'Memória RAM 16GB', 'Placa de Vídeo RTX'
]

def delivery_callback(err, msg):
    if err:
        print(f'❌ Erro: {err}')
    else:
        print(f'✅ Pedido enviado: {msg.value()[:50] if isinstance(msg.value(), bytes) else str(msg.value())[:50]}...')

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera pedidos Avro finitos para o tópico demo-orders.")
    parser.add_argument(
        "--events",
        type=int,
        default=20,
        help="Quantidade de pedidos a serem enviados (default: 20).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Intervalo em segundos entre eventos (default: 0.5s).",
    )
    parser.add_argument(
        "--start-order-id",
        type=int,
        default=1000,
        help="Valor inicial do contador de IDs (default: 1000).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"🚀 Iniciando gerador de pedidos Avro → tópico '{topic}'")
    print(f"   Total planejado: {args.events} eventos | Intervalo: {args.interval}s\n")

    order_counter = args.start_order_id

    for _ in range(args.events):
        order_id = f"ORD-{order_counter}"
        order = {
            "order_id": order_id,
            "customer_name": fake.name(),
            "product": random.choice(products),
            "amount": round(random.uniform(50.0, 5000.0), 2),
            "status": random.choice(statuses),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        try:
            print(f"→ Serializando {order_id}", flush=True)
            serialized_value = avro_serializer(
                order,
                SerializationContext(topic, MessageField.VALUE)
            )
            print(f"→ Publicando {order_id}", flush=True)
            producer.produce(
                topic,
                value=serialized_value,
                callback=delivery_callback
            )
            producer.poll(0)
        except Exception as exc:
            print(f"❌ Erro ao serializar/enviar: {exc}")
        finally:
            order_counter += 1
            time.sleep(args.interval)

    producer.flush()
    print("\n✅ Todos os pedidos foram enviados!")


if __name__ == "__main__":
    main()
