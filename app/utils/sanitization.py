import bleach


ALLOWED_TAGS = [
    "b",
    "i",
    "em",
    "strong",
    "a",
]

# Define allowed attributes (e.g., 'href' for 'a' tags)
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
}


def sanitize_comment(v: str) -> str:
    """
    Sanitizes the comment field by cleaning untrusted HTML.
    """
    if not v:
        return v
    
    # bleach.clean() is the core function.
    # - 'tags' specifies which tags to keep.
    # - 'attributes' specifies which attributes to keep for which tags.
    # - 'strip=True' removes disallowed tags (e.g., <script>) entirely.
    #   The default (False) would escape them as text (e.g., "&lt;script&gt;").
    
    cleaned_value = bleach.clean(
        v,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True  # Strips disallowed tags instead of escaping them
    )
    return cleaned_value