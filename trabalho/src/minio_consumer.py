import io
import json
import os
import time
import uuid
from datetime import datetime
import logging
import boto3
import pandas as pd
from kafka import KafkaConsumer

# Configuration (fixed for compose setup)
KAFKA_TOPIC = 'dbserver1.public.meme_coins'
BOOTSTRAP = 'kafka:29092'
S3_ENDPOINT = 'http://minio:9000'
S3_ACCESS_KEY = 'minioadmin'
S3_SECRET_KEY = 'minioadmin'
BUCKET = 'meme-parquet'
AWS_REGION = 'us-east-1'

# Kafka consumer configuration
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=[BOOTSTRAP],
    group_id='minio-consumer-group',
    auto_offset_reset='earliest',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
    key_deserializer=lambda m: m.decode('utf-8') if m else None,
)

def connect_s3(retries=5, delay=2):
    for attempt in range(1, retries + 1):
        try:
            client = boto3.client(
                's3',
                endpoint_url=S3_ENDPOINT,
                aws_access_key_id=S3_ACCESS_KEY,
                aws_secret_access_key=S3_SECRET_KEY,
                region_name=AWS_REGION,
            )
            return client
        except Exception as e:
            print(f"S3 connection attempt {attempt} failed: {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to S3 after retries")


s3 = connect_s3()

# Configure logging to match style of postgres_consumer
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s - %(message)s',
)
logger = logging.getLogger('minio_consumer')


def ensure_bucket():
    try:
        s3.head_bucket(Bucket=BUCKET)
        logger.info('Bucket %s exists', BUCKET)
    except Exception:
        try:
            s3.create_bucket(Bucket=BUCKET)
            logger.info('Created bucket %s', BUCKET)
        except Exception as e:
            logger.exception('Unable to create or access bucket %s: %s', BUCKET, e)
            raise

ensure_bucket()

def record_to_parquet_bytes(data: dict) -> bytes:
    """Convert a single dict record to parquet bytes using pandas + pyarrow."""
    # Accept Debezium envelope or plain record
    payload = data.get('payload') if isinstance(data, dict) and 'payload' in data else data
    if isinstance(payload, dict) and ('after' in payload or 'before' in payload):
        if payload.get('after'):
            row = payload.get('after')
        else:
            row = payload.get('before')
    else:
        row = payload

    if row is None:
        row = {}

    df = pd.DataFrame([row])
    buf = io.BytesIO()
    df.to_parquet(buf, engine='pyarrow', index=False)
    buf.seek(0)
    return buf.read()


def upload_parquet(data_bytes: bytes, obj_key: str):
    s3.put_object(Bucket=BUCKET, Key=obj_key, Body=data_bytes)
    logger.info('Uploaded object %s to bucket %s', obj_key, BUCKET)


def delete_objects_by_id(key_id: str):
    # List objects that include the id in their key and delete them
    prefix = f"id={key_id}_"
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    if not resp or 'Contents' not in resp:
        logger.info('No objects to delete for id=%s', key_id)
        return
    objects = [{'Key': o['Key']} for o in resp['Contents']]
    s3.delete_objects(Bucket=BUCKET, Delete={'Objects': objects})
    logger.info('Deleted %d objects for id=%s', len(objects), key_id)


def apply_change(payload):
    """Handle Debezium payload: upsert (create/update) -> write parquet; delete -> remove objects."""
    if payload is None:
        return

    op = payload.get('op')
    after = payload.get('after')
    before = payload.get('before')

    try:
        if op in ('c', 'r', 'u'):
            record = after or {}
            key_id = record.get('id') or str(uuid.uuid4())
            # create object key including id for easy deletion
            obj_key = f"id={key_id}_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex}.parquet"
            data_bytes = record_to_parquet_bytes(payload)
            upload_parquet(data_bytes, obj_key)
            logger.info('Uploaded parquet for id=%s key=%s', key_id, obj_key)

        elif op == 'd':
            key_id = (before or {}).get('id')
            if not key_id:
                logger.warning("No 'before' id available for delete, skipping")
                return
            delete_objects_by_id(key_id)

        else:
            logger.warning("Unhandled operation '%s'", op)

    except Exception as e:
        logger.exception('Failed to apply change: %s', e)


try:
    logger.info('Kafka consumer started, listening for messages on topic %s', KAFKA_TOPIC)
    for message in consumer:
        key = message.key
        value = message.value
        logger.debug('Raw message key=%s value=%s', key, json.dumps(value) if value is not None else None)

        payload = None
        if isinstance(value, dict) and 'payload' in value:
            payload = value.get('payload')
        else:
            payload = value

        if payload is None:
            logger.info('Empty payload received, skipping')
            continue

        op = payload.get('op')
        logger.info('Received operation=%s for key=%s', op, key)

        apply_change(payload)

except KeyboardInterrupt:
    logger.info('MinIO consumer interrupted. Exiting...')

except Exception as e:
    logger.exception('Unexpected consumer error: %s', e)

finally:
    consumer.close()
