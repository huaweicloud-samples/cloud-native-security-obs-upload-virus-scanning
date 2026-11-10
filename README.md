# cloud-native-security-obs-upload-virus-scanning

> [中文](README.cn.md)

[![License](https://img.shields.io/badge/License-MIT%20No%20Attribution-blue.svg)](LICENSE)
[![Huawei Cloud](https://img.shields.io/badge/Huawei%20Cloud-FunctionGraph-red.svg)](https://support.huaweicloud.com/intl/en-us/)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](#)

> An event-driven content check practice on Huawei Cloud

---

## 1. Overview

An event-driven content check practice on Huawei Cloud: an object written to a
private OBS bucket triggers a FunctionGraph function through CTS key operation
notifications and an SMN topic. The function reads the object, runs registered
inspection rules, then writes a status back to the object or removes it.

**Scope of the built-in check.** The bundled `demo-signature` rule matches a
standard, non-executable test signature so the matched / unmatched branches can
be exercised locally. It is **not** a malware detection engine and does not
maintain signature databases. For production use, register an enterprise
content inspection service via `register_rule()` and disable the demo rule.

## 2. Table of Contents

| # | Chapter |
|---|---|
| 1 | [Overview](#1-overview) |
| 2 | [Table of Contents](#2-table-of-contents) |
| 3 | [Architecture](#3-architecture) |
| 4 | [Highlights](#4-highlights) |
| 5 | [Cloud Services Used](#5-cloud-services-used) |
| 6 | [Prerequisites](#6-prerequisites) |
| 7 | [Quick Start](#7-quick-start) |
| 8 | [Step-by-Step Deployment](#8-step-by-step-deployment) |
| 9 | [Usage / Verification](#9-usage--verification) |
| 10 | [Cleanup](#10-cleanup) |
| 11 | [Detailed Explanation](#11-detailed-explanation) |
| 12 | [Dependencies](#12-dependencies) |
| 13 | [FAQ / Troubleshooting](#13-faq--troubleshooting) |
| 14 | [Contributing](#14-contributing) |
| 15 | [License](#15-license) |
| 16 | [Contact / Maintainers](#16-contact--maintainers) |

## 3. Architecture

Full profile (scheduled review enabled):

```
                        ┌────────────────────┐
                        │   Write / timer    │
                        │  CTS / SMN topic   │
                        └──────────┬─────────┘
                                   │ 1 event or timer fires
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│        FunctionGraph function (Python 3.9 / 512 MB / 60 s)         │
│       index.handler - one function.zip, project modules only       │
└──────────┬───────────────────────┬───────────────────────┬─────────┘
           │                       │                       │
           ▼                       ▼                       ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│    2 Read bytes    │  │   3 Write status   │  │  4 LTS log group   │
│ OBS getObject read │  │ metadata / delete  │  │   JSON log lines   │
└────────────────────┘  └────────────────────┘  └────────────────────┘
```

Lightweight profile (scheduled review disabled, event-driven checks only):

```
                        ┌────────────────────┐
                        │    Object write    │
                        │  CTS / SMN topic   │
                        └──────────┬─────────┘
                                   │ 1 object write fires
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│        FunctionGraph function (Python 3.9 / 512 MB / 60 s)         │
│       index.handler - one function.zip, project modules only       │
└──────────┬───────────────────────┬───────────────────────┬─────────┘
           │                       │                       │
           ▼                       ▼                       ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│    2 Read bytes    │  │   3 Write status   │  │  4 LTS log group   │
│ OBS getObject read │  │ metadata / delete  │  │   JSON log lines   │
└────────────────────┘  └────────────────────┘  └────────────────────┘
```

The two profiles differ only at the initiator. The function, storage,
notification and logging paths are identical. Both diagrams are shared with
`docs/architecture.md`.

## 4. Highlights

- Event-driven: object writes trigger the function without a polling loop.
- Pluggable checks: rules are registered by name and can be replaced without
  changing the handler.
- Two remediation policies: removal or quarantine by object metadata.
- Configurable scope: restrict processing to a key prefix.
- Offline test suite: 34 assertions run without any cloud connection.
- Minimal deployment archive: six project-owned Python modules only.

## 5. Cloud Services Used

| Service | Role |
|---|---|
| Object Storage Service (OBS) | Private bucket for objects and status metadata |
| Cloud Trace Service (CTS) | Key operation notification for object writes |
| Simple Message Notification (SMN) | Topic that carries events and triggers the function |
| FunctionGraph | Python function running the check workflow |
| Identity and Access Management (IAM) | Service agency for temporary credentials |
| Log Tank Service (LTS) | Structured execution logs |

## 6. Prerequisites

- A Huawei Cloud account able to create the services listed above.
- Terraform 1.5 or newer, Python 3.9 or newer, Bash.
- A globally unique bucket name, or leave it empty to derive one.
- Credentials supplied through `HW_ACCESS_KEY` and `HW_SECRET_KEY` environment
  variables. No credential value belongs in a repository file.

## 7. Quick Start

```bash
bash scripts/package-function.sh
cd infra
terraform init -backend=false -input=false
terraform validate
terraform apply
cd ..
python scripts/local-e2e/test_e2e.py
```

## 8. Step-by-Step Deployment

1. Copy the parameter template: `cp infra/terraform.tfvars.example infra/terraform.tfvars`.
2. Set `region` and `obs_bucket_name`; choose `preferred_action` (`delete` or `tag`).
3. Optionally set `content_prefix` to limit which keys are processed.
4. Build the archive with `bash scripts/package-function.sh`.
5. Run `terraform init`, `terraform fmt -check` and `terraform validate` in `infra/`.
6. Run `terraform apply` in `infra/` and record the outputs.
7. Run the offline suite and the cloud verification steps in chapter 9.

See `docs/deployment-guide.md` for the full procedure.

## 9. Usage / Verification

Offline verification:

```bash
python scripts/local-e2e/test_e2e.py
```

Cloud verification:

1. Upload a plain text object and confirm metadata `check-status = clean`.
2. Upload an object containing the standard test signature and confirm the
   configured `delete` or `tag` action.
3. Read the `object-checked` structured log lines in the LTS stream.
4. Upload an object outside `content_prefix` and confirm the `skipped` result.
5. Invoke the function directly with `{"bucket": "...", "key": "..."}` to
   exercise the manual event path.

**Local verification completed; cloud deployment has not been executed in this
delivery.** Chapter 9 describes the procedure; the offline suite is the only
verification actually run here.

## 10. Cleanup

```bash
cd infra
terraform destroy
cd ..
```

The bucket is created with forced deletion, so confirm no objects need to be
retained before destroying the stack.

## 11. Detailed Explanation

| Module | Responsibility |
|---|---|
| `src/functions/src/config.py` | Reads configuration and normalises the remediation policy |
| `src/functions/src/events.py` | Unwraps SMN / direct / manual event envelopes, extracts bucket and key |
| `src/functions/src/inspection.py` | Rule registry and the built-in demonstrative signature check |
| `src/functions/src/storage.py` | Object read, status write, removal and listing through the runtime client |
| `src/functions/src/observability.py` | Structured JSON log lines |
| `src/functions/src/index.py` | Handler and the check / remediation state machine |

Event envelopes: topic delivery uses `record[0].smn.message` (a JSON string),
direct delivery uses the `cts` object, and manual calls pass `bucket` / `key`
at the top level. Non-write operations are skipped to avoid recursive
triggering. Object status is stored in metadata keys `check-status` and
`check-findings`.

## 12. Dependencies

- Terraform provider `huaweicloud/huaweicloud >= 1.97.0`.
- Python standard library only. The runtime supplies the object storage
  client, so no third-party package is bundled into `function.zip`.
- `scripts/local-e2e/test_e2e.py` uses `unittest` from the standard library.

## 13. FAQ / Troubleshooting

| Question | Answer |
|---|---|
| Is this a malware detection engine? | No. The built-in rule is a demonstrative signature check. Register an enterprise inspection service for production. |
| Why is no third-party library in the archive? | The runtime provides the object storage client; bundling native extensions into a deployment archive is fragile. |
| Object writes do not trigger the function? | Check the key operation notification status and the topic's allowed publishing services. |
| The function cannot read objects? | Verify the service agency and its bucket permissions. |
| Logs are empty? | Check the `log_group_id` / `log_stream_id` outputs and the LTS stream. |
| Can I disable the scheduled review? | Set `enable_timer = false` and apply again. |

## 14. Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run the offline checks before opening
a pull request, and keep both README variants and `docs/architecture.md`
diagrams identical.

## 15. License

MIT No Attribution. See [LICENSE](LICENSE).

## 16. Contact / Maintainers

| Item | Content |
|---|---|
| **Creator** | [@<github-username>](https://github.com/<github-username>) |
| **Maintainer** | [@<github-username>](https://github.com/<github-username>) |
| **Contact** | GitHub Issues / PR (see [Section 14](#14-contributing)) |
