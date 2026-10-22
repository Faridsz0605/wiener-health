# ---------- Lambda: S3 raw/ ObjectCreated -> UC landing Volume ----------
variable "landing_volume" {
  type    = string
  default = "/Volumes/workspace/wiener/landing"
}

data "archive_file" "to_volume" {
  type        = "zip"
  source_file = "${path.module}/../lambda_src/to_volume.py"
  output_path = "${path.module}/.build/to_volume.zip"
}

resource "aws_iam_role" "to_volume" {
  name = "wiener-to-volume"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "to_volume_logs" {
  role       = aws_iam_role.to_volume.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "to_volume" {
  role = aws_iam_role.to_volume.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.raw_archive.arn}/raw/*" },
      { Effect = "Allow", Action = ["ssm:GetParameter"], Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter/wiener/env" },
    ]
  })
}

resource "aws_lambda_function" "to_volume" {
  function_name    = "wiener-to-volume"
  role             = aws_iam_role.to_volume.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "to_volume.handler"
  filename         = data.archive_file.to_volume.output_path
  source_code_hash = data.archive_file.to_volume.output_base64sha256
  timeout          = 120
  memory_size      = 256
  environment { variables = { LANDING_VOLUME = var.landing_volume } }
}

resource "aws_lambda_permission" "s3" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.to_volume.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw_archive.arn
}

resource "aws_s3_bucket_notification" "raw" {
  bucket = aws_s3_bucket.raw_archive.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.to_volume.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
  }
  depends_on = [aws_lambda_permission.s3]
}

resource "aws_cloudwatch_metric_alarm" "to_volume_errors" {
  alarm_name          = "wiener-to-volume-errors"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.to_volume.function_name }
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
