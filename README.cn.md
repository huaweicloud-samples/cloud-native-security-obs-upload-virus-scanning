# cloud-native-security-obs-upload-virus-scanning

> [English](README.md)

[![License](https://img.shields.io/badge/License-MIT%20No%20Attribution-blue.svg)](LICENSE)
[![Huawei Cloud](https://img.shields.io/badge/Huawei%20Cloud-FunctionGraph-red.svg)](https://support.huaweicloud.com/intl/en-us/)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](#)

> 华为云上的事件驱动内容检查实践

---

## 1. 简介

华为云上的事件驱动内容检查实践：对象写入 OBS 私有桶后，经 CTS 关键操作通知与
SMN 主题触发 FunctionGraph 函数。函数读取对象内容，执行已注册的检查规则，
再写回对象状态或删除对象。

**内置检查规则的边界**：仓库自带的 `demo-signature` 规则匹配一段标准、
不可执行的测试特征串，仅用于本地验证命中与未命中两条分支。它**不是**恶意代码
检测引擎，也不维护特征库。生产环境请通过 `register_rule()` 注册企业内容检测服务，
并停用演示规则。

## 2. 目录

| # | 章节 |
|---|---|
| 1 | [简介](#1-简介) |
| 2 | [目录](#2-目录) |
| 3 | [架构图](#3-架构图) |
| 4 | [方案亮点](#4-方案亮点) |
| 5 | [涉及云服务](#5-涉及云服务) |
| 6 | [前置条件](#6-前置条件) |
| 7 | [快速开始](#7-快速开始) |
| 8 | [分步部署](#8-分步部署) |
| 9 | [使用方法 / 验证](#9-使用方法--验证) |
| 10 | [清理资源](#10-清理资源) |
| 11 | [详细说明](#11-详细说明) |
| 12 | [依赖](#12-依赖) |
| 13 | [FAQ / 故障排除](#13-faq--故障排除) |
| 14 | [贡献指南](#14-贡献指南) |
| 15 | [许可证](#15-许可证) |
| 16 | [联系方式 / 维护者](#16-联系方式--维护者) |

## 3. 架构图

完整档（启用定时复核）：

```
                        ┌────────────────────┐
                        │ 对象写入/定时复核  │
                        │ CTS / SMN 通知链路 │
                        └──────────┬─────────┘
                                   │ ① 事件或定时规则触发
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│          FunctionGraph 函数（Python 3.9 · 512 MB · 60 s）          │
│          index.handler · 单个 function.zip（仅自有模块）           │
└──────────┬───────────────────────┬───────────────────────┬─────────┘
           │                       │                       │
           ▼                       ▼                       ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│   ② 读取对象内容   │  │ ③ 写回状态 / 处置  │  │    ④ LTS 日志组    │
│ OBS getObject 读取 │  │ 对象元数据 / 删除  │  │   结构化 JSON 行   │
└────────────────────┘  └────────────────────┘  └────────────────────┘
```

轻量档（关闭定时复核，仅保留事件驱动检查）：

```
                        ┌────────────────────┐
                        │    对象写入事件    │
                        │ CTS / SMN 通知链路 │
                        └──────────┬─────────┘
                                   │ ① 对象写入事件触发
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│          FunctionGraph 函数（Python 3.9 · 512 MB · 60 s）          │
│          index.handler · 单个 function.zip（仅自有模块）           │
└──────────┬───────────────────────┬───────────────────────┬─────────┘
           │                       │                       │
           ▼                       ▼                       ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│   ② 读取对象内容   │  │ ③ 写回状态 / 处置  │  │    ④ LTS 日志组    │
│ OBS getObject 读取 │  │ 对象元数据 / 删除  │  │   结构化 JSON 行   │
└────────────────────┘  └────────────────────┘  └────────────────────┘
```

两档只在发起端不同：完整档多一个定时触发器用于周期性复核；
函数、存储、通知与日志链路完全一致。两图与 `docs/architecture.md` 同源。

## 4. 方案亮点

- 事件驱动：对象写入即触发函数，无需轮询。
- 规则可插拔：检查规则按名称注册，替换规则无需改动业务入口。
- 两种处置策略：删除对象，或通过对象元数据隔离保留。
- 范围可配置：可用键前缀限定处理范围。
- 离线测试套件：34 项断言，无需任何云端连接。
- 最小部署包：仅含 6 个项目自有 Python 模块。

## 5. 涉及云服务

| 云服务 | 作用 |
|---|---|
| 对象存储服务 OBS | 存放对象与状态元数据的私有桶 |
| 云审计服务 CTS | 对象写入的关键操作通知 |
| 消息通知服务 SMN | 承载事件并触发函数的主题 |
| 函数工作流 FunctionGraph | 运行检查流程的 Python 函数 |
| 统一身份认证 IAM | 为函数提供临时凭据的服务委托 |
| 云日志服务 LTS | 结构化执行日志 |

## 6. 前置条件

- 具备创建上述云服务的华为云账号。
- Terraform 1.5+、Python 3.9+、Bash。
- 一个全局唯一的桶名；留空时由应用名与区域推导。
- 凭据通过 `HW_ACCESS_KEY` / `HW_SECRET_KEY` 环境变量提供，任何仓库文件都不写入凭据值。

## 7. 快速开始

```bash
bash scripts/package-function.sh
cd infra
terraform init -backend=false -input=false
terraform validate
terraform apply
cd ..
python scripts/local-e2e/test_e2e.py
```

## 8. 分步部署

1. 复制参数模板：`cp infra/terraform.tfvars.example infra/terraform.tfvars`。
2. 填写 `region` 与 `obs_bucket_name`，选择 `preferred_action`（`delete` 或 `tag`）。
3. 按需设置 `content_prefix`，限定参与处理的对象键前缀。
4. 执行 `bash scripts/package-function.sh` 生成部署包。
5. 在 `infra/` 下依次执行 `terraform init`、`terraform fmt -check`、`terraform validate`。
6. 在 `infra/` 下执行 `terraform apply` 并记录输出。
7. 执行离线测试与第 9 章的云端验证步骤。

完整步骤见 `docs/deployment-guide.md`。

## 9. 使用方法 / 验证

离线验证：

```bash
python scripts/local-e2e/test_e2e.py
```

云端验证：

1. 上传普通文本对象，确认元数据出现 `check-status = clean`。
2. 上传含标准测试特征串的对象，确认按配置执行删除或写 `quarantined`。
3. 在 LTS 日志流中查看 `object-checked` 结构化记录。
4. 上传位于 `content_prefix` 之外的对象，确认返回 `skipped`。
5. 以 `{"bucket": "...", "key": "..."}` 直接调用函数，验证手动事件入口。

**本地验证已完成；本次交付未执行云端部署。** 第 9 章描述的是验证步骤，
实际运行过的验证只有离线测试套件。

## 10. 清理资源

```bash
cd infra
terraform destroy
cd ..
```

桶设置了强制删除，清理前请确认其中没有需要保留的对象。

## 11. 详细说明

| 模块 | 职责 |
|---|---|
| `src/functions/src/config.py` | 读取配置并归一化处置策略 |
| `src/functions/src/events.py` | 解析 SMN / 直连 / 手动事件信封，提取桶名与对象键 |
| `src/functions/src/inspection.py` | 规则注册表与内置演示特征串规则 |
| `src/functions/src/storage.py` | 通过运行时客户端读取对象、写状态、删除与列举 |
| `src/functions/src/observability.py` | 结构化 JSON 日志行 |
| `src/functions/src/index.py` | 函数入口与检查 / 处置状态机 |

事件信封：主题投递为 `record[0].smn.message`（JSON 字符串），直连投递为 `cts` 对象，
手动调用在顶层传 `bucket` / `key`。非写入类操作会被跳过，避免递归触发。
对象状态写入元数据键 `check-status` 与 `check-findings`。

## 12. 依赖

- Terraform provider `huaweicloud/huaweicloud >= 1.97.0`。
- 仅使用 Python 标准库；运行时提供对象存储客户端，部署包内不含第三方库。
- `scripts/local-e2e/test_e2e.py` 使用标准库 `unittest`。

## 13. FAQ / 故障排除

| 问题 | 解答 |
|---|---|
| 这是恶意代码检测引擎吗？ | 不是。内置规则是演示用特征串检查，生产请注册企业内容检测服务。 |
| 为什么部署包里没有第三方库？ | 运行时已提供对象存储客户端，打包原生扩展容易引发加载失败。 |
| 对象写入没有触发函数？ | 检查关键操作通知状态与主题允许发布的服务配置。 |
| 函数读不到对象？ | 核对服务委托及其桶权限。 |
| 日志为空？ | 核对 `log_group_id` / `log_stream_id` 输出与日志流。 |
| 能否关闭定时复核？ | 设置 `enable_timer = false` 后重新 apply。 |

## 14. 贡献指南

见 [CONTRIBUTING.md](CONTRIBUTING.md)。提交变更前请执行离线检查，
并保持两版 README 与 `docs/architecture.md` 的架构图一致。

## 15. 许可证

MIT No Attribution，见 [LICENSE](LICENSE)。

## 16. 联系方式 / 维护者

| 项 | 内容 |
|---|---|
| **创建者** | [@<github-username>](https://github.com/<github-username>) |
| **维护者** | [@<github-username>](https://github.com/<github-username>) |
| **联系方式** | GitHub Issues / PR（见[第 14 章](#14-贡献指南)） |
