# Estrutura do Projeto

```
poc_similarity/
│
├── 📄 README.md                           # Documentação principal
├── 📄 SOLUTION_SUMMARY.md                 # Resumo executivo da solução
├── 📄 SECURITY_FIXES_IMPLEMENTED.md       # ⭐ Correções de segurança aplicadas
├── 📄 SECURITY_RECOMMENDATIONS.md         # Relatório Checkov e próximos passos
├── 📄 SECURITY_COMPLIANCE_SUMMARY.md      # ⭐ Resumo de compliance e auditoria
├── 📄 PROJECT_STRUCTURE.md                # Este arquivo
├── 📄 Makefile                            # Comandos facilitadores
├── 📄 .gitignore                          # Arquivos ignorados pelo Git
├── 📄 docker-compose.yml                  # Orquestração ambiente local
├── 🔧 deploy.sh                           # Script de deploy AWS
│
├── 📁 app/                                # Aplicação Python
│   ├── person_matcher.py                  # ⭐ Job Spark principal de matching
│   ├── person_matcher_local.py            # Versão local para testes
│   ├── opensearch_indexer.py              # Indexador OpenSearch
│   ├── index_matches.py                   # Indexação de matches
│   ├── name_search.py                     # Busca por nome
│   ├── search_opensearch.py               # Cliente OpenSearch
│   ├── generate_test_data.py              # Gerador de dados de teste
│   └── requirements.txt                   # Dependências Python
│
├── 📁 lambdas/                            # Funções Lambda
│   └── delta_detector.py                  # ⭐ Detecção incremental de mudanças
│
├── 📁 terraform/                          # Infraestrutura como Código ⭐
│   ├── main.tf                            # Configuração principal + provider
│   ├── variables.tf                       # Variáveis de configuração
│   ├── outputs.tf                         # Outputs (endpoints, ARNs, etc)
│   ├── vpc.tf                             # ⭐ VPC, subnets, NAT, flow logs
│   ├── emr.tf                             # ⭐ EMR cluster + security config
│   ├── opensearch.tf                      # ⭐ OpenSearch + audit logs
│   ├── elasticache.tf                     # Redis + Multi-AZ + auth token
│   ├── s3.tf                              # 5 buckets + encryption + logging
│   ├── glue.tf                            # Glue catalog + security config
│   ├── dynamodb.tf                        # Tabelas DynamoDB + KMS
│   ├── lambda.tf                          # Lambda + X-Ray + DLQ + KMS
│   ├── kms.tf                             # ⭐ 7 KMS keys com policies
│   ├── terraform.tfvars.example           # Exemplo de variáveis
│   └── terraform.tfvars                   # Variáveis (não versionado)
│
├── 📁 docker/                             # Containers
│   ├── Dockerfile.app                     # Container aplicação
│   └── Dockerfile.spark                   # Container Spark local
│
├── 📁 localstack-init/                    # LocalStack (dev local)
│   ├── init.sh                            # Script inicialização
│   └── 01-create-buckets.sh               # Criação de buckets S3
│
├── 📁 scripts/                            # Scripts utilitários
│   ├── deploy.sh                          # Deploy completo
│   ├── benchmark.sh                       # Benchmark de performance
│   ├── run_matching.sh                    # Executar matching
│   ├── index_to_opensearch.sh             # Indexar resultados
│   ├── search_name.sh                     # Buscar por nome
│   └── search_opensearch.sh               # Buscar no OpenSearch
│
├── 📁 docs/                               # Documentação detalhada
│   ├── architecture.md                    # ⭐ Arquitetura completa
│   ├── PERFORMANCE_GUIDE.md               # Guia de otimização
│   └── quick-reference.md                 # Comandos rápidos
│
├── 📁 data/                               # Dados locais (gitignored)
├── 📁 notebooks/                          # Jupyter notebooks (análise)
└── 📁 benchmark_results/                  # Resultados de testes
```

## Arquivos Principais (⭐)

### 1. **app/person_matcher.py** (267 linhas)
- Implementação do algoritmo de matching distribuído
- Blocking strategy para otimização O(n log n)
- 5 algoritmos de similaridade combinados
- Integração com Glue Catalog
- Escrita de resultados em S3 Parquet

### 2. **lambdas/delta_detector.py** (236 linhas)
- Detecção de mudanças em S3 via eventos
- Comparação de hashes de metadata
- Disparo automático de jobs EMR
- State tracking em DynamoDB
- Processamento apenas de deltas (eficiência)

### 3. **terraform/emr.tf** (350+ linhas)
- Configuração completa do cluster EMR
- Auto-scaling policies (3-10 nodes)
- Security groups com regras específicas
- IAM roles e policies (least privilege)
- Configurações Spark otimizadas (AQE, Kryo)
- **EMR security configuration** com encryption

### 4. **terraform/opensearch.tf** (220+ linhas)
- Domain OpenSearch em VPC privada
- Multi-AZ deployment (3 data + 3 master)
- Encryption at-rest (KMS) e in-transit (TLS)
- **4 tipos de logs:** index, search, application, audit
- Fine-grained access control habilitado
- Index mapping otimizado para matching

### 5. **terraform/kms.tf** (340+ linhas) ⭐ NOVO
- **7 KMS Keys segregadas** por serviço
- Policies específicas para cada key
- Rotation habilitada em todas
- Keys: S3, Logs, DynamoDB, ElastiCache, OpenSearch, Secrets, SQS, Lambda

### 6. **terraform/vpc.tf** (190+ linhas)
- VPC isolada com CIDR /16
- Subnets públicas e privadas em 2 AZs
- NAT Gateways redundantes
- **VPC Flow Logs** para auditoria
- **Default Security Group** bloqueado
- Route tables otimizadas

### 7. **SECURITY_COMPLIANCE_SUMMARY.md** ⭐ NOVO
- Resumo executivo de compliance
- 93%+ de aprovação em security checks
- Análise de riscos e mitigações
- Documentação de todas proteções implementadas

### 5. **terraform/vpc.tf** (120+ linhas)
- VPC isolada
- Subnets públicas e privadas
- NAT Gateways
- VPC Endpoints (S3, DynamoDB)
- Route tables

## Componentes por Categoria

### Processamento de Dados
```
person_matcher.py       → Matching distribuído com Spark
opensearch_indexer.py   → Indexação de resultados
generate_test_data.py   → Geração de dados sintéticos
```

### Infraestrutura AWS
```
emr.tf                  → Computação distribuída
opensearch.tf           → Busca e indexação
elasticache.tf          → Cache Redis
s3.tf                   → Storage
glue.tf                 → Data catalog
dynamodb.tf             → State tracking
lambda.tf               → Orquestração
vpc.tf                  → Networking
```

### Orquestração e Deploy
```
delta_detector.py       → Detecção incremental
deploy.sh               → Script de deployment
docker-compose.yml      → Ambiente local
Makefile                → Comandos úteis
```

### Documentação
```
README.md                        → Guia principal + quick start
SOLUTION_SUMMARY.md              → Resumo executivo completo
SECURITY_FIXES_IMPLEMENTED.md    → Todas correções de segurança
SECURITY_RECOMMENDATIONS.md      → Relatório Checkov
SECURITY_COMPLIANCE_SUMMARY.md   → Auditoria e compliance
PROJECT_STRUCTURE.md             → Este arquivo
architecture.md                  → Arquitetura detalhada
PERFORMANCE_GUIDE.md             → Otimizações
quick-reference.md               → Referência rápida
```

## Estatísticas

- **Total de arquivos**: 50+
- **Linhas de código Python**: ~1,500
- **Linhas de Terraform**: ~2,500+
- **Linhas de documentação**: ~4,000+
- **Componentes AWS**: 15+ serviços
- **KMS Keys**: 7 (segregadas por serviço)
- **Security Checks**: 500+ (93%+ passing)

## Tecnologias

### Backend
- Python 3.11
- PySpark 3.5
- Levenshtein, Jellyfish, Phonetics
- OpenSearch Python Client

### Infraestrutura AWS
- **Compute**: EMR (Spark), Lambda
- **Storage**: S3, DynamoDB
- **Search**: OpenSearch
- **Cache**: ElastiCache Redis
- **Catalog**: AWS Glue
- **Network**: VPC, Security Groups, NAT Gateway
- **Security**: KMS, Secrets Manager, IAM
- **Monitoring**: CloudWatch, VPC Flow Logs, X-Ray

### DevOps & IaC
- Terraform 1.5+
- Docker & Docker Compose
- LocalStack
- Makefile
- Checkov (security scanning)

### Algoritmos
- Levenshtein Distance (edit distance)
- Jaro-Winkler Similarity (names)
- Soundex (phonetic matching)
- Blocking Strategy (performance)
- Distributed Computing (Spark)

### Segurança Implementada
- **Encryption**: KMS em todas camadas
- **Network**: VPC isolation, Security Groups
- **Access Control**: IAM least privilege
- **Audit**: CloudWatch Logs (365 dias)
- **HA**: Multi-AZ deployment
- **Compliance**: 93%+ Checkov approval

## Próximos Arquivos Recomendados

```
📁 tests/                           # Testes unitários e integração
├── test_person_matcher.py
├── test_opensearch_indexer.py
└── test_delta_detector.py

📁 notebooks/                       # Jupyter notebooks
├── exploratory_analysis.ipynb
└── algorithm_comparison.ipynb

📁 scripts/                         # Scripts utilitários
├── benchmark.py
└── data_quality_check.py

📁 .github/workflows/              # CI/CD
└── terraform.yml

📄 .pre-commit-config.yaml         # Pre-commit hooks
📄 pyproject.toml                  # Python config
📄 pytest.ini                      # Pytest config
```

---

**Última atualização**: 2024-11-17
