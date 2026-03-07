import json
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes


@require_http_methods(['POST'])
def login(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown')).split(',')[0].strip()
    cache_key = f'login_fails_{ip}'
    fails = cache.get(cache_key, 0)

    if fails >= MAX_ATTEMPTS:
        return JsonResponse({'error': 'Too many attempts. Try again in 5 minutes.'}, status=429)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if data.get('password') == settings.APP_PASSWORD:
        cache.delete(cache_key)
        request.session['authenticated'] = True
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        return JsonResponse({'ok': True})

    cache.set(cache_key, fails + 1, timeout=LOCKOUT_SECONDS)
    return JsonResponse({'error': 'Incorrect password'}, status=401)


@require_http_methods(['POST'])
def logout(request):
    request.session.flush()
    return JsonResponse({'ok': True})


def check(request):
    return JsonResponse({'authenticated': bool(request.session.get('authenticated'))})
