#!/bin/bash
set -e

BUCKET_NAME="live-fraud-detector-terraform-state"
REGION="us-east-1"
TABLE_NAME="terraform-state-lock"

while [[ $# -gt 0 ]]; do
  case $1 in
    --bucket-name)
      BUCKET_NAME="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --table-name)
      TABLE_NAME="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --bucket-name NAME    S3 bucket name for Terraform state (default: your-terraform-state-bucket)"
      echo "  --region REGION       AWS region (default: us-east-1)"
      echo "  --table-name NAME     DynamoDB table name for state locking (default: terraform-state-lock)"
      echo "  --help                Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo "Starting Terraform backend bootstrap..."
echo "S3 Bucket: $BUCKET_NAME"
echo "Region: $REGION"
echo "DynamoDB Table: $TABLE_NAME"

if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "AWS credentials are not configured. Please run 'aws configure' first."
    exit 1
fi

echo "AWS CLI and credentials verified"

echo "Creating S3 bucket for Terraform state..."
if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://$BUCKET_NAME" --region "$REGION"
    echo "S3 bucket '$BUCKET_NAME' created successfully"
else
    echo "S3 bucket '$BUCKET_NAME' already exists"
fi

echo "Enabling versioning on S3 bucket..."
aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled
echo "Versioning enabled on S3 bucket"

echo "Creating DynamoDB table for state locking..."
if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" 2>&1 | grep -q 'ResourceNotFoundException'; then
    aws dynamodb create-table \
        --table-name "$TABLE_NAME" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$REGION"

    echo "Waiting for DynamoDB table to be active..."
    aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"
    echo "DynamoDB table '$TABLE_NAME' created successfully"
else
    echo "DynamoDB table '$TABLE_NAME' already exists"
fi

echo ""
echo "Terraform backend setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Update terraform.tfvars file with these values:"
echo "   terraform_state_bucket = \"$BUCKET_NAME\""
echo "   terraform_state_region = \"$REGION\""
echo "   terraform_state_dynamodb_table = \"$TABLE_NAME\""
echo ""
echo "2. Run 'terraform init' to initialize the backend"
echo "3. Run 'terraform plan' to review the infrastructure changes"
echo "4. Run 'terraform apply' to deploy the infrastructure"
