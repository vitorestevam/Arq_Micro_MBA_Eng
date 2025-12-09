# Demo 6: Kafka Connect JDBC Sink com UPSERT (Dual Sink)

Esta demo demonstra como usar o **Kafka Connect** para persistir automaticamente dados do Kafka em **dois bancos** (Postgres e MySQL) usando o modo **UPSERT** (insert ou update).

## Conceito

Simula um sistema de e-commerce que gera pedidos continuamente. Os pedidos são enviados para um tópico Kafka e o Kafka Connect os persiste automaticamente no Postgres.

```
[Python Producer (Faker)] 
    ↓ (JSON)
[Tópico: demo-orders]
    ↓ (Connect consome)
[JDBC Sink Connector - UPSERT (Postgres)]
    ↓
[Tabela Postgres: orders]

[JDBC Sink Connector - UPSERT (MySQL)]
    ↓
[Tabela MySQL: orders]
```

## Pré-requisitos

1. Ambiente Docker rodando (com Postgres, MySQL e Kafka Connect):
```bash
cd ../../aula_01
docker compose up -d
```

2. Aguarde ~60 segundos para o Kafka Connect instalar o plugin JDBC e inicializar completamente.

3. **IMPORTANTE:** Esta demo usa **Avro com Schema Registry**. Certifique-se que o Schema Registry está rodando na porta 8082.

## Passo a Passo

### 1. Configurar o Ambiente

Execute o script de setup que cria o tópico (RF=3) e registra **dois conectores**:

```bash
bash setup.sh
```

**O que ele faz:**
- Cria o tópico `demo-orders` com 3 partições e RF=3
- Aguarda o Kafka Connect estar pronto
- Registra os conectores `jdbc-sink-orders-demo` (Postgres) e `jdbc-sink-orders-demo-mysql`
- Mostra o status de ambos os conectores

### 2. Iniciar o Gerador de Pedidos

Em um terminal separado, execute:

```bash
python order_generator.py --events 20 --interval 0.5
```

**Parâmetros úteis:**
- `--events`: quantidade finita de pedidos (default: 20)
- `--interval`: intervalo entre pedidos em segundos (default: 0.5)
- `--start-order-id`: número inicial para os IDs (default: 1000)

**O que acontece:**
- Gera pedidos sintéticos usando Faker
- Cada pedido é **serializado com Avro** e registrado no Schema Registry
- Cada pedido tem: ID, nome do cliente, produto, valor, status e timestamps
- Os pedidos são enviados para o tópico `demo-orders` no formato Avro

### 3. Verificar os Dados (Postgres e MySQL)

Em outro terminal, execute:

```bash
bash verify.sh
```

**O que você verá:**
- Os 10 pedidos mais recentes no Postgres
- Os 10 pedidos mais recentes no MySQL
- Totais e distribuição por status nos dois bancos

## Testando o UPSERT

O modo UPSERT significa que se você enviar um pedido com um `order_id` que já existe, ele será **atualizado** em vez de duplicado.

**Teste:**
1. Deixe o producer rodando por ~30 segundos
2. Pare o producer (Ctrl+C)
3. Modifique o `order_generator.py` para gerar IDs fixos (ex: sempre `ORD-1000`)
4. Execute novamente
5. Rode `bash verify.sh` e veja que o contador não aumenta, mas o registro é atualizado

## Configuração dos Conectores

- `connector-config.json`: Postgres (`jdbc-sink-orders-demo`)
- `connector-config-mysql.json`: MySQL (`jdbc-sink-orders-demo-mysql`)

Ambos usam os mesmos princípios:

- **insert.mode: "upsert"**
- **pk.mode: "record_value"**
- **pk.fields: "order_id"**
- **auto.create/auto.evolve: true**
- **value.converter: AvroConverter** apontando para o Schema Registry

## Limpeza

Para parar tudo:

```bash
# Parar o producer (Ctrl+C no terminal dele)

# Remover os conectores
curl -X DELETE http://localhost:8083/connectors/jdbc-sink-orders-demo
curl -X DELETE http://localhost:8083/connectors/jdbc-sink-orders-demo-mysql

# Parar os containers
cd ../../aula_01
docker compose down
```

## Troubleshooting

**Erro: "Connection refused" ao registrar conector**
- Aguarde mais tempo. O Kafka Connect demora ~30s para instalar o plugin JDBC.
- Verifique: `curl http://localhost:8083/`

**Tabela não está sendo criada**
- Verifique o status do conector: `curl http://localhost:8083/connectors/jdbc-sink-orders-demo/status`
- Veja os logs: `docker logs kafka-connect`

**Producer não conecta**
- Certifique-se que o Kafka está rodando: `docker ps | grep kafka`
