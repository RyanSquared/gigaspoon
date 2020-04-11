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


def test_list(app):
    list_validator = gs.v.List(gs.v.Length(min=2, max=4))
    many_list_validator = gs.v.List([gs.v.Length(min=2, max=7),
                                     gs.v.Bool()])

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({"input": list_validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    @app.route("/many", methods=["GET", "POST"])
    @gs.flask.validator({"input": many_list_validator})
    @gs.flask.base
    def many(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        result = c.get("/")
        items = gs.u.sanitize(list_validator.name,
                              list_validator.populate("input"))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == ["list_validators"]

        result = c.get("/many")
        items = gs.u.sanitize(many_list_validator.name,
                              many_list_validator.populate("input"))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == ["list_validators"]

        # Ensure valid options work
        c.post("/", data={"input.1": "test"})
        c.post("/many", data={"input.1": "yes", "input.2": "false"})

        # Ensure invalid fields don't work
        for field in ["input", "input.dict_entry"]:
            with pytest.raises(gs.e.ValidationError):
                c.post("/", data={field: "test"})

        # Ensure invalid values don't work
        with pytest.raises(gs.e.ValidationError):
            c.post("/", data={"input.1": "Testing"})


def test_dict(app):
    dict_validator = gs.v.Dict({"test_key": gs.v.Length(min=2, max=4),
                                "test_mult": [gs.v.Length(min=4),
                                              gs.v.Bool()],
                                "test_list": gs.v.List([gs.v.Length(max=5),
                                                        gs.v.Bool()])})

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({"input": dict_validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        result = c.get("/")
        items = gs.u.sanitize(dict_validator.name,
                              dict_validator.populate("input"))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        # TODO populate the dict_validators field and do comparison on the
        # values put into it
        assert sorted(items.keys()) == ["dict_test_key", "dict_test_list",
                                        "dict_test_mult"]

        # Ensure valid options work
        c.post("/", data={"input.test_key": "test",
                          "input.test_mult": "false",
                          "input.test_list.1": "yes"})

        # Ensure invalid types don't work
        for field in ["input", "input.1"]:
            with pytest.raises(gs.e.ValidationError):
                c.post("/", data={field: "test"})

        # Ensure invalid fields don't work
        with pytest.raises(gs.e.FormKeyError):
            c.post("/", data={"input.testing": "test"})

        # Ensure invalid values don't work
        with pytest.raises(gs.e.ValidationError):
            c.post("/", data={"input.test_key": "Testing",
                              "input.test_mult": "asdfpotato",
                              "input.test_list.1": "not a bool"})


def test_map(app):
    map_validator = gs.v.Map(gs.v.Length(min=2, max=10))

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({"input": map_validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        result = c.get("/")
        items = gs.u.sanitize(map_validator.name,
                              map_validator.populate("input"))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == ["map_validators"]

        # Ensure valid options work
        c.post("/", data={"input.testing": "test"})
        c.post("/many", data={"input.hello": "world", "input.haudi": "tests!"})

        # Ensure invalid fields don't work
        for field in ["input", "input.1"]:
            with pytest.raises(gs.e.ValidationError):
                c.post("/", data={field: "test"})

        # Ensure invalid values don't work
        with pytest.raises(gs.e.ValidationError):
            c.post("/", data={"input.key": "this is a long string"})


def test_lambdamap(app):
    lambdamap_validator = gs.v.LambdaMap(lambda x: int(x) * 2)

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({"input": lambdamap_validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        result = c.get("/")
        items = gs.u.sanitize(lambdamap_validator.name,
                              lambdamap_validator.populate("input"))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == []

        # Ensure valid options work
        for item in ["1", "5", "27"]:
            c.post("/", data={"input": item})

        # Ensure invalid options don't work
        for item in ["asdf", "these are words and not numbers"]:
            with pytest.raises(gs.e.ValidationError) as err:
                c.post("/", data={"input": item})
            assert err.value.value == item


def test_lambdafilter(app):
    lambdafilter_validator = gs.v.LambdaFilter(lambda x: x.isprintable())
    none_validator = gs.v.LambdaFilter(lambda x: {"a": "b"}.get(x, None),
                                       matches=gs.v.LambdaFilter.NONE)
    not_none_validator = gs.v.LambdaFilter(lambda x: {"a": "b"}.get(x, None),
                                           matches=gs.v.LambdaFilter.NOTNONE)
    falsy_validator = gs.v.LambdaFilter(lambda x: x.isdigit(),
                                        matches=gs.v.LambdaFilter.FALSY)
    literal_validator = gs.v.LambdaFilter(lambda x: int(x) + 1,
                                          matches=2)

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({"input": lambdafilter_validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    @app.route("/is-none", methods=["GET", "POST"])
    @gs.flask.validator({"input": none_validator})
    @gs.flask.base
    def is_none(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    @app.route("/is-not-none", methods=["GET", "POST"])
    @gs.flask.validator({"input": not_none_validator})
    @gs.flask.base
    def is_not_none(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    @app.route("/is-falsy", methods=["GET", "POST"])
    @gs.flask.validator({"input": falsy_validator})
    @gs.flask.base
    def is_falsy(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    @app.route("/is-2", methods=["GET", "POST"])
    @gs.flask.validator({"input": literal_validator})
    @gs.flask.base
    def is_2(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.input_validator)

    # TODO test over various other options for `matches`

    with app.test_client() as c:
        # Ensure valid options work

        for route, item in [("/", "hello world!"),  # is printable text
                            ("/is-none", "b"),  # dict contains "a"
                            ("/is-not-none", "a"),  # dict contains "a"
                            ("/is-falsy", "asdf"),  # comparing is digit
                            ("/is-2", "1")]:  # testing if + 1 == 2
            c.post(route, data={"input": item})

        for route, item in [("/", "hello,\nworld!"),  # is not printable text
                            ("/is-none", "a"),  # dict contains "a"
                            ("/is-not-none", "b"),  # dict contains "a"
                            ("/is-falsy", "7"),  # comparing is digit
                            ("/is-2", "9")]:  # testing if + 1 == 2
            with pytest.raises(gs.e.ValidationError) as err:
                c.post(route, data={"input": item})
            assert err.value.value == item


def test_bool(app):
    bool_validator = gs.v.Bool()

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({"input": bool_validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return flask.jsonify({"output": form["input"]})
        return flask.jsonify(flask.g.input_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        result = c.get("/")
        items = gs.u.sanitize(bool_validator.name,
                              bool_validator.populate("input"))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == []

        # Ensure valid options work
        for item in ["YeS", "TRUE", "on"]:
            result = c.post("/", data={"input": item})
            assert {"output": True} == json.loads(result.data.decode('ascii'))

        # Ensure valid options work
        for item in ["NO", "false", "Off"]:
            result = c.post("/", data={"input": item})
            assert {"output": False} == json.loads(result.data.decode('ascii'))

        # Ensure invalid options don't work
        for item in ["hbbhbhbnbbhbhb", "27", "0"]:
            with pytest.raises(gs.e.ValidationError) as err:
                c.post("/", data={"input": item})
            assert err.value.value == item


def test_date(app):
    use_isoformat_validator = gs.v.Date(use_isoformat=True)
    format_validator = gs.v.Date("%m/%d/%Y")  # ugly format lol
    keep_date_object_validator = gs.v.Date(use_isoformat=True,
                                           keep_date_object=True)
    bad_validator = gs.v.Date(use_isoformat=True)
    bad_validator.use_isoformat = False  # naughty naughty, raises ValueError

    # Ensure that making a bad validator is a ValueError
    with pytest.raises(ValueError):
        gs.v.Date()

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

    @app.route("/bad_validator", methods=["GET", "POST"])
    @gs.flask.validator({"date": bad_validator})
    @gs.flask.base
    def is_invalid_validator(form):
        if form.is_form():
            return "success?"
        return flask.jsonify(flask.g.date_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        for endpoint in [("/use_isoformat", use_isoformat_validator),
                         ("/format", format_validator),
                         ("/keep_date_object", keep_date_object_validator),
                         ("/bad_validator", bad_validator)]:
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

        # Ensure that a corrupted validator raises a ValueError and not a
        # validation error
        with pytest.raises(ValueError):
            c.post("/bad_validator", data={"date": ""})


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


def test_length(app):
    length_validator = gs.v.Length(min=15, max=30)

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({"username": length_validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.username_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        result = c.get("/")
        items = gs.u.sanitize(length_validator.name,
                              length_validator.populate("fruit"))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == ["length_max", "length_min"]

        for test in ["this one is fine", "so is this one?"]:
            c.post("/", data={"username": test})

        # Ensure invalid options don't work
        for test in ["too small", "this one is way too long it will be bad"]:
            with pytest.raises(gs.e.ValidationError) as err:
                c.post("/", data={"username": test})
            assert err.value.value == test


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
    bad_validator = gs.v.Time(use_isoformat=True)
    bad_validator.use_isoformat = False  # naughty naughty, raises ValueError

    # Ensure that making a bad validator is a ValueError
    with pytest.raises(ValueError):
        gs.v.Time()

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

    @app.route("/bad_validator", methods=["GET", "POST"])
    @gs.flask.validator({"time": bad_validator})
    @gs.flask.base
    def is_invalid_validator(form):
        if form.is_form():
            return "success?"
        return flask.jsonify(flask.g.time_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        for endpoint in [("/use_isoformat", use_isoformat_validator),
                         ("/format", format_validator),
                         ("/keep_time_object", keep_time_object_validator),
                         ("/bad_validator", bad_validator)]:
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

        # Ensure that a corrupted validator raises a ValueError and not a
        # validation error
        with pytest.raises(ValueError):
            c.post("/bad_validator", data={"time": ""})


def test_select(app):
    options = ["apples", "bananas", "oranges"]
    select_validator = gs.v.Select(options)

    @app.route("/", methods=["GET", "POST"])
    @gs.flask.validator({"fruit": select_validator})
    @gs.flask.base
    def index(form):
        if form.is_form():
            return "success"
        return flask.jsonify(flask.g.fruit_validator)

    with app.test_client() as c:
        # Make sure data populates correctly
        result = c.get("/")
        items = gs.u.sanitize(select_validator.name,
                              select_validator.populate("fruit"))
        content = result.data.decode('ascii')
        assert items == json.loads(content)
        assert sorted(items.keys()) == ["select_options"]
        assert sorted(items["select_options"]) == options

        # Ensure valid options work
        for fruit in options:
            c.post("/", data={"fruit": fruit})

        # Ensure invalid options don't work
        for fruit in ["durian", "pineapple", "tomato"]:  # i guess we're picky
            with pytest.raises(gs.e.ValidationError) as err:
                c.post("/", data={"fruit": fruit})
            assert err.value.value == fruit
