from typing import List, Callable
from collections.abc import Iterable

import base64
import os
import functools

import flask

from .. import validators as v
from .. import errors as e
from .. import u


class Form(dict):
    """Dictionary with extra utilities for checking Flask form status

    :usage:
        form = Form("POST", "PUT")
        form["hello"] = "example message"
        if form.is_form():
            print(form["hello"])
        else:
            print("Use a POST or PUT request!")
    """

    # Create a Form, triggered "on" when Flask request is in `methods`
    def __init__(self, methods: List[str]):
        super(Form, self).__init__()
        self._methods = methods

    # Check if the current Flask request is in the set_methods() values
    def is_form(self):
        if flask.request.method in self._methods:
            return True
        return False


# Check or preload a form into a Flask request variable
def get_form(methods: List[str] = ["POST"]):
    try:
        form = flask.g.form
    except AttributeError:
        form = Form(methods=methods)
        flask.g.form = form
    return form


# Prototype decorator for validating incoming requests
def _validator_prototype(func: Callable, validators, *args, **kwargs):
    for name, validator_list in validators.items():
        if not isinstance(validator_list, Iterable):
            validator_list = [validator_list]
            validators[name] = validator_list
        for validator in validator_list:
            assert isinstance(validator, v.Validator)

    @functools.wraps(func)
    def handle_func(*args, **kwargs):
        form = get_form()
        if form.is_form():
            request_form = flask.request.form

            # Iterate through all fields
            for name, validator_list in validators.items():

                # Locate item in either form or JSON
                item = request_form.get(name)
                if item is None:
                    json = flask.request.json
                    if json is None or json.get(name) is None:
                        raise e.FormKeyError(name, request_form)
                    item = json[name]

                if not isinstance(validator_list, Iterable):
                    validator_list = [validator_list]

                # Iterate through all validators
                for validator in validator_list:
                    # Check to make sure input is valid
                    validator.validate(form, name, item)

                # Data is valid, can put into our local form
                form[name] = item
        else:
            for name, validator_list in validators.items():
                for validator in validator_list:
                    if hasattr(validator, "populate"):
                        # Populate flask.g.[{name}_validator] with values
                        populated_name = f"{name}_validator"
                        values = getattr(flask.g, populated_name, {})
                        values.update(u.sanitize(validator.name,
                                                 validator.populate(name)))
                        setattr(flask.g, populated_name, values)
                        # Data is now accessible under something akin to:
                        # flask.g.email_validator["email_domain"]
        return func(*args, **kwargs)
    return handle_func


# Validate incoming Flask requests using a Validator
def validator(validators):
    """
    Validate incoming Flask requests using a Validator.

    :usage:
        @app.route("/")
        @sb.flask_validator({
            "csrf": [sb.v.CSRF()],
            "email": [sb.v.Email(domain="hashbang.sh")],
        })
        def index():
            # Your code here
            pass
    """
    return functools.partial(
        _validator_prototype, validators=validators)


# Prototype decorator for validating a form on certain HTTP methods
def _set_methods_prototype(func, methods):
    @functools.wraps(func)
    def setup_methods(*args, **kwargs):
        get_form(methods)
        return func(*args, **kwargs)
    return setup_methods


# Set the HTTP methods that will trigger validation
def set_methods(*methods):
    return functools.partial(_set_methods_prototype, methods=methods)


# Automatically pass a `form` to the decorated function
def base(func):
    @functools.wraps(func)
    def setup_form(*args, **kwargs):
        return func(get_form(), *args, **kwargs)
    return setup_form


class CSRF(v.Validator):
    """
    Create a CSRF token and ensure that the token exists (and matches that
    of the form) when serving and processing forms.

    Only usable with the Flask engine.

    :usage:
        @app.route("/")
        @sb.validator({
            "csrf": sb.CSRF(),
        })
        def index():
            # Your code here
            pass
    """

    name = "csrf"

    def __init__(self):
        pass

    # Generate a CSRF token from random bytes, and store in a session
    def populate(self, name):
        if flask.session.get("_csrf_token") is None:
            token = base64.b64encode(os.urandom(24))
            flask.session["_csrf_token"] = token.decode('utf8')
        return {
            "name": name,
            "token": flask.session["_csrf_token"],
            "tag": '<input type="hidden" name="%s" value="%s" />' % (
                name, flask.session["_csrf_token"])
        }

    # Verify that the CSRF token passed is the same as in the session
    def validate(self, form, key, value):
        token = flask.session.get("_csrf_token")
        if token is None:
            raise e.InvalidSessionError()
        elif value != token:
            self.raise_error(key, value)
