"""
Simple serializer helpers — no Django models, just plain dicts.
Validation logic for incoming request data.
"""
from typing import Optional


VALID_STATUSES = {'NEEDS-ACTION', 'IN-PROCESS', 'COMPLETED', 'CANCELLED'}
PRIORITY_MAP = {'high': 1, 'medium': 5, 'low': 9, 'none': 0}


def validate_task_input(data: dict) -> tuple[dict, list[str]]:
    """
    Validate and normalize task input data.
    Returns (cleaned_data, errors).
    """
    errors = []
    cleaned = {}

    # title
    title = data.get('title', '').strip()
    if not title:
        errors.append('title is required')
    else:
        cleaned['title'] = title

    # description (optional)
    if 'description' in data:
        cleaned['description'] = str(data['description'])

    # status
    status = str(data.get('status', 'NEEDS-ACTION')).upper()
    if status not in VALID_STATUSES:
        errors.append(f'status must be one of {VALID_STATUSES}')
    else:
        cleaned['status'] = status

    # priority — accept int 0-9 or string name
    raw_priority = data.get('priority', 0)
    if isinstance(raw_priority, str):
        raw_priority = PRIORITY_MAP.get(raw_priority.lower(), 0)
    try:
        priority = int(raw_priority)
        if not 0 <= priority <= 9:
            raise ValueError
        cleaned['priority'] = priority
    except (ValueError, TypeError):
        errors.append('priority must be 0-9 or one of: high, medium, low, none')

    # dates
    for field in ('due', 'start', 'completed_at'):
        if field in data and data[field]:
            cleaned[field] = str(data[field])

    # tags — list of strings
    if 'tags' in data:
        tags = data['tags']
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        cleaned['tags'] = [str(t) for t in tags]

    # location
    if 'location' in data:
        cleaned['location'] = str(data['location'])

    # parent_uid
    if 'parent_uid' in data:
        cleaned['parent_uid'] = str(data['parent_uid']) if data['parent_uid'] else None

    # recurrence — requires a due date
    if 'recurrence' in data:
        cleaned['recurrence'] = str(data['recurrence']) if data['recurrence'] else None
    if cleaned.get('recurrence') and not (cleaned.get('due') or data.get('due')):
        errors.append('recurring tasks must have a due date')

    # starred
    if 'starred' in data:
        cleaned['starred'] = bool(data['starred'])

    # percent
    if 'percent' in data:
        try:
            pct = int(data['percent'])
            cleaned['percent'] = max(0, min(100, pct))
        except (ValueError, TypeError):
            pass

    return cleaned, errors
