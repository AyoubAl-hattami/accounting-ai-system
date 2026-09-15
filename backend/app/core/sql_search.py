"""Escaping for user-supplied SQL LIKE / ILIKE search terms.

`%` and `_` are wildcards inside a LIKE pattern.  Interpolating a search term
straight into one lets the term choose how wide the search is: measured against
the platform subscriptions search, a search for a single `%` returned all 4,181
companies in the database rather than the companies whose name contains a
percent sign.

Escaping the term is only half of it.  The comparison has to be told which
character does the escaping, or the backslashes are matched literally instead --
so every call site pairs this with ``escape=LIKE_ESCAPE``:

    column.ilike(escaped_search_pattern(term), escape=LIKE_ESCAPE)
"""

# The escape character declared to the database. A LIKE with escaped input but
# no escape= clause is not safer than no escaping at all; it just fails
# differently.
LIKE_ESCAPE = "\\"


def escaped_search_pattern(search: str) -> str:
    """A contains-pattern whose only wildcards are the two this function adds.

    The backslash is replaced first, otherwise the backslashes introduced for
    `%` and `_` would themselves be escaped a second time.
    """
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
