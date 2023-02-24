import logging as log
import typing

from fastapi import Request

from turbo_fastapi.turbo import Turbo  # noqa: F401


# Adding functions to replace flask's `flash` functionality
def flash(request: Request, message: typing.Any, category: str = "primary"):
    if "_messages" not in request.session:
        request.session["_messages"] = []
        request.session.get["_messages"].append(
            {"message": message, "category": category}
        )


def get_flashed_messages(request: Request):
    log.info(request.session)
    msg = "_messages"
    return request.session.pop(msg) if msg in request.session else []
