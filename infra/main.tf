terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.70" }
  }
}

variable "region" { type = string }
variable "alert_email" { type = string }

provider "aws" {
  region = var.region
  default_tags { tags = { project = "wiener" } }
}

data "aws_caller_identity" "me" {}

# ---------- Raw Archive ----------
resource "aws_s3_bucket" "raw_archive" {
  bucket = "wiener-raw-archive-${data.aws_caller_identity.me.account_id}"
}

resource "aws_s3_bucket_public_access_block" "raw_archive" {
  bucket                  = aws_s3_bucket.raw_archive.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "raw_archive" {
  bucket = aws_s3_bucket.raw_archive.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_archive" {
  bucket = aws_s3_bucket.raw_archive.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_archive" {
  bucket = aws_s3_bucket.raw_archive.id
  rule {
    id     = "raw-to-glacier-ir"
    status = "Enabled"
    filter { prefix = "raw/" }
    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }
  }
  rule {
    id     = "expire-old-deploy-versions"
    status = "Enabled"
    filter { prefix = "deploy/" }
    noncurrent_version_expiration { noncurrent_days = 7 }
  }
}

# ---------- Alerts ----------
resource "aws_sns_topic" "alerts" { name = "wiener-alerts" }

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ---------- Box ----------
data "aws_ssm_parameter" "al2023_arm" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

resource "aws_iam_role" "box" {
  name = "wiener-box"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "box_ssm" {
  role       = aws_iam_role.box.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "box" {
  role = aws_iam_role.box.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:PutObject"], Resource = "${aws_s3_bucket.raw_archive.arn}/raw/*" },
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.raw_archive.arn}/deploy/*" },
      { Effect = "Allow", Action = ["ssm:GetParameter"], Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter/wiener/*" },
      { Effect = "Allow", Action = ["sns:Publish"], Resource = aws_sns_topic.alerts.arn },
    ]
  })
}

resource "aws_iam_instance_profile" "box" {
  name = "wiener-box"
  role = aws_iam_role.box.name
}

# No inbound rules: access only through SSM.
resource "aws_security_group" "box" {
  name = "wiener-box"
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "box" {
  ami                    = data.aws_ssm_parameter.al2023_arm.value
  instance_type          = "t4g.small"
  iam_instance_profile   = aws_iam_instance_profile.box.name
  vpc_security_group_ids = [aws_security_group.box.id]
  user_data              = file("${path.module}/user_data.sh")
  metadata_options { http_tokens = "required" }
  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
    tags        = { Name = "wiener-box", snapshot = "daily" }
  }
  tags = { Name = "wiener-box" }
  lifecycle { ignore_changes = [ami, user_data] }
}

# ---------- Daily EBS snapshots, keep 7 ----------
resource "aws_iam_role" "dlm" {
  name = "wiener-dlm"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "dlm.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "dlm" {
  role       = aws_iam_role.dlm.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
}

resource "aws_dlm_lifecycle_policy" "box" {
  description        = "wiener box daily snapshots"
  execution_role_arn = aws_iam_role.dlm.arn
  state              = "ENABLED"
  policy_details {
    resource_types = ["VOLUME"]
    target_tags    = { snapshot = "daily" }
    schedule {
      name = "daily-7"
      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["05:00"]
      }
      retain_rule { count = 7 }
      copy_tags = true
    }
  }
}

output "raw_archive_bucket" { value = aws_s3_bucket.raw_archive.bucket }
output "instance_id" { value = aws_instance.box.id }
output "alert_topic_arn" { value = aws_sns_topic.alerts.arn }
