import random
import re
import sys
import threading
import time

from fastapi import FastAPI, templating

from turbo_fastapi import Turbo


def get_linux_load():
    with open("/proc/loadavg", "rt") as f:
        return f.read().split()[:3]


def get_non_linux_load():
    load = [int(random.random() * 100) / 100 for _ in range(3)]
    keys = ["load1", "load5", "load15"]

    return dict(zip(keys, load))


app = FastAPI(__name__)
turbo = Turbo(app)

templates = templating.Jinja2Templates(directory="templates")

if sys.platform.startswith("linux"):
    templates.env.globals["load"] = get_linux_load()
else:
    templates.env.globals.update(get_non_linux_load())


@app.get("/")
def index():
    return templates.TemplateResponse("index.html")


@app.get("/page2")
def page2():
    return templates.TemplateResponse("page2.html")


@app.on_event("startup")
def before_first_request():
    threading.Thread(target=update_load).start()


def update_load():
    while True:
        time.sleep(5)
        turbo.push(
            turbo.replace(templates.TemplateResponse("loadavg.html"), "load")
        )
