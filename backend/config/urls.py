from django.urls import path, include, re_path
from django.http import FileResponse
from pathlib import Path

_SPA_INDEX = Path(__file__).parent.parent / 'spa' / 'index.html'


def spa(request):
    return FileResponse(open(_SPA_INDEX, 'rb'), content_type='text/html')


urlpatterns = [
    path('api/', include('tasks.urls')),
    re_path(r'.*', spa),
]
