# Quick Reference Guide

## 🚀 Comandos Rápidos

### Desenvolvimento Local

```bash
# Iniciar ambiente completo
docker-compose up -d

# Verificar status
docker-compose ps

# Logs
docker-compose logs -f spark-master

# Parar ambiente
docker-compose down

# Limpar volumes
docker-compose down -v
```

### Gerar Dados de Teste

```bash
# 10k registros (dev)
python app/generate_test_data.py --records 10000

# 1M registros (teste)
python app/generate_test_data.py --records 1000000

# 10M registros com alta sobreposição
python app/generate_test_data.py --records 10000000 --overlap 0.5
```

### Executar Matching Local

```bash
# Via container
docker-compose exec app spark-submit \
  --master spark://spark-master:7077 \
  /app/person_matcher.py \
  person_data dataset1 dataset2 /data/output 0.7

# Via Jupyter
# Acesse http://localhost:8888 e use notebooks
```

### Deploy AWS

```bash
# Deploy completo
./deploy.sh

# Apenas infrastructure
cd terraform && terraform apply

# Destruir tudo
cd terraform && terraform destroy
```

### Terraform

```bash
# Planejar mudanças
terraform plan -var-file=dev.tfvars

# Aplicar
terraform apply -auto-approve

# Ver outputs
terraform output

# Destruir recurso específico
terraform destroy -target=aws_emr_cluster.main
```

### AWS CLI

```bash
# Upload datasets
aws s3 cp data/dataset1.parquet s3://person-matching-data-source1-dev/
aws s3 cp data/dataset2.parquet s3://person-matching-data-source2-dev/

# Trigger Lambda manualmente
aws lambda invoke \
  --function-name person-matching-delta-detector \
  --payload '{}' \
  response.json

# Listar steps EMR
aws emr list-steps --cluster-id j-XXXXXXXXXXXXX

# Ver logs step
aws emr describe-step \
  --cluster-id j-XXXXXXXXXXXXX \
  --step-id s-XXXXXXXXXXXXX

# Glue crawlers
aws glue start-crawler --name person-matching-dataset1-crawler
aws glue get-crawler --name person-matching-dataset1-crawler
```

### OpenSearch

```bash
# Health check
curl https://<opensearch-endpoint>/_cluster/health

# Listar índices
curl https://<opensearch-endpoint>/_cat/indices?v

# Buscar por documento
curl -X POST "https://<opensearch-endpoint>/person-matches/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "bool": {
        "should": [
          {"term": {"nr_documento_1": "12345678900"}},
          {"term": {"nr_documento_2": "12345678900"}}
        ]
      }
    },
    "size": 10
  }'

# Deletar índice
curl -X DELETE "https://<opensearch-endpoint>/person-matches"
```

## 📊 Monitoramento

### CloudWatch Metrics

```bash
# EMR memory
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElasticMapReduce \
  --metric-name YARNMemoryAvailablePercentage \
  --dimensions Name=JobFlowId,Value=j-XXXXXXXXXXXXX \
  --start-time 2024-11-17T00:00:00Z \
  --end-time 2024-11-17T23:59:59Z \
  --period 3600 \
  --statistics Average

# Lambda errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=person-matching-delta-detector \
  --start-time 2024-11-17T00:00:00Z \
  --end-time 2024-11-17T23:59:59Z \
  --period 300 \
  --statistics Sum
```

### CloudWatch Logs

```bash
# Lambda logs
aws logs tail /aws/lambda/person-matching-delta-detector --follow

# EMR step logs
aws logs tail /aws/emr/j-XXXXXXXXXXXXX/steps/s-XXXXXXXXXXXXX --follow
```

## 🐛 Troubleshooting

### EMR Cluster não inicia

```bash
# Verificar service role
aws iam get-role --role-name person-matching-emr-service-role

# Verificar security groups
aws ec2 describe-security-groups --group-ids sg-XXXXXXXXXXXXX
```

### Lambda timeout

```bash
# Aumentar timeout
aws lambda update-function-configuration \
  --function-name person-matching-delta-detector \
  --timeout 900

# Verificar logs
aws logs tail /aws/lambda/person-matching-delta-detector --since 1h
```

### OpenSearch cluster red

```bash
# Ver status detalhado
curl https://<endpoint>/_cluster/health?pretty

# Listar unassigned shards
curl https://<endpoint>/_cat/shards?v | grep UNASSIGNED

# Reallocar shard
curl -X POST "https://<endpoint>/_cluster/reroute" \
  -H 'Content-Type: application/json' \
  -d '{
    "commands": [{
      "allocate_replica": {
        "index": "person-matches",
        "shard": 0,
        "node": "node-1"
      }
    }]
  }'
```

### Spark job lento

```bash
# Ver Spark UI
# http://<emr-master-dns>:18080

# Verificar partições
df.rdd.getNumPartitions()

# Repartition
df = df.repartition(200)

# Verificar skew
df.groupBy("blocking_key").count().orderBy("count", ascending=False).show()
```

## 🔐 Segurança

### Rotação de credenciais

```bash
# Criar nova key pair EMR
aws ec2 create-key-pair --key-name emr-new-key --query 'KeyMaterial' --output text > emr-new-key.pem

# Atualizar cluster (requer recreate)
terraform taint aws_emr_cluster.main
terraform apply
```

### Audit logs

```bash
# S3 access logs
aws s3api put-bucket-logging \
  --bucket person-matching-data-source1-dev \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "person-matching-logs-dev",
      "TargetPrefix": "s3-access-logs/"
    }
  }'

# CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::S3::Bucket \
  --max-results 10
```

## 📈 Performance Tuning

### Spark Configuration

```python
# Para datasets grandes (>100GB)
spark.conf.set("spark.sql.shuffle.partitions", "400")
spark.conf.set("spark.sql.files.maxPartitionBytes", "268435456")  # 256MB

# Para clusters grandes (>10 nodes)
spark.conf.set("spark.default.parallelism", "200")
spark.conf.set("spark.sql.adaptive.coalescePartitions.initialPartitionNum", "400")

# Memory tuning
spark.conf.set("spark.executor.memoryOverhead", "4096")
spark.conf.set("spark.memory.fraction", "0.8")
```

### OpenSearch Tuning

```bash
# Aumentar refresh interval
curl -X PUT "https://<endpoint>/person-matches/_settings" \
  -H 'Content-Type: application/json' \
  -d '{"index": {"refresh_interval": "30s"}}'

# Bulk indexing
curl -X POST "https://<endpoint>/_bulk" \
  -H 'Content-Type: application/x-ndjson' \
  --data-binary @bulk_data.ndjson
```

## 🧪 Testes

### Unit tests

```bash
cd app
pytest tests/ -v
```

### Integration tests

```bash
# Teste end-to-end local
docker-compose up -d
python tests/integration/test_full_pipeline.py
```

### Load tests

```bash
# Gerar dataset grande
python app/generate_test_data.py --records 10000000

# Executar matching
time docker-compose exec app spark-submit /app/person_matcher.py ...
```

## 📦 Backup & Restore

### Backup OpenSearch

```bash
# Registrar repository
curl -X PUT "https://<endpoint>/_snapshot/s3-repo" \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "s3",
    "settings": {
      "bucket": "person-matching-snapshots",
      "region": "us-east-1"
    }
  }'

# Criar snapshot
curl -X PUT "https://<endpoint>/_snapshot/s3-repo/snapshot-$(date +%Y%m%d)"

# Restore
curl -X POST "https://<endpoint>/_snapshot/s3-repo/snapshot-20241117/_restore"
```

### Backup DynamoDB

```bash
# Export to S3
aws dynamodb export-table-to-point-in-time \
  --table-name person-matching-state \
  --s3-bucket person-matching-backups \
  --s3-prefix dynamodb-exports/
```

---

**Documento:** Quick Reference  
**Versão:** 1.0  
**Data:** 2024-11-17
