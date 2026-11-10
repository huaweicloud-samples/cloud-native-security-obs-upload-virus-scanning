resource "huaweicloud_obs_bucket" "objects" {
  bucket        = local.bucket_name
  acl           = "private"
  force_destroy = true
}
