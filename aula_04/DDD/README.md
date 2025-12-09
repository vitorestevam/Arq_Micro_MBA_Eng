# Aula 04 — DDD aplicado ao Checkout com Kafka

Este diretório demonstra o **Exemplo 3** proposto: um aggregate `Order` modelado com Pydantic emitindo o domínio **`OrderItemAdded`** e publicando em Kafka.

## Conceitos Utilizados

- **Bounded Context (Checkout)**: responsável pelo ato de fechar o pedido.
- **Aggregate Root (`Order`)**: garante as invariantes e calcula o `total_amount`.
- **Value Objects (`Money`, `OrderItem`)**: encapsulam valores e regras (moeda única, quantidades, preços).
- **Domain Event (`OrderItemAdded`)**: imutável, usa linguagem ubíqua e é o payload enviado ao tópico `checkout.order-events`.

## Estrutura

```
aula_04/DDD/
├── order_domain.py          # Pydantic models (Value Objects, Aggregate, Domain Event)
└── order_event_producer.py  # Script que instancia o aggregate e produz eventos em Kafka
```

## Pré-requisitos

1. Ambiente Docker da `aula_01` rodando (`docker compose up -d`).
2. Ambiente Conda principal:
   ```bash
   conda env create -f ../../environment.yml  # primeira vez
   conda activate arq-microsservicos-mba
   ```

## Executando o Demo

```bash
cd aula_04/DDD
python order_event_producer.py \
  --bootstrap-server localhost:9092 \
  --topic checkout.order-events \
  --order-id ORDER-2024-0001 \
  --customer-id CUSTOMER-42
```

### O que observar

- O console mostra o aggregate adicionando itens e emitindo `OrderItemAdded`.
- No **Kafka UI** (`http://localhost:8080`), veja o tópico `checkout.order-events`:
  - Payload traz `event_name`, `bounded_context`, `order_id`, `item` (Value Object) e `total_amount`.
  - Todos os campos usam a linguagem ubíqua definida nos slides.

## Adaptações

- Modifique a lista em `demo_items` para simular outros subdomínios.
- Troque o `--topic` para publicar em um contexto diferente mantendo a mesma modelagem de domínio.
