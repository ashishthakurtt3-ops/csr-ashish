import math
from typing import Any, Callable, Dict, List, Optional
from django.db.models import QuerySet


def paginate_queryset(
    queryset: QuerySet,
    serialize_func: Callable[[Any], Dict[str, Any]],
    page: Optional[Any] = None,
    page_size: Optional[Any] = 12,
    fallback_limit: int = 200,
) -> Dict[str, Any] | List[Dict[str, Any]]:
    """
    Unified pagination engine compliant with ImpactBridge API Contract:
    - If page is None or empty: returns flat list of serialized dicts up to fallback_limit.
    - If page is an integer: returns structured pagination envelope {items, total, page, page_size, total_pages, has_next, has_prev}.
    """
    # Guard against non-numeric page values
    if page is not None:
        if isinstance(page, str) and page.lower() in ('none', 'null', ''):
            page = None
        else:
            try:
                page = max(1, int(page))
            except (ValueError, TypeError):
                page = None

    if page_size is not None:
        try:
            page_size = max(1, min(100, int(page_size)))
        except (ValueError, TypeError):
            page_size = 12
    else:
        page_size = 12

    if page is None:
        items = [serialize_func(obj) for obj in queryset[:fallback_limit]]
        return items

    total = queryset.count()
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size
    slice_qs = queryset[offset:offset + page_size]
    items = [serialize_func(obj) for obj in slice_qs]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
