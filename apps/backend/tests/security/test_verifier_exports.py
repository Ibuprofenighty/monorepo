"""Every identity adapter exports the same surface."""

from __future__ import annotations

import project_backend.platform.authn.verifiers.keycloak as keycloak
import project_backend.platform.authn.verifiers.local as local
import project_backend.platform.authn.verifiers.wechat as wechat
from project_backend.platform.authn.protocol import REQUIRED_EXPORTS


def test_each_verifier_exports_the_contract() -> None:
    for module in (local, wechat, keycloak):
        missing = [name for name in REQUIRED_EXPORTS if not hasattr(module, name)]
        assert missing == []
