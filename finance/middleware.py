import time
from django.conf import settings
from django.shortcuts import redirect

EXEMPT = ['/setup/', '/unlock/', '/static/', '/media/', '/admin/']

class PinAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        # Always allow the PIN login page itself and exempt paths
        if path == '/' or any(path.startswith(e) for e in EXEMPT):
            return self.get_response(request)

        auth = request.session.get(settings.PIN_SESSION_KEY, False)
        ts   = request.session.get('pin_auth_time', 0)

        if auth and (time.time() - ts) < settings.PIN_SESSION_TIMEOUT:
            request.session['pin_auth_time'] = time.time()
            return self.get_response(request)

        if auth:  # expired
            request.session[settings.PIN_SESSION_KEY] = False
            request.session['session_expired'] = True
        return redirect('pin_login')
