from kafka import KafkaConsumer
import psycopg2
import json
import time
import logging

# Kafka / topic
KAFKA_TOPIC = 'dbserver1.public.meme_coins'
KAFKA_BOOTSTRAP = ['kafka:29092']
KAFKA_GROUP_ID = 'python-consumer-group'
KAFKA_AUTO_OFFSET_RESET = 'earliest'

# Destination Postgres
PG_DEST_HOST = 'postgres_dest'
PG_DEST_PORT = 5432
PG_DEST_DB = 'analytics'
PG_DEST_USER = 'postgres'
PG_DEST_PASSWORD = 'postgres'

# DB connection retry policy
DB_CONNECT_RETRIES = 5
DB_CONNECT_DELAY = 2

LOG_LEVEL = logging.INFO


# Kafka consumer configuration
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP,
    group_id=KAFKA_GROUP_ID,
    auto_offset_reset=KAFKA_AUTO_OFFSET_RESET,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
    key_deserializer=lambda m: m.decode('utf-8') if m else None,
)

def connect_db(retries=DB_CONNECT_RETRIES, delay=DB_CONNECT_DELAY):
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=PG_DEST_HOST,
                port=PG_DEST_PORT,
                dbname=PG_DEST_DB,
                user=PG_DEST_USER,
                password=PG_DEST_PASSWORD,
            )
            conn.autocommit = False
            return conn
        except Exception as e:
            print(f"Postgres connection attempt {attempt} failed: {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to Postgres after retries")


conn = connect_db()
cursor = conn.cursor()

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s %(levelname)s %(name)s - %(message)s',
)
logger = logging.getLogger('postgres_consumer')
logger.info('Connected to Postgres and ensured destination table exists')


# Ensure destination table exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS meme_coins (
    id TEXT PRIMARY KEY,
    name TEXT,
    symbol TEXT,
    price TEXT,
    volume TEXT,
    cap TEXT,
    date TEXT,
    is_valid INTEGER
)
""")
conn.commit()


def apply_change(payload):
    """Apply a Debezium payload change to the destination Postgres.

    Expected Debezium payload structure (value/payload):
      { 'op': 'c'|'u'|'d'|'r', 'after': {...}, 'before': {...}, ... }
    """
    if payload is None:
        return

    op = payload.get('op')
    after = payload.get('after')
    before = payload.get('before')

    try:
        if op in ('c', 'r', 'u'):
            # Use 'after' for inserts/updates (snapshot 'r' also uses 'after')
            if not after:
                print("No 'after' data for create/update, skipping")
                return

            # Map fields explicitly to avoid unexpected keys
            record = {
                'id': after.get('id'),
                'name': after.get('name'),
                'symbol': after.get('symbol'),
                'price': after.get('price'),
                'volume': after.get('volume'),
                'cap': after.get('cap'),
                'date': after.get('date'),
                'is_valid': after.get('is_valid'),
            }

            # Upsert: insert or update on conflict
            cursor.execute(
                """
                INSERT INTO meme_coins (id, name, symbol, price, volume, cap, date, is_valid)
                VALUES (%(id)s, %(name)s, %(symbol)s, %(price)s, %(volume)s, %(cap)s, %(date)s, %(is_valid)s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    symbol = EXCLUDED.symbol,
                    price = EXCLUDED.price,
                    volume = EXCLUDED.volume,
                    cap = EXCLUDED.cap,
                    date = EXCLUDED.date,
                    is_valid = EXCLUDED.is_valid
                """,
                record,
            )
            conn.commit()
            logger.info("Upserted id=%s", record['id'])

        elif op == 'd':
            # Delete: use 'before' to find primary key
            if not before:
                print("No 'before' data for delete, skipping")
                return
            key_id = before.get('id')
            cursor.execute("DELETE FROM meme_coins WHERE id = %s", (key_id,))
            conn.commit()
            logger.info("Deleted id=%s", key_id)
        else:
            logger.warning("Unhandled operation '%s'", op)

    except Exception as e:
        # On error, rollback the transaction and print error
        try:
            conn.rollback()
        except Exception:
            pass
        logger.exception("Failed to apply change: %s", e)


try:
    logger.info('Kafka consumer started, listening for messages on topic %s', KAFKA_TOPIC)
    for message in consumer:
        key = message.key
        value = message.value

        logger.debug('Raw message key=%s value=%s', key, json.dumps(value) if value is not None else None)

        # Debezium usually sends an object with a 'payload' field
        payload = None
        if isinstance(value, dict) and 'payload' in value:
            payload = value.get('payload')
        else:
            # Some setups directly send the payload as the value
            payload = value

        if payload is None:
            logger.info('Empty payload received, skipping')
            continue

        op = payload.get('op')
        logger.info("Received operation=%s for key=%s", op, key)

        # Optionally log compact after/before for debugging large messages
        if 'after' in payload and payload.get('after'):
            logger.debug('After: %s', json.dumps(payload.get('after')))
        if 'before' in payload and payload.get('before'):
            logger.debug('Before: %s', json.dumps(payload.get('before')))

        apply_change(payload)

except KeyboardInterrupt:
    logger.info('Consumer interrupted. Exiting...')

except Exception as e:
    logger.exception('Unexpected consumer error: %s', e)

finally:
    try:
        cursor.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass
    consumer.close()