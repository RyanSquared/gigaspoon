"""
This module provides utility validators to avoid rewriting validators that
are not usecase specific.
"""
import re
import socket

from . import errors as e


class Validator(object):
    """
    Base class for all Validator objects. Your Validator must extend off
    this class or the handler will raise an assertion error. Usage of how
    to extend off this class is demonstrated in the `custom-validator`
    example.
    """

    def validate(self, key, value):  # pylint: disable=C0111
        raise NotImplementedError()

    def populate(self, name):  # pylint: disable=C0111
        return {}

    def raise_error(self, key, value, **kwargs):  # pylint: disable=C0111
        raise e.ValidationError(key, value, self, **kwargs)


class Email(Validator):
    """
    Checks whether an input matches a potential email. Other methods
    should be used for advanced verification. An optional `domain`
    argument can be passed to the constructor, which will check
    whether the email is in the domain.

    :usage:
    @app.route("/")
    @sb.validator({
        "email": sb.v.Email(domain="hashbang.sh"),
    })
    @sb.base
    def index(form):
        if form.is_form_mode():
            do_thing(form)
            return flask.redirect(flask.url_for("index"))
        return flask.render_template("index.html")
    """
    name = "email"

    # Store the domain if one is passed
    def __init__(self, domain=None):
        self._domain = domain

    def populate(self, name):
        return {"domain": self._domain}

    # Check if input data is a semi-valid email matching the domain
    def validate(self, key, value):
        first, _, last = value.rpartition("@")
        if "@" in first or not first or not last:
            self.raise_error(key, value, message="invalid email")
        elif self._domain is not None and last != self._domain:
            self.raise_error(
                key, value,
                message="invalid domain (%r)" % self._domain)


class Exists(Validator):
    """
    Checks whether a value exists or not.

    :usage:
    @app.route("/")
    @sb.validator({
        "username": sb.v.Exists(),
    })
    @sb.validator(sb.v.Exists("username"))
    @sb.base
    def index(form):
        if form.is_form_mode():
            perform_advanced_validation(form["username"])
            do_thing(form)
            return flask.redirect(flask.url_for("index"))
        return flask.render_template("index.html")
    """
    name = "exists"

    # Store the domain if one is passed
    def __init__(self):
        pass

    # Check if the value exists
    def validate(self, key, value):
        pass


class IPAddress(Validator):
    """
    Checks whether an input matches a (default) IPv4 or IPv6 address;
    either IPv4, IPv6, or both can be chosen from. The `address_type`
    field should be assigned to an array containing the strings "ipv4",
    "ipv6", or both depending on which are considered valid.

    Depending on which system you use, IPv4 may or may not be allowed to use
    leading zeroes. Take this into consideration when writing tests.

    :usage:
    @app.route("/")
    @sb.validator({
        "addr": sb.v.IPAddress(),
    })
    @sb.base
    def index(form):
        if form.is_form_mode():
            print(form["addr"])
            return flask.redirect(flask.url_for("index"))
        return flask.render_template_string(
            "Address families: {{ g.addr_validator.address_type }}")
    """
    name = "ipaddress"

    def __init__(self, address_type=["ipv4"]):  # pylint: disable=W0102
        self._type = address_type

    def validate(self, key, value):
        dirty = True
        error = None
        if "ipv4" in self._type:
            try:
                socket.inet_pton(socket.AF_INET, value)
            except socket.error as err:
                error = err
            else:
                dirty = False
        if "ipv6" in self._type:
            try:
                socket.inet_pton(socket.AF_INET6, value)
            except socket.error as err:
                # Will still be "dirty" if IPv4 didn't match, meaning this is
                # also a valid error
                if dirty:
                    error = err
            else:
                dirty = False
        if dirty:
            self.raise_error(key, value, exception=error)

    def populate(self, name):
        return {"type": self._type}


class Length(Validator):
    """
    Checks whether an input has a certain number of characters.

    :usage:
    @app.route("/")
    @sb.validator({
        "username": sb.v.Length(min=6, max=30),
    })
    @sb.base
    def index(form):
        if form.is_form_mode():
            perform_advanced_validation(form["username"])
            do_thing(form)
            return flask.redirect(flask.url_for("index"))
        return flask.render_template("index.html")
    """
    name = "length"

    # Store the domain if one is passed
    def __init__(self, min=None, max=None):
        self._min = min
        self._max = max

    def populate(self, name):
        return {"min": self._min, "max": self._max}

    # Check if input data is a semi-valid email matching the domain
    def validate(self, key, value):
        length = len(value)
        msg = "value too %s (%s %s %s)"
        if self._min is not None:
            if length < self._min:
                self.raise_error(
                    key, value,
                    message=msg % ("short", length, "<", self._min))
        if self._max is not None:
            if length > self._max:
                self.raise_error(
                    key, value,
                    message=msg % ("long", length, ">", self._max))


class Regex(Validator):
    """
    Validate input data based on a raw, uncompiled regex pattern. To match
    an exact string, text should be anchored at the beginning and end by using
    `^` and `$` respectively.

    It is suggested to use the "most common" subset of regex to ensure that
    the framework displaying your views (most likely HTML) can properly use
    the regex.

    :usage:
        @app.route("/")
        @sb.validator({
            "count": sb.v.Regex("[0-9]{1,4}"),
        })
        @sb.base
        def index(form):
            if form.is_form_mode():
                print(form["count"])
                return flask.redirect(flask.url_for("index"))
            return flask.render_template("index.html")
    """
    name = "regex"

    # Compiles and stores a pattern
    def __init__(self, pattern):
        self.pattern = re.compile(pattern)

    def populate(self, name):
        return {"pattern": self.pattern.pattern}

    # Check if input data matches the pattern; otherwise, raise errors
    def validate(self, key, value):
        if not self.pattern.match(value):
            self.raise_error(key, value, message=self.pattern)


class Select(Validator):
    """
    Validate that a given input is a selection of a list of input options.

    :usage:
    @app.route("/")
    @sb.validator({
        "option": sb.v.Select(["apples", "oranges", "bananas"]),
    })
    """
    name = "select"

    def __init__(self, options):
        self._options = set(options)

    def __repr__(self):
        return "%r %r" % (type(self), self._options)

    def populate(self, name):
        return {
            "options": sorted(self._options)
        }

    def validate(self, key, value):
        if value not in self._options:
            self.raise_error(key, value)
