# pylint: disable-all
import pytest

import spudbucket as sb

pytestmark = pytest.mark.usefixtures("app")


def test_setup(app):
    """
    Make sure that app setup and routing works as-intended.
    """
    import os
    assert app.name == "test_setup"

    randstr = os.urandom(20)

    @app.route("/")
    def index():
        return randstr

    with app.test_client() as c:
        assert randstr == c.get("/").data


def test_modes(app):
    @app.route("/", methods=["POST"])
    @sb.set_methods("POST")
    @sb.base
    def index(form):
        assert form.is_form_mode()
        return "success"

    with app.test_client() as c:
        assert c.post("/").data == b"success"
