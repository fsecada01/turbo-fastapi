from fastapi import FastAPI, HTTPException, staticfiles, templating
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from models import Todo
from starlette.routing import Route

from turbo_fastapi import Turbo


def get_todo_by_id(id_str):
    todo = [todo for todo in todos if todo.id == id_str]
    if len(todo) == 0:
        raise HTTPException(status_code=404, detail="todo not found.")
    return todo[0]


def index(request: Request):
    if request.method == "POST":
        todo = Todo(task=request.form.get("task"))
        todos.append(todo)
        if turbo.can_stream():
            return turbo.stream(
                [
                    turbo.append(
                        templates.TemplateResponse(
                            "_todo.html", context={"todo": todo}
                        ),
                        target="todos",
                    ),
                    turbo.update(
                        templates.TemplateResponse("_todo_input.html"),
                        target="form",
                    ),
                ]
            )
    return templates.TemplateResponse("index.html", context={"todos": todos})


def toggle(id_str: str or int, request: Request):
    todo = get_todo_by_id(id_str)
    todo.completed = not todo.completed
    if turbo.can_stream():
        return turbo.stream(
            turbo.replace(
                templates.TemplateResponse(
                    "_todo.html", context={"todo": todo}
                ),
                target=f"todo-{todo.id}",
            )
        )
    return RedirectResponse(request.url_for("index"))


def edit(id_str, request: Request):
    todo = get_todo_by_id(id_str)
    if request.method == "POST":
        todo.task = request.form["task"]
        return RedirectResponse(request.url_for("index"))
    return templates.TemplateResponse(
        "index.html", context={"todos": todos, "edit_id": todo.id}
    )


def delete(id_str, request: Request):
    todo = get_todo_by_id(id_str)
    todos.remove(todo)
    if turbo.can_stream():
        return turbo.stream(turbo.remove(target=f"todo-{todo.id}"))
    return RedirectResponse(request.url_for("index"))


routes = [
    Route("/", index, methods=["GET", "POST"]),
    Route("/toggle/{id_str}", toggle, methods=["POST"]),
    Route("/edit/{id_str}", edit, methods=["GET", "POST"]),
    Route("/delete/{id_str}", delete, methods=["POST"]),
]

todos = [Todo(task="buy eggs"), Todo(task="walk the dog")]
app = FastAPI(__name__, routes=routes)
turbo = Turbo(app)

templates = templating.Jinja2Templates(directory="templates")

app.mount("static", staticfiles.StaticFiles(directory="static"), name="static")
