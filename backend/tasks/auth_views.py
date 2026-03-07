import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(['POST'])
def login(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if data.get('password') == settings.APP_PASSWORD:
        request.session['authenticated'] = True
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Incorrect password'}, status=401)


@require_http_methods(['POST'])
def logout(request):
    request.session.flush()
    return JsonResponse({'ok': True})


def check(request):
    return JsonResponse({'authenticated': bool(request.session.get('authenticated'))})
