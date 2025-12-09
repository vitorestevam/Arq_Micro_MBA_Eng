# Demo 00 — CQRS + Event Sourcing (Checkout)

Este demo mostra um fluxo completo usando Kafka como Event Store:
- **Command-side**: `commands.py` valida o aggregate `Order` e publica eventos no tópico `cqrs.checkout-events`.
- **Event Store**: o próprio Kafka mantém a fita imutável (pode ser reprocessada a qualquer momento).
- **Query-side**: `projection.py` lê o tópico desde o início e gera/atualiza o read model (`read_model.db`), que é consultado via `query_read_model.py`.

## Pré-requisitos
```bash
conda activate arq-microsservicos-mba
cd aula_05/demo_00_cqrs_checkout
bash setup.sh  # garante o tópico cqrs.checkout-events (RF=3)
```

## Fluxo sugerido
1. **Resetar o estado (opcional)**
   ```bash
   bash reset_demo.sh
   ```
2. **Executar comandos (command-side → Kafka)**
   ```bash
   python commands.py create-order --order-id ORDER-9001 --customer-id CUSTOMER-77 --currency BRL
   python commands.py add-item --order-id ORDER-9001 --sku SKU-CHECKOUT --quantity 1 --unit-price 199.90
   python commands.py add-item --order-id ORDER-9001 --sku SKU-SHIPPING --quantity 1 --unit-price 29.90
   ```
   Cada comando gera eventos `OrderCreated` ou `OrderItemAdded` no tópico.
3. **Rebuild da projeção (read model a partir do Kafka)**
   ```bash
   python projection.py --bootstrap-server localhost:9092 --topic cqrs.checkout-events
   ```
   O script consome todo o tópico, reaplica a fita e popula `orders_read` (SQLite).
4. **Consultar o read model**
   ```bash
   python query_read_model.py --order-id ORDER-9001
   # ou listar tudo
   python query_read_model.py
   ```
   Note que esta consulta não toca o aggregate; ela lê apenas a projeção.

## Conceitos reforçados
- Command-side escreve apenas eventos em Kafka, nunca estados derivados.
- Read model pode ser destruído e recriado a qualquer momento rodando `projection.py` (replay completo).
- Os comandos são finitos e idempotentes (mesmo script pode ser reexecutado após limpar o event store).
