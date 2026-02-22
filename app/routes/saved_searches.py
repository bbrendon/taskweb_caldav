from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from app import saved_searches as saved_searches_lib
from app.templates_env import templates

router = APIRouter()


@router.post("/saved-searches", response_class=HTMLResponse)
async def create_saved_search(
    request: Request,
    name: str = Form(...),
    query: str = Form(...),
):
    saved_searches_lib.save(name.strip(), query.strip())
    searches = saved_searches_lib.load()
    return templates.TemplateResponse("partials/saved_searches.html", {
        "request": request,
        "saved_searches": searches,
    })


@router.delete("/saved-searches/{id}", response_class=HTMLResponse)
async def delete_saved_search(id: str, request: Request):
    saved_searches_lib.delete(id)
    searches = saved_searches_lib.load()
    return templates.TemplateResponse("partials/saved_searches.html", {
        "request": request,
        "saved_searches": searches,
    })
