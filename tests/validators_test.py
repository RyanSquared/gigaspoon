# pylint: disable-all
import json

import flask
import pytest

import spudbucket as sb

pytestmark = pytest.mark.usefixtures("app")


def test_base_validator_interface():
    import os
    bytes_1, bytes_2 = os.urandom(24), os.urandom(24)
    validator = sb.v.Validator()

    # Test `validate` raises NotImplementedError
    with pytest.raises(NotImplementedError):
        validator.validate(0, 0, 0)

    # Test dummy `populate` returns nothing
    # Fallback for validators that don't provide populable data
    assert validator.populate() is None

    # Test raise_error actually raises the proper error
    with pytest.raises(sb.e.ValidationError) as err:
        validator.raise_error(bytes_1, bytes_2)
    assert err.value.key == bytes_1
    assert err.value.value == bytes_2


def test_csrf(app):
    instance = {}
    validator = sb.v.CSRF()

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
        assert sorted(items.keys()) == ["csrf_tag", "csrf_token", "name"]

        # Get the session value back when POSTing
        result = c.post("/", data={"csrf_token": flask.session["_csrf_token"]})
        assert result.data == b"success"

        # Raise a validation error when a value is invalid
        with pytest.raises(sb.e.ValidationError) as err:
            c.post("/", data={"csrf_token": instance["token"][::-1]})

        assert err.value.value == instance["token"][::-1]

        # Raises a validation error when no value is provided
        with pytest.raises(sb.e.FormKeyError) as err:
            c.post("/")

        assert err.value.key == "csrf_token"


def test_email(app):
    no_domain_validator = sb.v.Email("email")
    domain_validator = sb.v.Email("email", domain="example.com")

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
            assert sorted(items.keys()) == ["domain"]

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


def test_ipaddr(app):
    ipv4_validator = sb.v.IPAddress("ipv4")
    ipv6_validator = sb.v.IPAddress("ipv6", address_type=["ipv6"])

    both_validator = sb.v.IPAddress("both", address_type=["ipv4", "ipv6"])

    @app.route("/ipv4", methods=["GET", "POST"])
    @sb.validator(ipv4_validator)
    @sb.base
    def ipv4(form):
        if form.is_form_mode():
            return "success"
        return flask.jsonify(flask.g.ipv4_validator)

    @app.route("/ipv6", methods=["GET", "POST"])
    @sb.validator(ipv6_validator)
    @sb.base
    def ipv6(form):
        if form.is_form_mode():
            return "success"
        return flask.jsonify(flask.g.ipv6_validator)

    @app.route("/both", methods=["GET", "POST"])
    @sb.validator(both_validator)
    @sb.base
    def both(form):
        if form.is_form_mode():
            return "success"
        return flask.jsonify(flask.g.both_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        for endpoint in [("/ipv4", ipv4_validator),
                         ("/ipv6", ipv6_validator),
                         ("/both", both_validator)]:
            result = c.get(endpoint[0])
            items = endpoint[1].populate()
            content = result.data.decode('ascii')
            assert items == json.loads(content)
            assert sorted(items.keys()) == ["address_type"]

        # Test "canonical" IPv6
        for ip in ["2001:db8:0:0:1:0:0:1", "2001:0db8:0:0:1:0:0:1",
                   "2001:db8::1:0:0:1",    "2001:db8::0:1:0:0:1",
                   "2001:0db8::1:0:0:1",   "2001:db8:0:0:1::1",
                   "2001:db8:0000:0:1::1", "2001:DB8:0:0:1::1"]:
            result = c.post("/ipv6", data={"ipv6": ip})
            assert result.data == b"success"

        # Test bad IPv6
        for ip in ["2001:db8::1::1", "2001:db8:a:b:c:d:e:a:b", "::g"]:
            with pytest.raises(sb.e.ValidationError) as err:
                c.post("/ipv6", data={"ipv6": ip})
            assert err.value.value == ip

        # Test valid IPv4
        for ip in ["127.127.127.127", "1.1.1.1"]:
            result = c.post("/ipv4", data={"ipv4": ip})
            assert result.data == b"success"

        # Test bad IPv4
        for ip in ["256.0.0.0", "1.1.1", "1.1.1.1.1", "127.127.127."]:
            with pytest.raises(sb.e.ValidationError) as err:
                c.post("/ipv4", data={"ipv4": ip})
            assert err.value.value == ip


def test_regex(app):
    regex_validator = sb.v.Regex("username", "^[a-z][a-z0-9]{0,29}$")

    @app.route("/", methods=["GET", "POST"])
    @sb.validator(regex_validator)
    @sb.base
    def index(form):
        if form.is_form_mode():
            return "success"
        return flask.jsonify(flask.g.username_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        result = c.get("/")
        items = regex_validator.populate()
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == ["pattern"]

        # Ensure valid names work
        for name in ["bob", "daaaaaaaave", "test12345", "a" * 30]:
            c.post("/", data={"username": name})

        # Ensure invalid names don't work
        for name in ["_", "", "a" * 31, "A", "\\"]:
            with pytest.raises(sb.e.ValidationError) as err:
                c.post("/", data={"username": name})
            assert err.value.value == name
