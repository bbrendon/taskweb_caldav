"""Fill the local dev Radicale with sample tasks (never run against the real server)."""
import os
import sys
from datetime import date, timedelta

from task_caldav_lib import CalDAVService

url = os.environ['CALDAV_URL']
if '127.0.0.1' not in url and 'localhost' not in url:
    sys.exit('seed_dev.py only runs against a local Radicale')

svc = CalDAVService(url, 'dev', 'dev', 'Tasks', tz='America/Los_Angeles', create_calendar=True)
svc.refresh()
if svc.tasks():
    print(f'Dev calendar already has {len(svc.tasks())} tasks; not seeding.')
    sys.exit(0)

d = lambda n: (date.today() + timedelta(days=n)).isoformat()  # noqa: E731
home = {'title': 'Home', 'address': '', 'lat': 37.4000, 'lon': -122.1000, 'radius': 150, 'proximity': 'ARRIVE'}
work = {'title': 'Work', 'address': '', 'lat': 37.4100, 'lon': -122.0900, 'radius': 150, 'proximity': 'ARRIVE'}

svc.create({'title': 'Replace props on the 5" quad', 'due': d(-3), 'tags': ['drone'], 'priority': 1, 'starred': True})
svc.create({'title': 'Balance-charge LiPo packs', 'due': d(0), 'tags': ['drone'], 'recur_after': 'P14D'})
svc.create({'title': 'Water the backyard trees', 'due': d(1), 'tags': ['outside'], 'recur_after': 'P4W',
            'location': 'Home', 'location_alarm': home})
svc.create({'title': 'Pay rent', 'due': d(5), 'rrule': 'FREQ=MONTHLY;BYMONTHDAY=1', 'priority': 1})
svc.create({'title': 'Clean gutters', 'due': d(12), 'tags': ['outside'], 'recur_after': 'P6M', 'priority': 5})
svc.create({'title': 'Return library books', 'due': d(-1)})
svc.create({'title': 'Bring laptop charger back', 'location': 'Work', 'location_alarm': {**work, 'proximity': 'DEPART'}})
svc.create({'title': 'Plan coastal flight', 'start': d(10), 'due': d(20), 'tags': ['drone', 'outside']})
svc.create({'title': 'Mow the lawn', 'due': d(2), 'tags': ['outside'], 'recur_after': 'P10D'})
svc.create({'title': 'Renew FAA registration', 'due': d(40), 'tags': ['drone'], 'priority': 9,
            'notes': 'Recreational registration, $5. Have the old certificate number ready.'})
build = svc.create({'title': 'Build the 3" cinewhoop', 'due': d(9), 'tags': ['drone'], 'starred': True})
for title in ['Order frame and motors', 'Solder the ESC stack', 'Flash Betaflight and tune rates']:
    svc.create({'title': title, 'parent_uid': build.uid, 'tags': ['drone']})
svc.complete(svc.create({'title': 'Order frame and motors (old)', 'parent_uid': build.uid}).uid)
for i, title in enumerate(['Trim hedges', 'Fix sprinkler head', 'Update flight controller firmware']):
    svc.complete(svc.create({'title': title, 'due': d(-10 - i)}).uid)
svc.create({'title': 'Call about the fence quote', 'due': d(3) + 'T09:30:00-07:00', 'alarms': [{'at': d(3) + 'T09:00:00-07:00'}]})
print(f'Seeded {len(svc.tasks())} tasks.')
