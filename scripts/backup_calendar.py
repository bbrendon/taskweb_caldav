"""
Read-only backup + inventory of the CalDAV task calendar.

Writes every resource as-is to backups/<timestamp>/ (one .ics per task, plus all.ics)
and prints an inventory of property names, so we know what existing data contains
without printing task contents. Never writes to the server.

    python scripts/backup_calendar.py            # uses .env
"""
import collections
import os
import sys
from datetime import datetime
from pathlib import Path

import caldav
from icalendar import Calendar

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    load_env(ROOT / '.env')
    url, user, pw = os.environ['CALDAV_URL'], os.environ.get('CALDAV_USERNAME'), os.environ.get('CALDAV_PASSWORD')
    name = os.environ.get('CALDAV_CALENDAR', 'Tasks')
    if not user or not pw:
        print('Set CALDAV_USERNAME and CALDAV_PASSWORD in .env first.', file=sys.stderr)
        return 1

    client = caldav.DAVClient(url=url, username=user, password=pw, require_tls=url.startswith('https'))
    cals = {c.get_display_name(): c for c in client.principal().calendars()}
    print('Calendars on server:', ', '.join(f'{n!r}' for n in cals))
    if name not in cals:
        print(f'Calendar {name!r} not found.', file=sys.stderr)
        return 1

    out = ROOT / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S')
    out.mkdir(parents=True)
    os.chmod(out, 0o700)

    props = collections.Counter()
    alarm_props = collections.Counter()
    rrules = collections.Counter()
    value_types = collections.Counter()
    statuses = collections.Counter()
    merged = Calendar()
    merged.add('PRODID', '-//taskweb backup//EN')
    merged.add('VERSION', '2.0')
    n = 0
    for obj in cals[name].objects_by_sync_token(load_objects=True):
        if not obj.data:
            continue
        fname = str(obj.url).rstrip('/').rsplit('/', 1)[-1] or f'item-{n}.ics'
        (out / fname).write_text(obj.data)
        cal = Calendar.from_ical(obj.data)
        for comp in cal.subcomponents:
            if comp.name in ('VTODO', 'VTIMEZONE'):
                merged.add_component(comp)
        for todo in cal.walk('VTODO'):
            n += 1
            statuses[str(todo.get('STATUS', '(none)'))] += 1
            for key in todo.keys():
                props[key] += 1
            for key in ('DUE', 'DTSTART'):
                if key in todo:
                    v = todo[key]
                    kind = 'date' if not hasattr(v.dt, 'hour') else ('utc' if v.dt.tzinfo and v.dt.utcoffset().total_seconds() == 0 and 'TZID' not in v.params else ('tzid' if v.params.get('TZID') else 'floating'))
                    value_types[f'{key}:{kind}'] += 1
            if 'RRULE' in todo:
                rrules[todo['RRULE'].to_ical().decode()] += 1
            for alarm in todo.walk('VALARM'):
                for key in alarm.keys():
                    alarm_props[key] += 1
    (out / 'all.ics').write_bytes(merged.to_ical())

    print(f'\nBacked up {n} tasks to {out}')
    print('\nStatuses:', dict(statuses))
    print('\nVTODO properties (count):')
    for k, v in props.most_common():
        print(f'  {k:32} {v}')
    print('\nDUE/DTSTART value kinds:', dict(value_types))
    print('\nAlarm properties:', dict(alarm_props))
    print('\nRepeat rules (rule -> count):')
    for k, v in rrules.most_common():
        print(f'  {k:50} {v}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
