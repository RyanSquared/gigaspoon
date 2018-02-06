import spudbucket as sb
import flask
import os

app = flask.Flask(__name__)
app.secret_key = os.urandom(24)


class CustomSelectValidator(sb.v.Validator):
    def __init__(self, name, options):
        self.name = name
        self._options = set(options)

    def __repr__(self):
        return "%r %r" % (type(self), self._options)

    def populate(self):
        return {
            "options": self._options,
            "name": self.name
        }
        return self._options

    def validate(self, form, key, value):
        if value not in self._options:
            self.raise_error(key, value)


users = ["Fred", "George"]
html = """
<!DOCTYPE HTML>
{% for message in get_flashed_messages() -%}
<pre>{{ message }}</pre>
{%- endfor %}
<form method="POST">
    <select required name="{{ g.user_validator.name }}">
        {% for user in g.user_validator.options -%}
        <option value="{{ user }}">{{ user }}</option>
        {%- endfor %}
        <option value="break!">Bad input!</option>
    </select>
    <input type="submit" value="submit">
</form>
"""


@app.route("/", methods=["GET", "POST"])
@sb.set_methods("POST")
@sb.validator(CustomSelectValidator("user", users))
@sb.base
def index(form):
    if form.is_form_mode():
        # Method is POST and form fields are valid
        flask.flash(repr(form))
        return flask.redirect(flask.url_for('index'))
    else:
        return flask.render_template_string(html)


@app.errorhandler(sb.e.FormError)
def handle_form_error(exc):
    return flask.escape(str(exc)), 400


if __name__ == "__main__":
    app.run()
