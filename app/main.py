from datetime import date
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response

from app.config import settings
from app.templates_env import templates
from app.routes import tasks, search, auth, saved_searches, locations

app = FastAPI(title="TaskWeb CalDAV")

# Static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_PUBLIC = {"/login", "/logout"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Refresh today global for templates on every request
        templates.env.globals["today"] = date.today()

        path = request.url.path

        # Always allow public paths and static assets through
        if path in _PUBLIC or path.startswith("/static"):
            return await call_next(request)

        # Option C: static token via ?token= query param or X-Auth-Token header.
        # A valid token also promotes the browser to a session so the token isn't
        # required on every subsequent request.
        token = request.query_params.get("token") or request.headers.get("X-Auth-Token", "")
        if token and settings.AUTH_TOKEN and token == settings.AUTH_TOKEN:
            request.session["authenticated"] = True

        # Option B: session cookie set by the login form
        if request.session.get("authenticated"):
            return await call_next(request)

        # Not authenticated — redirect to /login.
        # For HTMX requests use HX-Redirect so the full page is replaced rather
        # than only the swap target.
        if request.headers.get("HX-Request"):
            resp = Response(status_code=204)
            resp.headers["HX-Redirect"] = "/login"
            return resp
        return RedirectResponse(f"/login?next={request.url.path}", status_code=302)


# Middleware is applied innermost-first via add_middleware (LIFO), so
# SessionMiddleware must be added LAST so it runs outermost (first on the
# request path) and populates request.session before AuthMiddleware sees it.
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

# Include routers
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(search.router)
app.include_router(saved_searches.router)
app.include_router(locations.router)
