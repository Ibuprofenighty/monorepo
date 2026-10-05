"""Cross-module collaboration tests (blueprint 10 §2).

With a single module this asserts the public.py surface is importable and
stable — the seam other modules will use.
"""

from project_backend.modules.catalog import public


def test_public_surface_is_stable():
    for name in (
        "create_resource",
        "purge_expired_idempotency",
        "delete_resource",
        "get_resource",
        "list_resources",
        "CreateResourceCommand",
        "DeleteResourceCommand",
    ):
        assert hasattr(public, name), f"public.py lost {name}"
