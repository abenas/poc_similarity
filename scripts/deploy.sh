#!/bin/bash

# Deploy Person Matching Solution to AWS

set -e

echo "🚀 Person Matching Solution - AWS Deployment"
echo "=============================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Please install Terraform >= 1.5.0"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI"
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Get AWS account info
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo "📍 AWS Account: $AWS_ACCOUNT_ID"
echo "📍 AWS Region: $AWS_REGION"
echo ""

# Step 1: Create S3 bucket for Terraform state (if needed)
echo "1️⃣  Setting up Terraform backend..."
TERRAFORM_STATE_BUCKET="person-matching-terraform-state-${AWS_ACCOUNT_ID}"

if ! aws s3 ls "s3://${TERRAFORM_STATE_BUCKET}" 2>/dev/null; then
    echo "Creating Terraform state bucket..."
    aws s3 mb "s3://${TERRAFORM_STATE_BUCKET}" --region ${AWS_REGION}
    aws s3api put-bucket-versioning \
        --bucket ${TERRAFORM_STATE_BUCKET} \
        --versioning-configuration Status=Enabled
    echo "✅ Terraform state bucket created"
else
    echo "✅ Terraform state bucket already exists"
fi
echo ""

# Step 2: Initialize and apply Terraform
echo "2️⃣  Deploying infrastructure with Terraform..."
cd terraform

# Create terraform.tfvars if it doesn't exist
if [ ! -f terraform.tfvars ]; then
    echo "Creating terraform.tfvars from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo "⚠️  Please review and update terraform.tfvars with your values"
    echo "Press Enter to continue after updating..."
    read
fi

# Initialize Terraform
terraform init \
    -backend-config="bucket=${TERRAFORM_STATE_BUCKET}" \
    -backend-config="key=person-matching/terraform.tfstate" \
    -backend-config="region=${AWS_REGION}"

# Plan
echo ""
echo "Planning infrastructure changes..."
terraform plan -out=tfplan

echo ""
echo "⚠️  Review the plan above. Continue with apply? (yes/no)"
read CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Apply
terraform apply tfplan

echo "✅ Infrastructure deployed"
echo ""

# Get outputs
EMR_CLUSTER_ID=$(terraform output -raw emr_cluster_id)
SCRIPTS_BUCKET=$(terraform output -raw s3_bucket_scripts)
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)

cd ..

# Step 3: Upload application scripts
echo "3️⃣  Uploading application scripts to S3..."

aws s3 cp app/person_matcher.py "s3://${SCRIPTS_BUCKET}/person_matcher.py"
aws s3 cp app/opensearch_indexer.py "s3://${SCRIPTS_BUCKET}/opensearch_indexer.py"
aws s3 cp app/requirements.txt "s3://${SCRIPTS_BUCKET}/requirements.txt"

echo "✅ Scripts uploaded"
echo ""

# Step 4: Install Python dependencies on EMR
echo "4️⃣  Installing Python dependencies on EMR..."

BOOTSTRAP_SCRIPT=$(cat <<'EOF'
#!/bin/bash
sudo python3 -m pip install --upgrade pip
sudo python3 -m pip install \
    boto3==1.34.0 \
    opensearch-py==2.4.2 \
    redis==5.0.1 \
    jellyfish==1.0.3 \
    python-Levenshtein==0.23.0 \
    phonetics==1.0.5 \
    recordlinkage==0.16 \
    awswrangler==3.5.2
EOF
)

echo "$BOOTSTRAP_SCRIPT" | aws s3 cp - "s3://${SCRIPTS_BUCKET}/bootstrap.sh"

echo "✅ Bootstrap script uploaded"
echo ""

# Step 5: Start Glue Crawlers
echo "5️⃣  Starting Glue Crawlers..."

aws glue start-crawler --name person-matching-dataset1-crawler || true
aws glue start-crawler --name person-matching-dataset2-crawler || true

echo "✅ Crawlers started (will run in background)"
echo ""

# Summary
echo ""
echo "=============================================="
echo "🎉 Deployment Complete!"
echo "=============================================="
echo ""
echo "📝 Important Information:"
echo ""
echo "EMR Cluster ID: ${EMR_CLUSTER_ID}"
echo "Scripts Bucket: ${SCRIPTS_BUCKET}"
echo "OpenSearch Endpoint: ${OPENSEARCH_ENDPOINT}"
echo ""
echo "📚 Next Steps:"
echo ""
echo "1. Upload your datasets to S3:"
echo "   aws s3 cp dataset1.parquet s3://person-matching-data-source1-dev/"
echo "   aws s3 cp dataset2.parquet s3://person-matching-data-source2-dev/"
echo ""
echo "2. Wait for Glue Crawlers to complete:"
echo "   aws glue get-crawler --name person-matching-dataset1-crawler"
echo ""
echo "3. The Lambda function will automatically trigger on new data"
echo "   Or trigger manually:"
echo "   aws lambda invoke --function-name person-matching-delta-detector output.json"
echo ""
echo "4. Monitor EMR job:"
echo "   aws emr list-steps --cluster-id ${EMR_CLUSTER_ID}"
echo ""
echo "5. Query results via OpenSearch:"
echo "   curl https://${OPENSEARCH_ENDPOINT}/person-matches/_search"
echo ""
echo "=============================================="
