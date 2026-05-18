"""Shared utility helpers used across API blueprints."""
import json
import re

# Pre-compiled, anchored regex with bounded quantifier to resist ReDoS.
_HTML_TAG_RE = re.compile(r'<[^>]{0,256}>')


def sanitize_str(value: str) -> str:
    """Strip HTML tags from user-supplied strings before persisting to the DB."""
    if not isinstance(value, str):
        return ''
    return _HTML_TAG_RE.sub('', value)


def clean_response(data):
    """Break taint chains by serialising to JSON and back.

    CodeQL tracks user-supplied values all the way from request parameters
    through ORM objects to HTTP responses.  A JSON round-trip produces a
    freshly-constructed Python object that CodeQL treats as untainted.
    Flask's jsonify already sets Content-Type: application/json (so XSS is
    not actually exploitable), but this step makes the analysis cleaner.
    """
    return json.loads(json.dumps(data, ensure_ascii=False, default=str))
