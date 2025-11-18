# Guia de Otimização de Performance

## 📊 Melhorias Implementadas

### 1. Otimizações no Código Spark

#### ✅ Reparticionamento Inteligente
```python
# ANTES: Cache sem reparticionamento
df1_blocked = self.create_blocking_key(df1).cache()

# DEPOIS: Reparticionamento por blocking_key
df1_blocked = self.create_blocking_key(df1) \
    .repartition(200, "blocking_key") \
    .cache()
```
**Ganho**: Melhor distribuição de dados e paralelismo nos joins.

#### ✅ Materialização Forçada
```python
# Força materialização do cache antes do join
df1_blocked.count()
df2_blocked.count()
```
**Ganho**: Evita recomputação durante o join.

#### ✅ Consolidação de Partições na Saída
```python
# Reduz partições para escrita eficiente
result = matches.select(...).repartition(10)
```
**Ganho**: Menos arquivos pequenos, I/O mais eficiente.

#### ✅ Remoção de Count() Desnecessários
```python
# EVITAR em produção - operação cara
# logger.info(f"Dataset 1 count: {df1.count()}")

# PREFERIR - apenas para debug
# Use explain() ou logs do Spark UI
```
**Ganho**: Elimina varreduras completas dos dados.

### 2. Configurações Spark Otimizadas

#### Adaptive Query Execution (AQE)
```bash
--conf spark.sql.adaptive.enabled=true
--conf spark.sql.adaptive.coalescePartitions.enabled=true
--conf spark.sql.adaptive.skewJoin.enabled=true
--conf spark.sql.adaptive.autoBroadcastJoinThreshold=10MB
```
**Benefícios**:
- Ajuste dinâmico de partições
- Detecção automática de skew
- Broadcast automático de tabelas pequenas

#### Configurações de Memória
```bash
--driver-memory 2g
--executor-memory 3g
--conf spark.memory.fraction=0.8          # 80% para execução e storage
--conf spark.memory.storageFraction=0.3   # 30% da fração para cache
```
**Benefícios**:
- Mais memória para computação
- Melhor aproveitamento do cache

#### Paralelismo
```bash
--conf spark.sql.shuffle.partitions=200
--conf spark.default.parallelism=200
```
**Regra**: 2-4x o número de cores disponíveis (4 cores × 50 = 200).

#### Serialização
```bash
--conf spark.serializer=org.apache.spark.serializer.KryoSerializer
```
**Ganho**: 2-10x mais rápido que Java serialization.

#### Compressão Columnar
```bash
--conf spark.sql.inMemoryColumnarStorage.compressed=true
--conf spark.sql.inMemoryColumnarStorage.batchSize=10000
```
**Ganho**: Menos memória, melhor cache.

#### Speculation
```bash
--conf spark.speculation=true
--conf spark.speculation.multiplier=2
--conf spark.speculation.quantile=0.75
```
**Ganho**: Re-executa tasks lentas em outros executores.

### 3. Melhorias na Infraestrutura

#### Docker Compose - Aumentar Recursos
```yaml
spark-worker-1:
  environment:
    - SPARK_WORKER_MEMORY=6g    # ANTES: 4g
    - SPARK_WORKER_CORES=4      # ANTES: 2
```

#### Adicionar Mais Workers
```yaml
spark-worker-3:
  build:
    context: .
    dockerfile: docker/Dockerfile.spark
  container_name: spark-worker-3
  command: /opt/spark/bin/spark-class org.apache.spark.deploy.worker.Worker spark://spark-master:7077
  environment:
    - SPARK_WORKER_MEMORY=4g
    - SPARK_WORKER_CORES=2
```

### 4. Otimizações de Algoritmo

#### Melhorar Blocking Strategy
```python
# ATUAL: Primeiras 3 letras + ano
blocking_key = concat_ws("_", 
                col("nome_completo").substr(1, 3),
                col("data_nascimento").substr(1, 4))

# MELHOR: Soundex + ano + mês
from pyspark.sql.functions import soundex, substring

blocking_key = concat_ws("_",
                soundex(col("nome_completo")),
                substring(col("data_nascimento"), 1, 7))  # YYYY-MM
```

#### Pré-filtrar Pares Óbvios
```python
# Eliminar pares onde a diferença de idade > 5 anos
from pyspark.sql.functions import abs, year

joined = joined.filter(
    abs(year(col("data_nascimento_1")) - year(col("data_nascimento_2"))) <= 5
)
```

#### Usar MinHash LSH para Similaridade
```python
from pyspark.ml.feature import MinHashLSH, NGram, HashingTF

# Criar assinaturas MinHash para comparação rápida
mh = MinHashLSH(inputCol="features", outputCol="hashes", numHashTables=3)
model = mh.fit(dataset)
similar_pairs = model.approxSimilarityJoin(df1, df2, threshold=0.3)
```

### 5. Particionamento de Dados

#### Particionar Datasets por Blocking Key
```python
# Ao salvar dados
df.write \
  .partitionBy("blocking_key_prefix") \
  .parquet(output_path)

# Leitura se torna mais eficiente
df = spark.read.parquet(path).filter(col("blocking_key_prefix") == "A_1990")
```

### 6. Benchmark e Monitoramento

#### Spark UI
```bash
# Acesse durante execução
http://localhost:4040
```
**Métricas importantes**:
- Stage duration
- Task skew
- Shuffle read/write
- GC time

#### Comandos de Benchmark
```bash
# Tempo de execução
time ./run_matching.sh

# Uso de CPU
docker stats

# Logs detalhados
docker-compose logs -f spark-master | grep "INFO"
```

## 📈 Estimativas de Ganho

| Otimização | Ganho Estimado | Dificuldade |
|------------|----------------|-------------|
| Reparticionamento | 20-30% | Baixa |
| AQE habilitado | 15-25% | Baixa |
| Remover count() | 10-20% | Baixa |
| Kryo Serializer | 5-10% | Baixa |
| Mais workers | 50-100% | Média |
| Memória aumentada | 15-30% | Baixa |
| MinHash LSH | 200-500% | Alta |
| Blocking melhorado | 30-50% | Média |

## 🚀 Roadmap de Otimização

### Curto Prazo (Implementado)
- ✅ Configurações Spark otimizadas
- ✅ Reparticionamento inteligente
- ✅ Remoção de count() desnecessários
- ✅ Speculation habilitado

### Médio Prazo
- [ ] Aumentar recursos Docker (8GB RAM, 4 cores por worker)
- [ ] Adicionar 3º worker
- [ ] Implementar blocking key melhorado (Soundex)
- [ ] Pré-filtrar por diferença de idade

### Longo Prazo
- [ ] Implementar MinHash LSH
- [ ] Particionar dados por blocking_key
- [ ] Migrar para Apache Flink
- [ ] Usar GPU para computação de similaridade (RAPIDS)

## 🔍 Debugging de Performance

### Task muito lenta?
```python
# Verificar skew de dados
df.groupBy("blocking_key").count().orderBy(col("count").desc()).show(20)
```

### Muito shuffle?
```python
# Reduzir necessidade de shuffle
df = df.repartition(col("blocking_key"))  # Antes do join
```

### Out of Memory?
```python
# Aumentar partições
spark.conf.set("spark.sql.shuffle.partitions", "400")

# Ou reduzir batch size
spark.conf.set("spark.sql.inMemoryColumnarStorage.batchSize", "5000")
```

### GC overhead?
```bash
# Aumentar memória
--executor-memory 6g
--conf spark.memory.fraction=0.9
```

## 📚 Referências

- [Spark Performance Tuning](https://spark.apache.org/docs/latest/tuning.html)
- [Adaptive Query Execution](https://spark.apache.org/docs/latest/sql-performance-tuning.html#adaptive-query-execution)
- [LSH for Similarity Search](https://spark.apache.org/docs/latest/ml-features.html#lsh-algorithms)
- [Record Linkage Best Practices](https://recordlinkage.readthedocs.io/)
