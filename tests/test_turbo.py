import unittest
from typing import Optional
from unittest import mock

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from jinja2 import BaseLoader, Environment
from pydantic import BaseSettings
from werkzeug.exceptions import NotFound
from werkzeug.routing import Map

import turbo_fastapi

app = FastAPI(name="test_application")
turbo = turbo_fastapi.Turbo(app)
test_client = TestClient(app)


class TestSettings(BaseSettings):
    TURBO_WEBSOCKET_ROUTE: str = "/turbo-stream"


class TestSettingsNoWS(BaseSettings):
    TURBO_WEBSOCKET_ROUTE: Optional[str] = None


def render_to_string(template_str: str, **kwargs):
    r_template = Environment(loader=BaseLoader()).from_string(template_str)
    data = r_template.render(**kwargs)

    return data


class TestTurbo(unittest.TestCase):
    def test_direct_create(self):
        settings = TestSettings
        app.settings = settings

        @app.get("/test")
        def test():
            return render_to_string("{{ turbo() }}")

        url_adapter = Map().bind(server_name="localhost", script_name="/")
        assert url_adapter.match("/turbo-stream", websocket=True) == (
            "__flask_sock.turbo_stream",
            {},
        )

        rv = test_client.get("/test")
        assert b"@hotwired/turbo@" in rv.data
        assert b"Turbo.connectStreamSource" in rv.data

    def test_indirect_create(self):
        @app.get("/test")
        def test():
            return render_to_string("{{ turbo() }}")

        url_adapter = Map().bind(server_name="localhost", script_name="/")
        assert url_adapter.match("/turbo-stream", websocket=True) == (
            "__flask_sock.turbo_stream",
            {},
        )

        rv = test_client.get("/test")
        assert b"@hotwired/turbo@" in rv.data
        assert b"Turbo.connectStreamSource" in rv.data

    def test_create_custom_ws(self):
        @app.websocket("/ws")
        def websocket_endpoint(websocket: WebSocket):
            websocket.accept()
            while True:
                data = websocket.receive()
                websocket.send_text(f"Message text was: {data}")

        @app.get("/test")
        def test():
            return render_to_string("{{ turbo() }}")

        url_adapter = Map().bind(server_name="localhost", script_name="/")
        with pytest.raises(NotFound):
            url_adapter.match("/turbo-stream", websocket=True)
        assert url_adapter.match("/ws", websocket=True) == (
            "__flask_sock.turbo_stream",
            {},
        )

        rv = test_client.get("/test")
        assert b"@hotwired/turbo@" in rv.data
        assert b"Turbo.connectStreamSource" in rv.data

    def test_create_no_ws(self):
        settings = TestSettingsNoWS()

        app.settings = settings

        @app.get("/test")
        def test():
            return render_to_string("{{ turbo() }}")

        url_adapter = Map().bind(server_name="localhost", script_name="/")
        with pytest.raises(NotFound):
            url_adapter.match("/turbo-stream", websocket=True)

        rv = test_client.get("/test")
        assert b"@hotwired/turbo@" in rv.data
        assert b"Turbo.connectStreamSource" not in rv.data

    def test_create_custom_turbo_version(self):
        settings = TestSettings()

        app.settings = settings

        @app.get("/test")
        def test():
            return render_to_string('{{ turbo(version="1.2.3") }}')

        url_adapter = Map().bind(server_name="localhost", script_name="/")
        assert url_adapter.match("/turbo-stream", websocket=True) == (
            "__flask_sock.turbo_stream",
            {},
        )

        rv = test_client.get("/test")
        assert b"@hotwired/turbo@1.2.3/dist" in rv.data
        assert b"Turbo.connectStreamSource" in rv.data

    def test_create_latest_turbo_version(self):
        settings = TestSettings()

        app.settings = settings

        @app.get("/test")
        def test():
            return render_to_string("{{ turbo(version=None) }}")

        url_adapter = Map().bind(server_name="localhost", script_name="/")
        assert url_adapter.match("/turbo-stream", websocket=True) == (
            "__flask_sock.turbo_stream",
            {},
        )

        rv = test_client.get("/test")
        assert b"@hotwired/turbo/dist" in rv.data
        assert b"Turbo.connectStreamSource" in rv.data

    def test_create_custom_turbo_url(self):
        app.settings = TestSettings()

        @app.get("/test")
        def test():
            return render_to_string('{{ turbo(url="/js/turbo.js") }}')

        url_adapter = Map().bind(server_name="localhost", script_name="/")
        assert url_adapter.match("/turbo-stream", websocket=True) == (
            "__flask_sock.turbo_stream",
            {},
        )

        rv = self.test_client.get("/test")
        assert b"/js/turbo.js" in rv.data
        assert b"Turbo.connectStreamSource" in rv.data

    def test_requested_frame(self):
        app.settings = TestSettings()

        with app.test_request_context("/", headers={"Turbo-Frame": "foo"}):
            assert turbo.requested_frame() == "foo"

    def test_can_stream(self):
        app.settings = TestSettings()

        with app.request("/", headers={"Accept": "text/html"}):
            # with app.test_request_context("/", headers={"Accept":
            # "text/html"}):
            assert not turbo.can_stream()
        with app.test_request_context(
            "/", headers={"Accept": "text/vnd.turbo-stream.html"}
        ):
            assert turbo.can_stream()

    def test_can_push(self):
        app.settings = TestSettings()

        assert not turbo.can_push()
        turbo.clients = {"123": "client"}
        assert turbo.can_push()
        assert turbo.can_push(to="123")
        assert not turbo.can_push(to="456")

    def test_streams(self):
        app.settings = TestSettings()

        actions = ["append", "prepend", "replace", "update", "after", "before"]
        for action in actions:
            assert getattr(turbo, action)("foo", "bar") == (
                f'<turbo-stream action="{action}" target="bar">'
                f"<template>foo</template></turbo-stream>"
            )
        assert turbo.remove("bar") == (
            '<turbo-stream action="remove" target="bar">'
            "<template></template></turbo-stream>"
        )

    def test_stream_response(self):
        app.settings = TestSettings()

        with app.test_request_context("/"):
            r = turbo.stream([turbo.append("foo", "bar"), turbo.remove("baz")])
        assert r.get_data() == (
            b'<turbo-stream action="append" target="bar">'
            b"<template>foo</template>"
            b"</turbo-stream>"
            b'<turbo-stream action="remove" target="baz">'
            b"<template></template>"
            b"</turbo-stream>"
        )

    def test_push(self):
        app.settings = TestSettings()
        turbo.clients = {"123": [mock.MagicMock()], "456": [mock.MagicMock()]}

        expected_stream = (
            '<turbo-stream action="append" target="bar">'
            "<template>foo</template>"
            "</turbo-stream>"
            '<turbo-stream action="remove" target="baz">'
            "<template></template>"
            "</turbo-stream>"
        )
        turbo.push([turbo.append("foo", "bar"), turbo.remove("baz")])
        turbo.clients["123"][0].send.assert_called_with(expected_stream)
        turbo.clients["456"][0].send.assert_called_with(expected_stream)

    def test_push_to(self):
        app.settings = TestSettings()
        turbo.clients = {"123": [mock.MagicMock()], "456": [mock.MagicMock()]}

        expected_stream = (
            '<turbo-stream action="append" target="bar">'
            "<template>foo</template>"
            "</turbo-stream>"
            '<turbo-stream action="remove" target="baz">'
            "<template></template>"
            "</turbo-stream>"
        )
        turbo.push([turbo.append("foo", "bar"), turbo.remove("baz")], to="456")
        turbo.clients["123"][0].send.assert_not_called()
        turbo.clients["456"][0].send.assert_called_with(expected_stream)
        turbo.clients["123"][0].reset_mock()
        turbo.clients["456"][0].reset_mock()
        turbo.push(
            [turbo.append("foo", "bar"), turbo.remove("baz")], to=["123"]
        )
        turbo.clients["123"][0].send.assert_called_with(expected_stream)
        turbo.clients["456"][0].send.assert_not_called()
