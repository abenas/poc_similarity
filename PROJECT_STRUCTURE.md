# Estrutura do Projeto

```
poc_lucene/
│
├── 📄 README.md                      # Documentação principal
├── 📄 SOLUTION_SUMMARY.md            # Resumo executivo da solução
├── 📄 Makefile                       # Comandos facilitadores
├── 📄 .gitignore                     # Arquivos ignorados pelo Git
├── 📄 docker-compose.yml             # Orquestração ambiente local
├── 🔧 deploy.sh                      # Script de deploy AWS
│
├── 📁 app/                           # Aplicação Python
│   ├── person_matcher.py             # ⭐ Job Spark principal de matching
│   ├── opensearch_indexer.py         # Indexador OpenSearch
│   ├── generate_test_data.py         # Gerador de dados de teste
│   └── requirements.txt              # Dependências Python
│
├── 📁 lambdas/                       # Funções Lambda
│   └── delta_detector.py             # ⭐ Detecção incremental de mudanças
│
├── 📁 terraform/                     # Infraestrutura como Código
│   ├── main.tf                       # Configuração principal
│   ├── variables.tf                  # Variáveis
│   ├── outputs.tf                    # Outputs
│   ├── vpc.tf                        # ⭐ VPC, subnets, routing
│   ├── emr.tf                        # ⭐ EMR cluster e auto-scaling
│   ├── opensearch.tf                 # ⭐ OpenSearch domain
│   ├── elasticache.tf                # Redis cluster
│   ├── s3.tf                         # Buckets S3
│   ├── glue.tf                       # Glue catalog e crawlers
│   ├── dynamodb.tf                   # Tabelas DynamoDB
│   ├── lambda.tf                     # Lambda functions
│   └── terraform.tfvars.example      # Exemplo de variáveis
│
├── 📁 docker/                        # Containers
│   └── Dockerfile.app                # Container aplicação
│
├── 📁 localstack-init/               # LocalStack (dev local)
│   └── init.sh                       # Script inicialização
│
└── 📁 docs/                          # Documentação
    ├── architecture.md               # ⭐ Arquitetura detalhada
    └── quick-reference.md            # Comandos rápidos

```

## Arquivos Principais (⭐)

### 1. **app/person_matcher.py** (267 linhas)
- Implementação do algoritmo de matching distribuído
- Blocking strategy para otimização
- 5 algoritmos de similaridade combinados
- Integração com Glue Catalog
- Escrita de resultados em S3

### 2. **lambdas/delta_detector.py** (236 linhas)
- Detecção de mudanças em S3
- Comparação de hashes de metadata
- Disparo automático de jobs EMR
- State tracking em DynamoDB
- Processamento apenas de deltas

### 3. **terraform/emr.tf** (200+ linhas)
- Configuração completa do cluster EMR
- Auto-scaling policies
- Security groups
- IAM roles e policies
- Configurações Spark otimizadas

### 4. **terraform/opensearch.tf** (150+ linhas)
- Domain OpenSearch em VPC
- Multi-AZ deployment
- Encryption at-rest e in-transit
- CloudWatch logs integration
- Index mapping otimizado

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
README.md               → Guia principal
SOLUTION_SUMMARY.md     → Resumo executivo
architecture.md         → Arquitetura detalhada
quick-reference.md      → Referência rápida
```

## Estatísticas

- **Total de arquivos**: ~30
- **Linhas de código Python**: ~1,500
- **Linhas de Terraform**: ~2,000
- **Linhas de documentação**: ~2,500
- **Componentes AWS**: 15+ serviços

## Tecnologias

### Backend
- Python 3.11
- PySpark 3.5
- Levenshtein, Jellyfish, Phonetics

### Infraestrutura
- AWS EMR, OpenSearch, ElastiCache
- S3, Glue, DynamoDB, Lambda
- Terraform 1.5+

### DevOps
- Docker & Docker Compose
- LocalStack
- Makefile

### Algoritmos
- Levenshtein Distance
- Jaro-Winkler Similarity
- Soundex (phonetic)
- Blocking Strategy
- Distributed Computing

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
