import gigaspoon as gs
import flask

app = flask.Flask(__name__)

# How to Use:
#
# `curl -F example=helloworld localhost:5000`
# `curl -F example=bad1input localhost:5000`
# `curl localhost:5000`


@app.route("/", methods=["GET", "POST"])
@gs.set_methods("POST")
@gs.validator(gs.v.Regex("example", "[A-Za-z]+"))
@gs.base
def index(form):
    if form.is_form_mode():
        # Method is POST and form fields are valid
        return repr(form)
    else:
        return 'hi!'


@app.errorhandler(gs.e.FormError)
def handle_form_error(exc):
    return str(exc), 400


if __name__ == "__main__":
    app.run()
