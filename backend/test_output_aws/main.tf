# Auto-generated Terraform configuration

resource "aws_vpc" "main_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  instance_tenancy     = "default"

  tags = merge(
    {
      Name        = "main-vpc"
      Environment = ""
      Project     = ""
    },
{"Environment": "production", "Project": "iac4-test"}  )
}

resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.main_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = merge(
    {
      Name        = "public-subnet-1"
      Environment = ""
      Project     = ""
      Type        = "Private"
    },
{"Name": "public-subnet-1", "Type": "public"}  )
}

resource "aws_security_group" "web_sg" {
  name        = "web-sg"
  description = "Security group for web servers"
  vpc_id      = aws_vpc.main_vpc.id

  ingress {
    description = "Allow HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Allow HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    {
      Name        = "web-sg"
      Environment = ""
      Project     = ""
    },
{"Name": "web-sg"}  )
}

resource "aws_instance" "web_server_1" {
  ami                         = "ami-0c55b159cbfafe1f0"
  instance_type               = "t3.medium"
  subnet_id                   = aws_subnet.public_subnet_1.id
  vpc_security_group_ids      = [
    aws_security_group.web_sg.id
  ]
  key_name                    = "my-keypair"
  associate_public_ip_address = false
  monitoring                  = false

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  user_data = <<-EOF
#!/bin/bash
apt-get update
apt-get install -y nginx
  EOF


  tags = merge(
    {
      Name        = "web-server-1"
      Environment = ""
      Project     = ""
    },
{"Name": "web-server-1", "Role": "webserver"}  )
}

resource "aws_s3_bucket" "iac4_test_bucket" {
  bucket = "iac4-test-bucket-12345"

  tags = merge(
    {
      Name        = "iac4-test-bucket"
      Environment = ""
      Project     = ""
    },
{"Purpose": "application-data"}  )
}

resource "aws_s3_bucket_versioning" "iac4_test_bucket" {
  bucket = aws_s3_bucket.iac4_test_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "iac4_test_bucket" {
  bucket = aws_s3_bucket.iac4_test_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "iac4_test_bucket" {
  bucket = aws_s3_bucket.iac4_test_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


