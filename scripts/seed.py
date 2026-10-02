from __future__ import annotations

"""Bootstrap RBAC, super admin, and demo tenant/users."""

from scripts.seed_demo import seed_demo


def seed() -> None:
    seed_demo()


if __name__ == "__main__":
    seed()
