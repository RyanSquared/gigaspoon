# pylint: disable-all
import flask
import pytest


@pytest.fixture
def app(request):
    """
    Create and return a Flask application.
    """
    import os
    app = flask.Flask(request.function.__name__)
    app.testing = True
    app.secret_key = os.urandom(24)
    return app
