# Aula 05 — Demos avançadas com Kafka

Esta aula reúne cinco demos independentes com foco nos tópicos discutidos em sala: ordenação/transações, integrações multi-sink, data contracts, throughput e ingestão Pub/Sub/Webhook.

## Demos

0. **demo_00_cqrs_checkout** — Command-side com Event Sourcing no Kafka e read model separado via SQLite.
1. **demo_01_ordering** — Produção transacional com garantia de ordem por chave e consumidor confirmando offsets. Todos os produtores são finitos.
2. **(aula_03/demo_06)** — Dual Sink Postgres + MySQL vive na pasta da aula 03, conforme alinhado.
3. **demo_03_data_contracts** — Validação declarativa de payloads Kafka usando Pydantic (contratos versionados).
4. **demo_04_throughput** — Runner que mede throughput variando número de partições e fator de replicação.
5. **demo_05_pubsub_webhook** — Ponte que recebe eventos por Pub/Sub interno e Webhook HTTP e os publica no Kafka.

Cada subdiretório possui README e scripts próprios. Execute sempre no ambiente Conda `arq-microsservicos-mba` e certifique-se de que os produtores sejam finitos para evitar loops, especialmente durante os testes em sala.
