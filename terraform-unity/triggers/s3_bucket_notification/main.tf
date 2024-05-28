resource "aws_sns_topic_policy" "isl_event_topic_policy" {
  arn = var.initiator_topic_arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "s3.amazonaws.com"
      }
      Action   = "SNS:Publish"
      Resource = var.initiator_topic_arn
      Condition = {
        ArnLike = {
          "aws:SourceArn" : "arn:aws:s3:*:*:${var.isl_bucket}"
        }
      }
    }]
  })
}

resource "aws_s3_bucket_notification" "isl_bucket_notification" {
  bucket = var.isl_bucket
  topic {
    topic_arn     = var.initiator_topic_arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = var.isl_bucket_prefix
  }
  depends_on = [
    aws_sns_topic_policy.isl_event_topic_policy,
  ]
}
