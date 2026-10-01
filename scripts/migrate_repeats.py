"""
One-time migration: old-style repeats -> "repeat after done".

The previous app stored "every N days after completion" as a plain RRULE. TaskWeb
stores it as X-TASKWEB-RECUR-AFTER so iPhone Reminders doesn't treat it as a fixed
schedule. This converts OPEN tasks whose RRULE is a simple "every N units".

Completed tasks are never touched: they are old finished copies, and converting
them would make TaskWeb roll them forward and reopen them.

    python scripts/migrate_repeats.py            # preview only, writes nothing
    python scripts/migrate_repeats.py --apply    # fresh backup, then convert

Add --date-only to also turn timed due/start values into all-day dates on the same
local day (the old app left completion-time clock values like 1:40:28pm on them).
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from backup_calendar import load_env, main as backup  # noqa: E402
from task_caldav_lib import CalDAVService, legacy_rrule_to_interval  # noqa: E402

UNIT = {'D': 'day', 'W': 'week', 'M': 'month', 'Y': 'year'}


def describe(interval: str) -> str:
    n, unit = int(interval[1:-1]), UNIT[interval[-1]]
    return f'{n} {unit}{"" if n == 1 else "s"} after done'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='write the changes (after a fresh backup)')
    ap.add_argument('--date-only', action='store_true', help='make due/start all-day dates')
    args = ap.parse_args()

    load_env(ROOT / '.env')
    svc = CalDAVService(
        os.environ['CALDAV_URL'], os.environ['CALDAV_USERNAME'], os.environ['CALDAV_PASSWORD'],
        os.environ.get('CALDAV_CALENDAR', 'Tasks'), tz='America/Los_Angeles',
    )
    svc.refresh()

    convert, keep = [], []
    for t in sorted(svc.tasks(), key=lambda t: t.title.lower()):
        if not t.rrule or t.recur_after or not t.is_open:
            continue
        interval = legacy_rrule_to_interval(t.rrule)
        (convert if interval else keep).append((t, interval))

    def patch_for(t, iv):
        patch = {'recur_after': iv, 'rrule': None}
        if args.date_only:
            for field in ('due', 'start'):
                v = getattr(t, field)
                if v and len(v) > 10:
                    patch[field] = v[:10]  # API values are already in local time
        return patch

    print(f'Convert to "after done" ({len(convert)}):')
    for t, iv in convert:
        p = patch_for(t, iv)
        due = f"{t.due} -> {p['due']}" if 'due' in p else (t.due or 'none')
        print(f'  {t.title[:44]:44}  {describe(iv):22} due {due}{"  (start too)" if "start" in p else ""}')
    print(f'\nKeep as fixed schedule ({len(keep)}):')
    for t, _ in keep:
        print(f'  {t.title[:48]:48}  {t.rrule}')
    done_with_rrule = sum(1 for t in svc.tasks() if t.rrule and not t.is_open)
    print(f'\nUntouched: {done_with_rrule} completed tasks that still carry an old repeat rule.')

    if not args.apply:
        print('\nPreview only. Nothing was written. Run with --apply to convert.')
        return 0

    print('\nTaking a fresh backup first...')
    if backup() != 0:
        print('Backup failed; not applying.', file=sys.stderr)
        return 1
    failed = 0
    for t, iv in convert:
        try:
            svc.update(t.uid, patch_for(t, iv))
            print(f'  converted: {t.title}')
        except Exception as e:  # keep going; report at the end
            failed += 1
            print(f'  FAILED: {t.title}: {e}', file=sys.stderr)
    print(f'\nDone. {len(convert) - failed} converted, {failed} failed.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
