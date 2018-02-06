import base64
import os
import re

import flask

from . import errors as e


class Validator(object):
    """
    Base class for all Validator objects. Your Validator must extend off
    this class or the handler will raise an assertion error. Usage of how
    to extend off this class is demonstrated in the `custom-validator`
    example.
    """

    def __init__(self):
        raise NotImplementedError()

    def validate(self, form, value):
        raise NotImplementedError()

    def populate(self):
        pass

    def raise_error(self, key, value):
        raise e.ValidationError(key, value, self)


class RegexValidator(Validator):
    """
    Validate input data based on a raw, uncompiled regex pattern. To match
    an exact string, text should be anchored at the end using `$`.

    :usage:
        @app.route("/")
        @sb.validator(sb.v.RegexValidator("count", "[0-9]{1,4}"))
        @sb.base
        def index(form):
            if form.is_form_mode():
                print(form["count"])
                return flask.redirect(flask.url_for("index"))
            else
                return flask.render_template("index.html")
    """

    # Compiles and stores a pattern
    def __init__(self, name, pattern):
        self.name = name
        self._pattern = re.compile(pattern)

    def __repr__(self):
        return "%r <%r>" % (type(self), self._pattern.pattern)

    # Check if input data matches the pattern; otherwise, raise errors
    def validate(self, form, key, value):
        if not self._pattern.match(value):
            self.raise_error(key, value)


class CSRFValidator(Validator):
    """
    Create a CSRF token and ensure that the token exists (and matches that
    of the form) when serving and processing forms.

    :usage:
        @app.route("/")
        @sb.validator(sb.v.CSRFValidator())
        def index():
            # Your code here
            pass
    """

    def __init__(self, name="csrf_token"):
        self.name = name

    # Generate a CSRF token from random bytes, and store in a session
    def populate(self):
        if flask.session.get("_csrf_token") is None:
            package = os.urandom(24)
            flask.session["_csrf_token"] = str(base64.b64encode(package))
        return {
            "name": self.name,
            "csrf_token": flask.session["_csrf_token"]
        }

    # Verify that the CSRF token passed is the same as in the session
    def validate(self, form, key, value):
        token = flask.session.get("_csrf_token")
        if token is None:
            raise e.InvalidSessionError()
        elif value != token:
            self.raise_error(key, value)
