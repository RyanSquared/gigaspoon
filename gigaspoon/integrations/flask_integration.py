from typing import List, Callable
from collections.abc import Iterable

import base64
import os
import functools

import flask

from .. import validators as v
from .. import errors as e
from .. import u


def process_flat_form(input_form):
    """
    Function adapted from https://github.com/marrow/WebCore

    Copyright © 2006-2019 Alice Bevan-McGregor and contributors.

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the “Software”),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL
    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

    Apply a flat namespace transformation to recreate (in some respects) a
    rich structure.

    This applies several transformations, which may be nested:

    `foo` (singular): define a simple value named `foo`
    `foo` (repeated): define a simple value for placement in an array named
                      `foo`
    `foo[]`: define a simple value for placement in an array, even if there is
             only one
    `foo.<id>`: define a simple value to place in the `foo` array at the
                identified index

    By nesting, you may define deeper, more complex structures:

    `foo.bar`: define a value for the named element `bar` of the `foo` dict
    `foo.<id>.bar`: define a `bar` dictionary element on the array element
                    marked by that ID

    References to `<id>` represent numeric "attributes", which makes the parent
    reference be treated as an array, not a dictionary. Exact indexes might not
    be able to be preserved if there are voids; Python lists are not sparse.

    No validation of values is performed.
    """

    ordered_arrays = []
    output = {}

    # Process arguments one at a time and apply them to the output passed in.

    for name, value in input_form.items():
        container = output

        if '.' in name:
            parts = name.split('.')
            name = name.rpartition('.')[2]

            for target, following in zip(parts[:-1], parts[1:]):
                if following.isnumeric():  # Prepare any use of numeric IDs.
                    container.setdefault(target, [{}])
                    if container[target] not in ordered_arrays:
                        ordered_arrays.append(container[target])
                    container = container[target][0]
                    continue

                container = container.setdefault(target, {})

        if name.endswith('[]'):  # `foo[]` or `foo.bar[]` etc.
            name = name[:-2]
            container.setdefault(name, [])
            container[name].append(value)
            continue

        # trailing identifiers, `foo.<id>`
        if name.isnumeric() and container is not output:
            container[int(name)] = value
            continue

        if name in container:
            if not isinstance(container[name], list):
                container[name] = [container[name]]

            container[name].append(value)
            continue

        container[name] = value

    for container in ordered_arrays:
        elements = container[0]
        del container[:]
        container.extend(value for name, value in sorted(elements.items()))

    return output


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


def validate_item(validator_list, name, item):
    """
    Validate an item across a set of validators. A name should be passed
    through representing the entire search path of the object, to make
    debugging client issues easier. For example, a value of "y" in a dict "x"
    should have a name value of "x.y".
    """
    if not isinstance(validator_list, Iterable):
        validator_list = [validator_list]

    # Iterate through all validators
    for validator in validator_list:
        # Check to make sure input is valid
        opt_value = validator.validate(name, item)
        if opt_value is not None:
            item = opt_value

    return item


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
            request_form = process_flat_form(flask.request.form)

            # Iterate through all fields
            for name, validator_list in validators.items():

                # Locate item in either form or JSON
                item = request_form.get(name)
                if item is None:
                    json = flask.request.json
                    if json is None or json.get(name) is None:
                        raise e.FormKeyError(name, request_form)
                    item = json[name]

                # Data is valid, can put into our local form
                form[name] = validate_item(validator_list, name, item)
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


# Errors


class InvalidSessionError(e.FormError):
    """
    This could be useful for if a session times out in the middle of
    something. An error handler could be caught and automatically redirect
    users to a login page if an invalid session is detected. This is an
    empty container error with no functionality.
    """

    def __str__(self):
        return "Invalid or missing Flask session for request"


# Validators


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
    def validate(self, key, value):
        token = flask.session.get("_csrf_token")
        if token is None:
            raise InvalidSessionError()
        elif value != token:
            self.raise_error(key, value)
