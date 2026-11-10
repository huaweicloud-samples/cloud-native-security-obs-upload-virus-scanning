"""Pluggable content checks.

The built-in rule is a demonstrative signature check, not a malware engine.
Production deployments should register an enterprise content inspection
service with register_rule() and keep the built-in rule for local tests only.
"""

# Standard, non-executable test signature used only to exercise the demo rule.
STANDARD_TEST_SIGNATURE = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
).strip()

_RULES = {}


def register_rule(name, fn):
    """Register a callable receiving bytes and returning a detail string or None."""
    _RULES[name] = fn


def builtin_signature_rule(content):
    if STANDARD_TEST_SIGNATURE and STANDARD_TEST_SIGNATURE in content:
        return "demo signature matched"
    return None


register_rule("demo-signature", builtin_signature_rule)


def inspect(content, rules=None):
    """Run every registered rule and return a structured verdict."""
    payload = content if isinstance(content, bytes) else bytes(content or b"")
    active = _RULES if rules is None else rules
    findings = []
    for name, fn in sorted(active.items()):
        detail = fn(payload)
        if detail:
            findings.append({"rule": name, "detail": str(detail)})
    return {
        "clean": not findings,
        "findings": findings,
        "bytes": len(payload),
        "rules": sorted(active.keys()),
    }
