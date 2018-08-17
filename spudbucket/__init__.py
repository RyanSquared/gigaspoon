import functools
import flask
from . import validators as v
from . import errors as e


class Form(dict):
    """Dictionary with extra utilities for checking Flask form status

    :usage:
        form = Form("POST", "PUT")
        form["hello"] = "example message"
        if form.is_form_mode():
            print(form["hello"])
        else:
            print("Use a POST or PUT request!")
    """

    # Create a Form, triggered "on" when Flask request is in `methods`
    def __init__(self, methods):
        super(Form, self).__init__()
        self._methods = methods

    # Check if the current Flask request is in the set_methods() values
    def is_form_mode(self):
        if flask.request.method in self._methods:
            return True
        return False


# Check or preload a form into a Flask request variable
def get_form(methods=("POST",)):
    try:
        form = flask.g.form
    except AttributeError:
        form = Form(methods=methods)
        flask.g.form = form
    return form


# Prototype decorator for validating incoming requests
def _validator_prototype(func, validator_instance, *args, **kwargs):
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
        if hasattr(validator_instance, "populate"):
            data_name = name + "_validator"
            setattr(flask.g, data_name, validator_instance.populate())
        return func(*args, **kwargs)
    return handle_func


# Validate incoming Flask requests using a Validator
def validator(validator_instance):
    """
    Validate incoming Flask requests using a Validator.

    :usage:
        @app.route("/")
        @sb.validator(sb.v.CSRFValidator())
        def index():
            # Your code here
            pass
    """
    return functools.partial(
        _validator_prototype, validator_instance=validator_instance)


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
        form = get_form()
        form.update(flask.request.form)
        return func(form, *args, **kwargs)
    return setup_form
