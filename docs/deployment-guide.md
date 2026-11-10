# 部署指导书

## 1. 部署前准备

- 具备创建 OBS 桶、FunctionGraph 函数、SMN 主题、CTS 通知、IAM 委托与 LTS 日志组的权限。
- 本地安装 Terraform 1.5 或更高版本、Python 3.9 或更高版本、Bash。
- 准备一个全局唯一的桶名；留空时由应用名与区域推导。

凭据通过环境变量提供给 Terraform，不写入任何提交到仓库的文件。

```bash
export HW_ACCESS_KEY="<your-access-key>"
export HW_SECRET_KEY="<your-secret-key>"
```

## 2. 构建函数部署包

```bash
bash scripts/package-function.sh
```

脚本把 `src/functions/src/*.py` 复制进 `build/` 并生成 `build/function.zip`。
部署包只包含项目自有模块，运行时提供对象存储客户端，因此不安装第三方库。

## 3. 填写部署参数

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars
```

按实际环境修改 `region`、`obs_bucket_name`、`preferred_action`、`content_prefix` 等项。
`terraform.tfvars` 已被忽略规则排除，请勿提交。

## 4. 初始化与校验

```bash
cd infra
terraform init -backend=false -input=false
terraform fmt -check
terraform validate
cd ..
```

## 5. 执行部署

```bash
cd infra
terraform apply
cd ..
```

Terraform 会创建私有桶、通知主题、关键操作通知、函数、服务委托、日志组与流，
以及通知触发器和（可选）定时复核触发器。

## 6. 记录输出

```bash
cd infra && terraform output && cd ..
```

重点记录 `bucket_name`、`function_name`、`topic_urn`、`notification_name` 与
`lts_group_id` / `lts_stream_id`，供后续验证使用。

## 7. 功能验证

离线验证不依赖云端资源，建议先执行：

```bash
python scripts/local-e2e/test_e2e.py
```

该套件覆盖配置解析、事件信封、检查规则、状态写入、删除 / 打标分支、
定时复核路径与部署包内容。

云端链路验证步骤：

1. 向桶上传一个普通文本文件，确认对象元数据出现 `check-status = clean`。
2. 上传包含标准测试特征串的文件，确认按配置执行删除或写 `quarantined`。
3. 查看 LTS 日志流中的 `object-checked` 结构化记录。
4. 上传一个位于 `content_prefix` 之外的对象，确认返回 `skipped`。

> 内置检查规则只用于演示与本地验证，不是恶意代码检测引擎；
> 生产使用请按 `docs/architecture.md` 的说明注册企业内容检测服务。

## 8. 轻量验证档

在 `terraform.tfvars` 中设置 `enable_timer = false`，然后重新执行
`terraform apply`。该档不创建定时复核触发器，其余链路保持一致。

## 9. 清理资源

```bash
cd infra
terraform destroy
cd ..
```

桶设置了强制删除，清理前请确认其中不再需要保留的对象。

## 10. 常见失败与处置

| 现象 | 可能原因 | 处置 |
|---|---|---|
| `terraform validate` 报缺少部署包 | 未先运行打包脚本 | 执行 `bash scripts/package-function.sh` 后重试 |
| 函数创建报委托不存在 | IAM 委托传播有延迟 | 配置已声明依赖，稍后重试 `apply` |
| 对象写入未触发函数 | 通知未启用或主题未授权服务发布 | 检查关键操作通知状态与主题的允许发布服务配置 |
| 函数日志为空 | 日志组 / 流未绑定 | 核对 `log_group_id` 与 `log_stream_id` 输出 |
| 解析不到桶名或对象键 | 事件信封字段与预期不同 | 在测试事件中显式传 `bucket` / `key`，并核对 `events.py` 的字段候选 |
| 本地测试报缺少 `build/function.zip` | 未打包 | 先执行打包脚本 |
