"""Routers package.

M2 adds ``app.routers.integrations`` (health) and reuses
``app.integrations.eval_push`` (CI push). These are wired into ``app/main.py``
by the gateway layer; see ``app/integrations/__init__.py`` for the guarded
include snippet.
"""
