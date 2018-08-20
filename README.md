# Spud Bucket - A library for handling Flask forms.
[![Build Status](https://travis-ci.org/RyanSquared/spudbucket.svg?branch=master)](https://travis-ci.org/RyanSquared/spudbucket) [![License](https://img.shields.io/github/license/RyanSquared/spudbucket.svg?maxAge=2592000)](https://github.com/RyanSquared/spudbucket/blob/master/LICENSE.md) ![Fanciness](https://img.shields.io/badge/fancy-totally-brightgreen.svg)

This is a super simple library I wrote to help handle validating Flask forms.
It's currently very unstable so I wouldn't recommend using it as things can and
probably will change over time.

This framework is designed to assist with **validating** input, while also
offering options to help with creating forms. Unlike other frameworks, the
priority is towards validation, leaving the creation and design of forms to
the developer.

## Why?

I like to think WTForms is appropriately named, because every time I hear
someone speaking about it, I always hear one thing - "WTF???". It feels like
a complicated library for something that should be super simple, and I hope
that with Spud Bucket, I'm able to make it as simple as possible for people to
validate their forms. In the future, there might also be some helpful utilities
set in `flask.g` to help with autogenerating forms based on values from a
`select`, setting types, etc. that can be used in Jinja2 templates (but will
not be required).

Spud Bucket is less "featureful" than other form-creation frameworks, so that
the developers can have more power over the forms. Instead of automatically
generating tags to be output, the framework urges you to write your own
templates, assisted by the framework.

## How?

It's actually super simple and relies on decorator functions to handle
everything. Here's an example:

```py
import spudbucket as sb
import flask

app = flask.Flask(__name__)


@app.route("/", methods=["GET", "POST"])
@sb.set_methods("POST")
@sb.validator(sb.v.Regex("new", "hi"))
@sb.validator(sb.v.Regex("asdf", "[A-Za-z]+"))
@sb.base
def index(form):
    if form.is_form_mode():
        # Method is POST and form fields are valid
        print(form["asdf"])
        print(form["new"])
        return "hello!"
    else:
        return "hi!"
        # return flask.render_template("index.html")


@app.errorhandler(sb.e.FormError)
def handle_form_error(exc):
    return str(exc), 400


app.run()
```

Let's walk through the decorator "chain".

**`@sb.set_methods("POST")`** - This method ensures that forms will only be
validated on `POST` requests. This function can take any amount of arguments
and will check through all of them every request.

<!-- ::TODO:: make `validator` store name, not `Regex` -->

**`@sb.validator(sb.v.Regex("new", "hi"))`** - This method is our
first validator. It checks for the key `new` on the inconing Flask form,
assuming the current Flask request matches the `set_methods()` (defaulting to
"POST" if the decorator wasn't called), then checks whether the incoming
value matches the pattern.

**`@sb.base`** - This is a simple decorator provided as a convenience, which
ensures that the first value for the called function is the incoming form,
which can instead be accessed using `flask.g.form`.

**`form.is_form_mode()`** - Check if the incoming request matches the set
methods. If it does, a value `True` is returned, otherwise `False`.

## Installation

Currently, spudbucket relies on no external dependencies other than Flask.
It can be installed from source using `pip install --user .`. If you'd like to
install a specific version (for example, version 0.1.0), checkout the Git tag
and run pip from there:

```sh
git checkout v0.1.0
pip install --user .
```

## Notes

Forms will be validated regardless of whether or not you use the values; the
only thing that determines whether they're validated is whether or not they
match the `set_methods()` value. This could change in the future by passing a
"check" function to `sb.validator()` which determines whether or not the value
will be used.
