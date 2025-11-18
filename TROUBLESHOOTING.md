# 🔧 Troubleshooting Guide

## Problemas Comuns e Soluções

### 🐳 Docker / Desenvolvimento Local

#### Container não inicia

**Sintoma**: `docker-compose up` falha

**Soluções**:
```bash
# 1. Verificar portas em uso
sudo lsof -i :8080  # Spark
sudo lsof -i :9200  # OpenSearch
sudo lsof -i :6379  # Redis

# 2. Limpar containers antigos
docker-compose down -v
docker system prune -a

# 3. Reconstruir imagens
docker-compose build --no-cache
docker-compose up -d
```

#### OpenSearch não fica green

**Sintoma**: Cluster status yellow/red

**Soluções**:
```bash
# Verificar status
curl http://localhost:9200/_cluster/health?pretty

# Aumentar memória
# Editar docker-compose.yml
OPENSEARCH_JAVA_OPTS: "-Xms4g -Xmx4g"

# Reiniciar
docker-compose restart opensearch
```

#### Spark worker desconecta

**Sintoma**: Workers não aparecem no UI

**Soluções**:
```bash
# Ver logs
docker-compose logs spark-worker-1

# Aumentar memória worker
# Editar docker-compose.yml
SPARK_WORKER_MEMORY: "8G"

# Restart workers
docker-compose restart spark-worker-1 spark-worker-2
```

---

### ☁️ AWS / Terraform

#### Terraform apply falha

**Sintoma**: Erro ao criar recursos

**Soluções**:
```bash
# 1. Verificar credenciais AWS
aws sts get-caller-identity

# 2. Verificar quotas
aws service-quotas list-service-quotas \
  --service-code elasticmapreduce

# 3. Validar terraform
cd terraform
terraform validate
terraform fmt -check

# 4. Reiniciar terraform
rm -rf .terraform .terraform.lock.hcl
terraform init
terraform plan
```

**Erros comuns**:

```
Error: InvalidInstanceType
Solução: Escolha instance type disponível na região
terraform plan -var="emr_core_instance_type=m5.xlarge"

Error: InsufficientCapacity
Solução: Tente outra AZ ou use Spot instances

Error: VPC limit exceeded
Solução: Delete VPCs não utilizadas ou solicite aumento de quota
```

#### EMR Cluster não inicia

**Sintoma**: Cluster fica em STARTING por muito tempo

**Soluções**:
```bash
# 1. Verificar logs bootstrap
aws emr describe-cluster --cluster-id j-XXXXX

# 2. Verificar security groups
aws ec2 describe-security-groups --group-ids sg-XXXXX

# 3. Verificar subnet
# Certifique-se que subnet privada tem NAT gateway

# 4. Verificar service role
aws iam get-role --role-name person-matching-emr-service-role
```

#### OpenSearch cluster red

**Sintoma**: Cluster status RED

**Soluções**:
```bash
# 1. Verificar shards
curl https://<endpoint>/_cat/shards?v | grep UNASSIGNED

# 2. Realocar shards
curl -X POST "https://<endpoint>/_cluster/reroute?retry_failed=true"

# 3. Aumentar nodes
# Editar terraform/opensearch.tf
opensearch_instance_count = 5
terraform apply

# 4. Verificar disk space
curl https://<endpoint>/_cat/allocation?v

# 5. Se crítico: restore snapshot
aws opensearch describe-domain --domain-name person-matching-dev
```

#### Lambda timeout

**Sintoma**: Lambda execution timeout

**Soluções**:
```bash
# 1. Aumentar timeout
aws lambda update-function-configuration \
  --function-name person-matching-delta-detector \
  --timeout 900

# 2. Aumentar memória
aws lambda update-function-configuration \
  --function-name person-matching-delta-detector \
  --memory-size 1024

# 3. Verificar VPC NAT gateway
# Lambda em VPC precisa NAT para acessar AWS services

# 4. Ver logs detalhados
aws logs tail /aws/lambda/person-matching-delta-detector \
  --since 1h --format short
```

---

### 🔥 Spark / Processamento

#### Job Spark falha com OOM

**Sintoma**: `java.lang.OutOfMemoryError`

**Soluções**:
```python
# 1. Aumentar executor memory
spark.conf.set("spark.executor.memory", "20g")
spark.conf.set("spark.executor.memoryOverhead", "4g")

# 2. Aumentar partições
spark.conf.set("spark.sql.shuffle.partitions", "400")

# 3. Repartition dataframe
df = df.repartition(200, "blocking_key")

# 4. Cache com cuidado
# Só cache o que for reutilizado
df.cache()
# ... usar df várias vezes ...
df.unpersist()

# 5. Usar persist em disco se necessário
df.persist(StorageLevel.MEMORY_AND_DISK)
```

#### Job muito lento

**Sintoma**: Processing time > esperado

**Diagnóstico**:
```bash
# 1. Acessar Spark UI
http://<emr-master-dns>:18080

# 2. Verificar:
- Skew de dados (tarefas desbalanceadas)
- Shuffle excessivo
- GC time alto
- Stages falhando
```

**Otimizações**:
```python
# 1. Broadcast joins para tabelas pequenas
df_small_broadcast = broadcast(df_small)
result = df_large.join(df_small_broadcast, "key")

# 2. Filtrar cedo
df = df.filter(col("status") == "Ativo")  # Antes de joins

# 3. Selecionar apenas colunas necessárias
df = df.select("nome", "data_nascimento", "nr_documento")

# 4. Usar AQE
spark.conf.set("spark.sql.adaptive.enabled", "true")

# 5. Salting para data skew
df = df.withColumn("salt", (rand() * 10).cast("int"))
df = df.repartition("blocking_key", "salt")
```

#### Blocking key com skew

**Sintoma**: Algumas partições muito maiores

**Soluções**:
```python
# 1. Adicionar salt ao blocking key
df = df.withColumn(
    "blocking_key_salted",
    concat(col("blocking_key"), lit("_"), (rand() * 5).cast("int"))
)

# 2. Multi-level blocking
# Primeiro blocking: year
# Segundo blocking: first 3 chars
df = df.withColumn("blocking_key_1", year(col("data_nascimento")))
df = df.withColumn("blocking_key_2", substring(col("nome"), 1, 3))

# 3. Adaptive partitioning
df.repartition(200).write.option("maxRecordsPerFile", 100000).parquet(path)
```

---

### 🔍 OpenSearch

#### Indexação lenta

**Sintoma**: Bulk indexing timeout

**Soluções**:
```python
# 1. Aumentar refresh interval durante bulk
PUT /person-matches/_settings
{
  "index": {
    "refresh_interval": "30s",
    "number_of_replicas": 0
  }
}

# Após indexação:
PUT /person-matches/_settings
{
  "index": {
    "refresh_interval": "1s",
    "number_of_replicas": 1
  }
}

# 2. Usar bulk API com batch size otimizado
batch_size = 1000  # Testar entre 500-2000

# 3. Aumentar thread pool
PUT /_cluster/settings
{
  "transient": {
    "threadpool.write.queue_size": 1000
  }
}
```

#### Busca lenta

**Sintoma**: Query time > 1s

**Soluções**:
```bash
# 1. Analisar slow logs
GET /person-matches/_settings/index.search.slowlog*

# 2. Usar explain API
GET /person-matches/_search
{
  "explain": true,
  "query": {...}
}

# 3. Otimizar query
# Usar term queries para campos keyword
{
  "query": {
    "term": {"nr_documento_1": "12345"}  # Mais rápido que match
  }
}

# 4. Force merge para reduzir segments
POST /person-matches/_forcemerge?max_num_segments=1
```

---

### 💾 S3 / Glue

#### Crawler não encontra dados

**Sintoma**: Glue table vazia

**Soluções**:
```bash
# 1. Verificar path S3
aws s3 ls s3://person-matching-data-source1-dev/

# 2. Verificar permissões IAM
aws iam get-role-policy \
  --role-name person-matching-glue-crawler-role \
  --policy-name person-matching-glue-s3-policy

# 3. Verificar formato arquivo
# Glue detecta: Parquet, JSON, CSV, Avro
# Arquivo deve ter extensão correta (.parquet)

# 4. Re-run crawler
aws glue start-crawler --name person-matching-dataset1-crawler
aws glue get-crawler --name person-matching-dataset1-crawler
```

#### Schema evolution

**Sintoma**: Colunas novas não aparecem

**Soluções**:
```bash
# 1. Configurar crawler para UPDATE_IN_DATABASE
aws glue update-crawler --name person-matching-dataset1-crawler \
  --schema-change-policy '{
    "UpdateBehavior": "UPDATE_IN_DATABASE",
    "DeleteBehavior": "LOG"
  }'

# 2. Re-run crawler
aws glue start-crawler --name person-matching-dataset1-crawler

# 3. Ou atualizar tabela manualmente
aws glue update-table --database-name person_data \
  --table-input file://new_schema.json
```

---

### 📊 Performance Issues

#### Alto custo

**Sintoma**: Bill AWS maior que esperado

**Análise**:
```bash
# 1. Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2024-11-01,End=2024-11-30 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# 2. Verificar recursos ociosos
aws emr list-clusters --active
aws opensearch list-domain-names
aws elasticache describe-replication-groups
```

**Otimizações de custo**:
```bash
# 1. Usar Spot instances EMR (70% economia)
# Editar terraform/emr.tf
market = "SPOT"
bid_price = "0.30"

# 2. Auto-scaling agressivo
emr_min_capacity = 1
emr_max_capacity = 5

# 3. Schedule start/stop EMR
# Lambda para stop cluster quando não usado

# 4. S3 Intelligent-Tiering
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket person-matching-results-dev \
  --id config1 \
  --intelligent-tiering-configuration file://tiering.json

# 5. OpenSearch Reserved Instances
# 1-year: 30% desconto
# 3-years: 50% desconto
```

---

### 🚨 Erros Comuns

#### "Access Denied" S3

```bash
# Verificar bucket policy
aws s3api get-bucket-policy --bucket person-matching-data-source1-dev

# Verificar IAM role
aws iam get-role-policy --role-name person-matching-emr-ec2-role \
  --policy-name person-matching-emr-ec2-policy

# Testar acesso
aws s3 ls s3://person-matching-data-source1-dev/ \
  --profile emr-role
```

#### "ResourceNotFoundException" DynamoDB

```bash
# Verificar tabela existe
aws dynamodb describe-table --table-name person-matching-state

# Verificar região correta
aws dynamodb list-tables --region us-east-1

# Recriar tabela
cd terraform
terraform taint aws_dynamodb_table.state
terraform apply
```

#### "ClusterNotFoundException" EMR

```bash
# Listar clusters
aws emr list-clusters --active

# Se não existe, criar
cd terraform
terraform apply

# Se existe mas não aparece, verificar região
aws emr list-clusters --region us-east-1
```

---

### 📞 Suporte

#### Logs para debug

```bash
# Coletar todos logs relevantes
mkdir debug-logs
cd debug-logs

# Terraform
terraform show > terraform-state.txt

# EMR
aws emr describe-cluster --cluster-id j-XXX > emr-cluster.json
aws logs get-log-events --log-group-name /aws/emr/XXX > emr-logs.txt

# Lambda
aws logs tail /aws/lambda/person-matching-delta-detector > lambda-logs.txt

# OpenSearch
curl https://<endpoint>/_cluster/health > opensearch-health.json
curl https://<endpoint>/_cat/indices?v > opensearch-indices.txt

# Zipar e enviar
zip -r debug-logs.zip .
```

#### Checklist debug

```
□ AWS credentials válidas
□ Região correta configurada
□ VPC e subnets corretas
□ Security groups permitem tráfego
□ IAM roles têm permissões necessárias
□ S3 buckets existem e têm dados
□ Glue tables criadas e populadas
□ EMR cluster RUNNING
□ OpenSearch cluster GREEN
□ Lambda sem erros
□ CloudWatch logs sem errors
□ Billing alerts configurados
```

---

**Última atualização**: 2024-11-17  
**Versão**: 1.0
