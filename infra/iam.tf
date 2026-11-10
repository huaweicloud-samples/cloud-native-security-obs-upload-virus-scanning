resource "huaweicloud_identity_agency" "functiongraph" {
  name                   = "${local.name_prefix}-fgs-agency"
  description            = "Allows the content check function to read and manage objects in the bucket"
  delegated_service_name = "op_svc_cff"

  domain_roles = [
    "OBS OperateAccess",
  ]
}
