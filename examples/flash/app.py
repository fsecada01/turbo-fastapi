from fastapi import FastAPI, Request, Response
from fastapi.templating import Jinja2Templates

from turbo_fastapi import Turbo, flash

app = FastAPI(__name__)
app.secret_key = "top-secret!"
turbo = Turbo(app)

templates = Jinja2Templates(directory="templates")


@app.after_request
def after_request(response: Response):
    # if the response has the turbo-stream content type, then append one more
    # stream with the contents of the alert section of the page
    if response.headers["Content-Type"].startswith(
        "text/vnd.turbo-stream.html"
    ):
        response.response.append(
            turbo.update(
                templates.TemplateResponse("alert.html"), "alert"
            ).encode()
        )
        if response.content_length:
            response.content_length += len(response.response[-1])
    return response


@app.get("/")
def index(request: Request):
    name_error = ""
    return templates.TemplateResponse(
        "index.html", context={"name_error": name_error}
    )


@app.post("/")
def index(request: Request):
    name_error = ""
    if request.method == "POST":
        name = request.form["name"]
        if name:
            flash(request=request, message=f"Hello, {name}!")
            name_error = ""
        else:
            flash(request=request, message="Invalid name")
            name_error = "The username cannot be empty."
        if turbo.can_stream():
            return turbo.stream(turbo.update(name_error, "name_error"))
    return templates.TemplateResponse(
        "index.html", context={"name_error": name_error}
    )
