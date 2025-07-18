provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "fraud-detection"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
