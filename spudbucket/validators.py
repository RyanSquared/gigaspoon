"""
This module provides utility validators to avoid rewriting validators that
are not usecase specific.
"""
import base64
import os
import re
import socket

import flask

from . import errors as e


class Validator(object):
    """
    Base class for all Validator objects. Your Validator must extend off
    this class or the handler will raise an assertion error. Usage of how
    to extend off this class is demonstrated in the `custom-validator`
    example.
    """

    def validate(self, form, key, value):  # pylint: disable=C0111
        raise NotImplementedError()

    def populate(self):  # pylint: disable=C0111
        pass

    def raise_error(self, key, value, **kwargs):  # pylint: disable=C0111
        raise e.ValidationError(key, value, self, **kwargs)


class CSRF(Validator):
    """
    Create a CSRF token and ensure that the token exists (and matches that
    of the form) when serving and processing forms.

    :usage:
        @app.route("/")
        @sb.validator(sb.v.CSRF())
        def index():
            # Your code here
            pass
    """

    def __init__(self, name="csrf_token"):
        self.name = name

    # Generate a CSRF token from random bytes, and store in a session
    def populate(self):
        if flask.session.get("_csrf_token") is None:
            token = base64.b64encode(os.urandom(24))
            flask.session["_csrf_token"] = token.decode('ascii')
        return {
            "name": self.name,
            "csrf_token": flask.session["_csrf_token"],
            "csrf_tag": '<input type="hidden" name="%s" value="%s" />' % (
                self.name, flask.session["_csrf_token"])
        }

    # Verify that the CSRF token passed is the same as in the session
    def validate(self, form, key, value):
        token = flask.session.get("_csrf_token")
        if token is None:
            raise e.InvalidSessionError()
        elif value != token:
            self.raise_error(key, value)


class Email(Validator):
    """
    Checks whether an input matches a potential email. Other methods
    should be used for advanced verification. An optional `domain`
    argument can be passed to the constructor, which will check
    whether the email is in the domain.

    :usage:
    @app.route("/")
    @sb.validator(sb.v.Email("email", domain="hashbang.sh"))
    @sb.base
    def index(form):
        if form.is_form_mode():
            perform_advanced_validation(form["email"])
            do_thing(form)
            return flask.redirect(flask.url_for("index"))
        return flask.render_template("index.html")
    """

    # Store the domain if one is passed
    def __init__(self, name, domain=None):
        self.name = name
        self._domain = domain

    def populate(self):
        return {"domain": self._domain}

    # Check if input data is a semi-valid email matching the domain
    def validate(self, form, key, value):
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
    @sb.validator(sb.v.Exists("username"))
    @sb.base
    def index(form):
        if form.is_form_mode():
            perform_advanced_validation(form["username"])
            do_thing(form)
            return flask.redirect(flask.url_for("index"))
        return flask.render_template("index.html")
    """

    # Store the domain if one is passed
    def __init__(self, name):
        self.name = name

    # Check if the value exists
    def validate(self, form, key, value):
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
    @sb.validator(sb.v.IPAddress("addr"))
    @sb.base
    def index(form):
        if form.is_form_mode():
            print(form["addr"])
            return flask.redirect(flask.url_for("index"))
        return flask.render_template_string(
            "Address families: {{ g.addr_validator.address_type }}")
    """

    def __init__(self, name, address_type=["ipv4"]):  # pylint: disable=W0102
        self.name = name
        self._type = address_type

    def validate(self, form, key, value):
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

    def populate(self):
        return {"address_type": self._type}


class Length(Validator):
    """
    Checks whether an input has a certain number of characters.

    :usage:
    @app.route("/")
    @sb.validator(sb.v.Length("username", min=6, max=30))
    @sb.base
    def index(form):
        if form.is_form_mode():
            perform_advanced_validation(form["username"])
            do_thing(form)
            return flask.redirect(flask.url_for("index"))
        return flask.render_template("index.html")
    """

    # Store the domain if one is passed
    def __init__(self, name, min=None, max=None):
        self.name = name
        self._min = min
        self._max = max

    def populate(self):
        return {"min": self._min, "max": self._max}

    # Check if input data is a semi-valid email matching the domain
    def validate(self, form, key, value):
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
        @sb.validator(sb.v.Regex("count", "[0-9]{1,4}"))
        @sb.base
        def index(form):
            if form.is_form_mode():
                print(form["count"])
                return flask.redirect(flask.url_for("index"))
            return flask.render_template("index.html")
    """

    # Compiles and stores a pattern
    def __init__(self, name, pattern):
        self.name = name
        self.pattern = re.compile(pattern)

    def populate(self):
        return {"pattern": self.pattern.pattern}

    # Check if input data matches the pattern; otherwise, raise errors
    def validate(self, form, key, value):
        if not self.pattern.match(value):
            self.raise_error(key, value, message=self.pattern)


class Select(Validator):
    def __init__(self, name, options):
        self.name = name
        self._options = set(options)

    def __repr__(self):
        return "%r %r" % (type(self), self._options)

    def populate(self):
        return {
            "options": sorted(self._options),
            "name": self.name
        }

    def validate(self, form, key, value):
        if value not in self._options:
            self.raise_error(key, value)
