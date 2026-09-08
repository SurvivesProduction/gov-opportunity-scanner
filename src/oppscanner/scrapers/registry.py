"""Generic fetcher registry: maps a `source_slug` to the concrete
`BaseOpportunityFetcher` subclass that knows how to fetch it.

This is the mechanism that makes adding a new jurisdiction "write one new
fetcher module," not "touch shared code": a real fetcher module (living
downstream, e.g. `oppscanner_full.scrapers.<something>`) decorates its
class with `@register_fetcher("some_source_slug")` at import time, and
anything holding a `source_slug` string (e.g. a row from the `sources`
table) can resolve it to a runnable fetcher via `get_fetcher_class`
without ever importing that module by name.

This module knows nothing about any real slug -- it ships in the public,
client-agnostic package.
"""
from __future__ import annotations

from oppscanner.scrapers.base import BaseOpportunityFetcher

_REGISTRY: dict[str, type[BaseOpportunityFetcher]] = {}


def register_fetcher(source_slug: str):
    """Class decorator: register `cls` as the fetcher for `source_slug`.

    Raises `ValueError` on a conflicting duplicate slug rather than
    silently overwriting the earlier registration -- two fetcher modules
    accidentally claiming the same slug is a bug worth surfacing loudly,
    not a last-import-wins ambiguity. Re-decorating the same class under
    the same slug (e.g. a module reimported) is not treated as a
    conflict.
    """

    def decorator(cls: type[BaseOpportunityFetcher]) -> type[BaseOpportunityFetcher]:
        existing = _REGISTRY.get(source_slug)
        if existing is not None and existing is not cls:
            raise ValueError(
                f"source_slug {source_slug!r} is already registered to "
                f"{existing.__qualname__!r}; cannot also register "
                f"{cls.__qualname__!r}."
            )
        _REGISTRY[source_slug] = cls
        return cls

    return decorator


def get_fetcher_class(source_slug: str) -> type[BaseOpportunityFetcher]:
    """Look up the fetcher class registered for `source_slug`.

    Raises `KeyError` if nothing is registered -- e.g. a `sources` row
    exists (active=true) but no fetcher module for it has been written
    or imported yet.
    """
    try:
        return _REGISTRY[source_slug]
    except KeyError:
        raise KeyError(
            f"No fetcher registered for source_slug {source_slug!r}. "
            "Make sure the module defining it (decorated with "
            "@register_fetcher(...)) has been imported."
        ) from None


def registered_source_slugs() -> list[str]:
    """Every `source_slug` currently registered, for diagnostics/tests."""
    return sorted(_REGISTRY)


def _clear_registry_for_tests() -> None:
    """Reset the registry. Test-only -- real code should never call this."""
    _REGISTRY.clear()
