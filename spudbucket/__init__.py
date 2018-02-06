import functools
import flask
from . import validators as v
from . import errors as e


class Form(dict):
    # Create a Form, triggered "on" when the Flask request is in `methods`
    def __init__(self, methods):
        super(Form, self).__init__()
        self._methods = methods

    # Check if the current Flask request is in the set_methods() values
    def is_form_mode(self):
        if flask.request.method in self._methods:
            return True
        return False


# Check or preload a form into a Flask session.
def get_form(methods=("POST",)):
    try:
        form = flask.g.form
    except AttributeError:
        form = Form(methods=methods)
        flask.g.form = form
    return form


# Prototype decorator for validating incoming requests
def validator_prototype(func, validator_instance, *args, **kwargs):
    assert isinstance(validator_instance, v.Validator)
    name = validator_instance.name

    @functools.wraps(func)
    def handle_func(*args, **kwargs):
        form = get_form()
        if form.is_form_mode():
            r_form = flask.request.form
            if r_form.get(name) is None:
                raise e.FormKeyError(name, r_form)
            item = r_form.get(name)
            validator_instance.validate(form, name, item)
            form[name] = item
        return func(*args, **kwargs)
    return handle_func


# Decorator factory
def validator(validator_instance):
    return functools.partial(
        validator_prototype, validator_instance=validator_instance)


# Prototype decorator for validating a form on certain HTTP methods
def set_methods_prototype(func, methods):
    @functools.wraps(func)
    def setup_methods(*args, **kwargs):
        get_form(methods)
        return func(*args, **kwargs)
    return setup_methods


# Decorator factory
def set_methods(*methods):
    return functools.partial(set_methods_prototype, methods=methods)


# Decorator for passing a form to the view function
def base(func):
    @functools.wraps(func)
    def setup_form(*args, **kwargs):
        return func(get_form(), *args, **kwargs)
    return setup_form
