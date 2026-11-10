locals {
  function_zip = "${path.module}/../build/function.zip"

  # A missing package produces a clear runtime error instead of an opaque
  # "Invalid function argument" during plan.
  function_code = (
    fileexists(local.function_zip)
    ? filebase64(local.function_zip)
    : base64encode("raise RuntimeError('Missing deployment package: build/function.zip. Run scripts/package-function.sh first.')")
  )

  # FunctionGraph rejects environment variables whose value is an empty string.
  env_without_empty = {
    for k, v in {
      REGION           = var.region
      OBS_BUCKET       = huaweicloud_obs_bucket.objects.bucket
      OBS_ENDPOINT     = "https://obs.${var.region}.myhuaweicloud.com"
      PREFERRED_ACTION = var.preferred_action
      CONTENT_PREFIX   = var.content_prefix
      SERVICE_NAME     = var.service_name
      LOG_LEVEL        = var.log_level
      LTS_GROUP_ID     = huaweicloud_lts_group.app.id
      LTS_STREAM_ID    = huaweicloud_lts_stream.app.id
    } : k => v if v != null && v != ""
  }
}

# The deployment archive contains only project-owned Python modules.
# The runtime supplies the object storage client, so no third-party
# libraries are bundled and no native extensions enter the archive.
resource "huaweicloud_fgs_function" "checker" {
  name        = "${local.name_prefix}-checker"
  app         = "default"
  agency      = huaweicloud_identity_agency.functiongraph.name
  handler     = "index.handler"
  runtime     = var.function_runtime
  memory_size = var.function_memory_size
  timeout     = var.function_timeout

  code_type     = "zip"
  code_filename = "function.zip"
  func_code     = local.function_code

  enable_lts_log = true
  log_group_id   = huaweicloud_lts_group.app.id
  log_stream_id  = huaweicloud_lts_stream.app.id

  user_data = jsonencode(local.env_without_empty)

  # Agency propagation is asynchronous; creating the function too early
  # fails with FSS.1501 The delegate not exist.
  depends_on = [huaweicloud_identity_agency.functiongraph]
}
