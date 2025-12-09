# Pipeline CDC

O trabalho se baseia em um banco postgres de origem, uma instancia do Debezium observando as mudanças e enviando para o kafka e duas instancias "destino" recebendo notificações do kafka e replicando as operações feitas.

```mermaid
flowchart LR
    %% Sources (Database shape)
    PostgresSrc([Postgres Source])
    
    %% Debezium (Parallelogram for process)
    Debezium[/Debezium CDC Watcher/]
    
    %% Kafka (Stadium for broker)
    Kafka([Kafka Broker])
    
    %% Destinations
    PostgresDest([Postgres Destination])
    MinioDest([MinIO Bucket])

    %% Data Flow
    PostgresSrc --> Debezium --> Kafka
    Kafka --> PostgresDest
    Kafka --> MinioDest

    class PostgresSrc source;
    class Debezium broker;
    class Kafka broker;
    class PostgresDest sink;
    class MinioDest sink;
```

## Como rodar

O deploy está automatizado e um  ````docker compose up``` vai subir todas as instancias de banco, registrar o connector e subir os consumers.

## Como testar

O arquivo test.ipynb é um notebook python que conta com testes de inserção, atualização e remoção de linhas do banco de origem e observa por essas mudanças nos bancos destino.

