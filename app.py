from dataclasses import asdict
import json
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from iodd.iodd import IODD

from asyncua import Client

class Pitem(BaseModel):
    value: int


async def check_ports():
    connected_ports = [{"port": i, "name": None} for i in range(8)]
    async with Client(url="opc.tcp://192.168.1.250:4840") as client:
        for i in range(8):
            node = client.get_node(f"ns=1;s=IOLM/Port {i+1}/Attached Device/Product Name")
            try:
                name = await node.read_value()
                connected_ports[i]["name"] = name
            except Exception:
                connected_ports[i]["name"] = "N/A"

    return connected_ports


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
    connected_ports = await check_ports()
    return templates.TemplateResponse("home.html", {"request": request, "ports": connected_ports})


@app.get("/monitor", response_class=HTMLResponse)
async def monitor(request: Request):
    """Return monitoring page."""
    connected_ports = await check_ports()
    return templates.TemplateResponse("monitor.html", {"request": request, "ports": connected_ports})


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

val = -1

@app.get("/value", response_model=Pitem)
async def value(request: Request):
    global val
    val += 1
    return Pitem(value=val)


if __name__ == "__main__":
    uvicorn.run("app:app", port=80, host="0.0.0.0", reload=True)
