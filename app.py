import asyncio
from dataclasses import asdict
import json
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
from pydantic import BaseModel
import uvicorn

from iodd.iodd import IODD
from sqlite_extension import register_list_types
from dashboard.src.data_models import ConnectedPorts, Reading

register_list_types()

async def reading():
    global cur
    cur.execute("SELECT readings FROM port2")
    row = cur.fetchone()[0]
    return Reading(values=list(row))

async def check_ports():
    global con
    global cur
    cur.execute("SELECT * FROM connections")
    rows = cur.fetchall()
    connected_ports = ConnectedPorts(numbers=[row[0] for row in rows], names=[row[-1] for row in rows])
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
templates.env.globals.update(zip=zip)

con = sqlite3.connect("dashboard.db", detect_types=sqlite3.PARSE_DECLTYPES)
cur = con.cursor()

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


@app.get("/opcua/port_connectivity", response_model=ConnectedPorts)
async def port_connectivity(request: Request):
    return await check_ports()

@app.get("/opcua/reading", response_model=Reading)
async def reading_request(request: Request):
    return await reading()

class Line(BaseModel):
    x: list[list[float]]
    y: list[list[float]]

import math

x = [i for i in range(100)]
y = [math.sin(i/50) for i in x]

@app.get("/random", response_model=Line)
async def randomvals(request: Request):
    global x, y
    x.append(x[-1] + 1)
    x.pop(0)
    y.append(math.sin(x[-1]/50))
    y.pop(0)
    return Line(x=[x, x], y=[y, [-i for i in y]])


async def main():
    uvicorn.run("app:app", port=80, host="0.0.0.0", reload=True)

if __name__ == "__main__":
    asyncio.run(main())