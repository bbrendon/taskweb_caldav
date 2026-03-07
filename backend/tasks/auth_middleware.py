from django.http import JsonResponse

EXEMPT = {'/api/auth/login/', '/api/auth/logout/'}


class RequireAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/') and request.path not in EXEMPT:
            if not request.session.get('authenticated'):
                return JsonResponse({'error': 'Unauthorized'}, status=401)
        return self.get_response(request)
