# pylint: disable-all
# Required for testing validators
import datetime

# Required for parsing returned inputs
import json

import flask
import pytest

import gigaspoon as gs

pytestmark = pytest.mark.usefixtures("app")


def test_base_validator_interface():
    import os
    bytes_1, bytes_2 = os.urandom(24), os.urandom(24)
    validator = gs.v.Validator()

    # Test `validate` raises NotImplementedError
    with pytest.raises(NotImplementedError):
        validator.validate(0, 0)

    # Test dummy `populate` returns empty dict
    # Fallback for validators that don't provide populable data
    assert validator.populate("") == {}

    # Test raise_error actually raises the proper error
    with pytest.raises(gs.e.ValidationError) as err:
        validator.raise_error(bytes_1, bytes_2)
    assert err.value.key == bytes_1
    assert err.value.value == bytes_2


def test_csrf(app):
    instance = {}
    validator = gs.flask.CSRF()

    VALIDATOR_NAME = "csrf"

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({VALIDATOR_NAME: validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return "success"
        instance["token"] = flask.session["_csrf_token"]
        return flask.jsonify(flask.g.csrf_validator)

    with app.test_client() as c:
        # Check if sessions are required
        with pytest.raises(gs.flask.InvalidSessionError):
            c.post("/", data={VALIDATOR_NAME: ""})

        # Make sure data populates correctly
        result = c.get("/")
        assert flask.session["_csrf_token"] == instance["token"]
        items = gs.u.sanitize(VALIDATOR_NAME,
                              validator.populate(VALIDATOR_NAME))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == ["csrf_name", "csrf_tag", "csrf_token"]

        # Get the session value back when POSTing
        result = c.post("/",
                        data={VALIDATOR_NAME: flask.session["_csrf_token"]})
        assert result.data == b"success"

        # Raise a validation error when a value is invalid
        with pytest.raises(gs.e.ValidationError) as err:
            c.post("/", data={VALIDATOR_NAME: instance["token"][::-1]})

        assert err.value.value == instance["token"][::-1]

        # Raises a validation error when no value is provided
        with pytest.raises(gs.e.FormKeyError) as err:
            c.post("/")

        assert err.value.key == VALIDATOR_NAME


def test_date(app):
    use_isoformat_validator = gs.v.Date(use_isoformat=True)
    format_validator = gs.v.Date("%m/%d/%Y")  # ugly format lol
    keep_date_object_validator = gs.v.Date(use_isoformat=True,
                                           keep_date_object=True)

    @app.route("/use_isoformat", methods=["GET", "POST"])
    @gs.flask.validator({"date": use_isoformat_validator})
    @gs.flask.base
    def no_domain(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.date_validator)

    @app.route("/format", methods=["GET", "POST"])
    @gs.flask.validator({"date": format_validator})
    @gs.flask.base
    def with_domain(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.date_validator)

    @app.route("/keep_date_object", methods=["GET", "POST"])
    @gs.flask.validator({"date": keep_date_object_validator})
    @gs.flask.base
    def keep_date_object(form):
        if form.is_form():
            assert isinstance(form["date"], datetime.date), "did not transform"
            return "success"
        return flask.jsonify(flask.g.date_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        for endpoint in [("/use_isoformat", use_isoformat_validator),
                         ("/format", format_validator),
                         ("/keep_date_object", keep_date_object_validator)]:
            result = c.get(endpoint[0])
            items = gs.u.sanitize("date", endpoint[1].populate("date"))
            content = result.data.decode('ascii')
            assert items == json.loads(content)
            assert sorted(items.keys()) == ["date_fmt", "date_use_isoformat"]

        # Ensure that ISO format works
        result = c.post("/use_isoformat", data={"date": "2020-04-10"})
        assert result.data == b"success"

        # Ensure that ISO format can fail on bad input
        with pytest.raises(gs.e.ValidationError):
            result = c.post("/use_isoformat", data={"date": "04/10/2020"})

        # Ensure that custom formats work
        result = c.post("/format", data={"date": "04/10/2020"})
        assert result.data == b"success"

        # Ensure that custom formats can fail on bad input
        with pytest.raises(gs.e.ValidationError):
            result = c.post("/format", data={"date": "2020-04-10"})

        # Ensure that data is transformed on keep_date_object
        result = c.post("/keep_date_object", data={"date": "2020-04-10"})


def test_email(app):
    no_domain_validator = gs.v.Email()
    domain_validator = gs.v.Email(domain="example.com")

    @app.route("/no_domain", methods=["GET", "POST"])
    @gs.flask.validator({"email": no_domain_validator})
    @gs.flask.base
    def no_domain(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.email_validator)

    @app.route("/with_domain", methods=["GET", "POST"])
    @gs.flask.validator({"email": domain_validator})
    @gs.flask.base
    def with_domain(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.email_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        for endpoint in [("/no_domain", no_domain_validator),
                         ("/with_domain", domain_validator)]:
            result = c.get(endpoint[0])
            items = gs.u.sanitize("email", endpoint[1].populate("email"))
            content = result.data.decode('ascii')
            assert items == json.loads(content)
            assert sorted(items.keys()) == ["email_domain"]

        # Ensure that valid emails work
        result = c.post("/no_domain", data={"email": "test@example.com"})
        assert result.data == b"success"

        # Make sure that invalid emails don't work
        for email in ("@example.com", "test@", "test@test@example.com"):
            with pytest.raises(gs.e.ValidationError):
                c.post("/no_domain", data={"email": email})

        # Ensure that valid domains work; does not check subdomains
        result = c.post("/with_domain", data={"email": "test@example.com"})
        assert result.data == b"success"

        # Make sure that subdomains _don't_ work
        for email in ("test@a.example.com", "test@aexample.com"):
            with pytest.raises(gs.e.ValidationError):
                result = c.post("/with_domain",
                                data={"email": email})


def test_ipaddr(app):
    ipv4_validator = gs.v.IPAddress()
    ipv6_validator = gs.v.IPAddress(address_type=["ipv6"])

    both_validator = gs.v.IPAddress(address_type=["ipv4", "ipv6"])

    @app.route("/ipv4", methods=["GET", "POST"])
    @gs.flask.validator({"addr": ipv4_validator})
    @gs.flask.base
    def ipv4(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.addr_validator)

    @app.route("/ipv6", methods=["GET", "POST"])
    @gs.flask.validator({"addr": ipv6_validator})
    @gs.flask.base
    def ipv6(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.addr_validator)

    @app.route("/both", methods=["GET", "POST"])
    @gs.flask.validator({"addr": both_validator})
    @gs.flask.base
    def both(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.addr_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        for endpoint in [("/ipv4", ipv4_validator),
                         ("/ipv6", ipv6_validator),
                         ("/both", both_validator)]:
            result = c.get(endpoint[0])
            items = gs.u.sanitize(endpoint[1].name,
                                  endpoint[1].populate("addr"))
            content = result.data.decode('ascii')
            assert items == json.loads(content)
            assert sorted(items.keys()) == ["ipaddress_type"]

        # Test "canonical" IPv6
        for ip in ["2001:db8:0:0:1:0:0:1", "2001:0db8:0:0:1:0:0:1",
                   "2001:db8::1:0:0:1",    "2001:db8::0:1:0:0:1",
                   "2001:0db8::1:0:0:1",   "2001:db8:0:0:1::1",
                   "2001:db8:0000:0:1::1", "2001:DB8:0:0:1::1"]:
            result = c.post("/ipv6", data={"addr": ip})
            assert result.data == b"success"

        # Test bad IPv6
        for ip in ["2001:db8::1::1", "2001:db8:a:b:c:d:e:a:b", "::g"]:
            with pytest.raises(gs.e.ValidationError) as err:
                c.post("/ipv6", data={"addr": ip})
            assert err.value.value == ip

        # Test valid IPv4
        for ip in ["127.127.127.127", "1.1.1.1"]:
            result = c.post("/ipv4", data={"addr": ip})
            assert result.data == b"success"

        # Test bad IPv4
        for ip in ["256.0.0.0", "1.1.1", "1.1.1.1.1", "127.127.127."]:
            with pytest.raises(gs.e.ValidationError) as err:
                c.post("/ipv4", data={"addr": ip})
            assert err.value.value == ip


def test_regex(app):
    regex_validator = gs.v.Regex("^[a-z][a-z0-9]{0,29}$")

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({"username": regex_validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.username_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        result = c.get("/")
        items = gs.u.sanitize(regex_validator.name,
                              regex_validator.populate("username"))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == ["regex_pattern"]

        # Ensure valid names work
        for name in ["bob", "daaaaaaaave", "test12345", "a" * 30]:
            c.post("/", data={"username": name})

        # Ensure invalid names don't work
        for name in ["_", "", "a" * 31, "A", "\\"]:
            with pytest.raises(gs.e.ValidationError) as err:
                c.post("/", data={"username": name})
            assert err.value.value == name


def test_time(app):
    use_isoformat_validator = gs.v.Time(use_isoformat=True)
    format_validator = gs.v.Time("%I:%M %p")
    keep_time_object_validator = gs.v.Time(use_isoformat=True,
                                           keep_time_object=True)

    @app.route("/use_isoformat", methods=["GET", "POST"])
    @gs.flask.validator({"time": use_isoformat_validator})
    @gs.flask.base
    def no_domain(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.time_validator)

    @app.route("/format", methods=["GET", "POST"])
    @gs.flask.validator({"time": format_validator})
    @gs.flask.base
    def with_domain(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.time_validator)

    @app.route("/keep_time_object", methods=["GET", "POST"])
    @gs.flask.validator({"time": keep_time_object_validator})
    @gs.flask.base
    def keep_time_object(form):
        if form.is_form():
            assert isinstance(form["time"], datetime.time), "did not transform"
            return "success"
        return flask.jsonify(flask.g.time_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        for endpoint in [("/use_isoformat", use_isoformat_validator),
                         ("/format", format_validator),
                         ("/keep_time_object", keep_time_object_validator)]:
            result = c.get(endpoint[0])
            items = gs.u.sanitize("time", endpoint[1].populate("time"))
            content = result.data.decode('ascii')
            assert items == json.loads(content)
            assert sorted(items.keys()) == ["time_fmt", "time_use_isoformat"]

        # Ensure that ISO format works
        result = c.post("/use_isoformat", data={"time": "19:51"})
        assert result.data == b"success"

        # Ensure that ISO format can fail on bad input
        with pytest.raises(gs.e.ValidationError):
            result = c.post("/use_isoformat", data={"time": "7:51 PM"})

        # Ensure that custom formats work
        result = c.post("/format", data={"time": "7:51 PM"})
        assert result.data == b"success"

        # Ensure that custom formats can fail on bad input
        with pytest.raises(gs.e.ValidationError):
            result = c.post("/format", data={"time": "19:51"})

        # Ensure that data is transformed on keep_time_object
        result = c.post("/keep_time_object", data={"time": "19:51"})
