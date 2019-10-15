# Test routing requests with JSON
import json

import pytest

import gigaspoon

pytestmark = pytest.mark.usefixtures("app")


def test_setup(app):
    validator = gigaspoon.v.Exists()

    @app.route("/", methods=["POST"])
    @gigaspoon.flask.validator({
        "example": validator,
    })
    @gigaspoon.flask.base
    def index(form):
        assert form["example"] is not None
        return ""

    with app.test_client() as c:
        c.post("/", data=json.dumps({"example": "hello"}),
               content_type="application/json")
        with pytest.raises(gigaspoon.e.FormKeyError):
            c.post("/", data=json.dumps({"nothing": "works"}),
                   content_type="application/json")
