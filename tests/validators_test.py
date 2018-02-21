# pylint: disable-all
import json

import flask
import pytest

import spudbucket as sb

pytestmark = pytest.mark.usefixtures("app")


def test_csrf(app):
    instance = {}
    validator = sb.v.CSRFValidator()

    @app.route("/", methods=["GET", "POST"])
    @sb.validator(validator)
    @sb.base
    def index(form):
        if form.is_form_mode():
            return "success"
        instance["token"] = flask.session["_csrf_token"]
        return flask.jsonify(flask.g.csrf_token_validator)

    with app.test_client() as c:
        # Check if sessions are required
        with pytest.raises(sb.e.InvalidSessionError):
            c.post("/", data={"csrf_token": ""})

        # Make sure data populates correctly
        result = c.get("/")
        assert flask.session["_csrf_token"] == instance["token"]
        items = validator.populate()
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        for item in ['csrf_token', 'csrf_tag']:
            assert item in items

        # Get the session value back when POSTing
        result = c.post("/", data={"csrf_token": flask.session["_csrf_token"]})
        assert result.data == b"success"

        # Raise a validation error when a value is invalid
        with pytest.raises(sb.e.ValidationError):
            c.post("/", data={"csrf_token": instance["token"][::-1]})

        # Raises a validation error when no value is provided
        with pytest.raises(sb.e.FormKeyError):
            c.post("/")


def test_email(app):
    no_domain_validator = sb.v.EmailValidator("email")
    domain_validator = sb.v.EmailValidator("email", domain="example.com")

    @app.route("/no_domain", methods=["GET", "POST"])
    @sb.validator(no_domain_validator)
    @sb.base
    def no_domain(form):
        if form.is_form_mode():
            return "success"
        return flask.jsonify(flask.g.email_validator)

    @app.route("/with_domain", methods=["GET", "POST"])
    @sb.validator(domain_validator)
    @sb.base
    def with_domain(form):
        if form.is_form_mode():
            return "success"
        return flask.jsonify(flask.g.email_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        for endpoint in [("/no_domain", no_domain_validator),
                         ("/with_domain", domain_validator)]:
            result = c.get(endpoint[0])
            items = endpoint[1].populate()
            content = result.data.decode('ascii')
            assert items == json.loads(content)
            for item in ["domain"]:
                assert item in items

        # Ensure that valid emails work
        result = c.post("/no_domain", data={"email": "test@example.com"})
        assert result.data == b"success"

        # Make sure that invalid emails don't work
        for email in ("@example.com", "test@", "test@test@example.com"):
            with pytest.raises(sb.e.ValidationError):
                c.post("/no_domain", data={"email": email})

        # Ensure that valid domains work; does not check subdomains
        result = c.post("/with_domain", data={"email": "test@example.com"})
        assert result.data == b"success"

        # Make sure that subdomains _don't_ work
        for email in ("test@a.example.com", "test@aexample.com"):
            with pytest.raises(sb.e.ValidationError):
                result = c.post("/with_domain",
                                data={"email": email})
