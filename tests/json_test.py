# Test routing requests with JSON
import json

import pytest

import spudbucket as sb

pytestmark = pytest.mark.usefixtures("app")


def test_setup(app):
    validator = sb.v.Exists("example")

    @app.route("/", methods=["POST"])
    @sb.validator(validator)
    @sb.base
    def index(form):
        assert form["example"] is not None
        return ""

    with app.test_client() as c:
        c.post("/", data=json.dumps({"example": "hello"}),
               content_type="application/json")
        with pytest.raises(sb.e.FormKeyError):
            c.post("/", data=json.dumps({"nothing": "works"}),
                   content_type="application/json")
