from dataclasses import asdict
import json
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from iodd.iodd import IODD


app = FastAPI()

app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
app.mount("/img", StaticFiles(directory="dashboard/img"), name="img")
app.mount(
    "/node_modules",
    StaticFiles(directory="dashboard/node_modules"),
    name="node_modules",
)
app.mount(
    "/ioddcollection", StaticFiles(directory="iodd/collection"), name="ioddcollection"
)

templates = Jinja2Templates(directory="dashboard/templates")


@app.get("/", response_class=RedirectResponse)
async def index(request: Request):
    """Redirect to homepage."""
    return RedirectResponse(url="/home")


@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    """Return homepage."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/monitor", response_class=HTMLResponse)
async def monitor(request: Request):
    """Return monitoring page."""
    connections = [
        {"port": 1, "name": "ABC123"},
        {"port": 2, "name": "ABC123"},
        {"port": 3, "name": "ABC123"},
        {"port": 4, "name": "ABC123"},
        {"port": 5, "name": "ABC123"},
        {"port": 6, "name": "ABC123"},
        {"port": 7, "name": "none"},
        {"port": 8, "name": "ABC123"},
    ]
    return templates.TemplateResponse("monitor.html", {"request": request, "connections": connections})


@app.get("/collection", response_class=HTMLResponse)
async def collection(request: Request):
    """Return IODD collection page."""
    with open(
        os.path.join(os.getcwd(), "iodd", "collection", "iodd_collection_index.json"),
        "r",
    ) as f:
        data = json.loads(f.read())
    iodds = []
    for _, entry in enumerate(data):
        iodds.append(IODD(entry["file"]))
    return templates.TemplateResponse(
        "collection.html",
        {"request": request, "iodds": [asdict(iodd) for iodd in iodds]},
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    """Return settings page."""
    return templates.TemplateResponse("settings.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run("app:app", port=80, host="0.0.0.0", reload=True)
