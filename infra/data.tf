data "aws_caller_identity" "nc_plus_one_caller_identity" {}

output "account_id" {
  value = data.aws_caller_identity.nc_plus_one_caller_identity.account_id
}
