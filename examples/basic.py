import spudbucket as sb
import flask

app = flask.Flask(__name__)


@app.route("/", methods=["GET", "POST"])
@sb.set_methods("POST")
@sb.validator(sb.v.RegexValidator("new", "hi"))
@sb.validator(sb.v.RegexValidator("asdf", "[A-Za-z]+"))
@sb.base
def index(form):
    if form.is_form_mode():
        # Method is POST and form fields are valid
        return repr(form)
    else:
        return "hi!"
        # return flask.render_template("index.html")


@app.errorhandler(sb.e.FormError)
def handle_form_error(exc):
    return str(exc), 400


if __name__ == "__main__":
    app.run()
