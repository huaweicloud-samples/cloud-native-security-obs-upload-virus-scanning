# Contributing

This practice ships Terraform configuration, a Python function, a packaging
script and an offline test suite. Keep changes small and run the checks below
before opening a pull request.

## Local checks

```bash
cd infra
terraform fmt -check
terraform init -backend=false -input=false
terraform validate
cd ..

bash scripts/package-function.sh
python scripts/local-e2e/test_e2e.py
```

## Guidelines

- The deployment archive contains project-owned Python modules only. Do not
  bundle third-party packages or platform-specific native extensions.
- Keep the content checks pluggable. The built-in rule is a demonstrative
  signature check, not a malware engine; document any new rule accordingly.
- Never place access keys, tokens, project identifiers or state files in the
  repository. Use placeholders in examples.
- Public documentation describes what this practice actually does. Avoid
  claiming capabilities the code does not implement.
- Both README variants share the same chapter structure. Keep the ASCII
  architecture diagrams in `README.md`, `README.cn.md` and
  `docs/architecture.md` identical.
