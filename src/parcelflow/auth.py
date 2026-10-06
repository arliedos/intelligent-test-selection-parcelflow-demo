"""Explicit local demo role-authorization simulation.

This is NOT production authentication/authorization. Roles are supplied by a
plain request header (`X-Demo-Role`) and checked against config-driven allow
lists. There is no session, token, or identity verification here.
"""
from __future__ import annotations

from parcelflow.models import ROLES, AuthorizationError


def is_allowed(role, allowed_roles) -> bool:
    if role is None or role not in ROLES:
        return False
    return role in allowed_roles


def require_role(role, allowed_roles) -> None:
    if role is None:
        raise AuthorizationError("missing role header")
    if role not in ROLES:
        raise AuthorizationError("unknown role")
    if role not in allowed_roles:
        raise AuthorizationError(f"role {role!r} is not permitted to perform this action")
