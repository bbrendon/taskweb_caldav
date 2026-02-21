"""Shared Jinja2Templates instance used by all routes."""
from datetime import date
from pathlib import Path
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.globals["today"] = date.today()
