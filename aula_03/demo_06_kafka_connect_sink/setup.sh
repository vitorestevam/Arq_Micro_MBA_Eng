#!/bin/bash

echo "🔧 Setup Demo 06 - Kafka Connect JDBC Sink"
echo ""

# 1. Criar tópico
echo "1️⃣  Criando tópico 'demo-orders'..."
docker exec kafka kafka-topics --create \
    --topic demo-orders \
    --bootstrap-server kafka:29092 \
    --partitions 3 \
    --replication-factor 3 2>/dev/null || echo "   ⚠️  Tópico já existe"

echo ""

# 2. Aguardar Kafka Connect estar pronto
echo "2️⃣  Aguardando Kafka Connect inicializar..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8083/ > /dev/null 2>&1; then
        echo "   ✅ Kafka Connect está pronto!"
        break
    fi
    attempt=$((attempt + 1))
    echo "   ⏳ Tentativa $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "   ❌ Timeout aguardando Kafka Connect"
    exit 1
fi

echo ""

# 3. Garantir tabela no MySQL (para evitar erro de key length)
echo "3️⃣  Garantindo tabela 'orders' no MySQL..."
docker exec mysql mysql -u root -pmysqlroot demo_db <<'SQL'
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(64) PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    product VARCHAR(255) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    status VARCHAR(64) NOT NULL,
    created_at VARCHAR(64) NOT NULL,
    updated_at VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
SQL

echo ""

# 4. Registrar conectores
register_connector () {
    local config_file=$1
    echo "4️⃣  Registrando $(basename "$config_file")..."
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8083/connectors \
        -H "Content-Type: application/json" \
        -d @"$config_file")
    if [ "$status" = "201" ] || [ "$status" = "409" ]; then
        echo "   ✅ Resposta ${status}"
    else
        echo "   ❌ Falha ao registrar (HTTP ${status})"
        exit 1
    fi
}

register_connector connector-config.json
echo ""
register_connector connector-config-mysql.json

echo ""

# 5. Verificar status
echo "5️⃣  Status dos conectores:"
sleep 2
curl -s http://localhost:8083/connectors/jdbc-sink-orders-demo/status | python3 -m json.tool
echo ""
curl -s http://localhost:8083/connectors/jdbc-sink-orders-demo-mysql/status | python3 -m json.tool

echo ""
echo "✅ Setup concluído!"
echo ""
echo "📝 Próximos passos:"
echo "   - Execute: python order_generator.py --events 20 --interval 0.5"
echo "   - Verifique os dados: bash verify.sh"
