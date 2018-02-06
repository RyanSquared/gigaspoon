class FormError(Exception):
    pass


class FormKeyError(FormError):
    def __init__(self, key, form):
        self._key = key
        self._form = form

    def __str__(self):
        return "Expected key %r for form %r" % (self._key, self._form)


class ValidationError(FormError):
    def __init__(self, key, value, validator):
        self._key = key
        self._value = value
        self._validator = validator

    def __str__(self):
        return "%r: %r failed test for %r" % (
            self._key, self._value, self._validator)


class InvalidSessionError(FormError):
    """
    This could be useful for if a session times out in the middle of
    something. An error handler could be caught and automatically redirect
    users to a login page if an invalid session is detected. This is an
    empty container error with no functionality.
    """

    def __str__(self):
        return "Invalid or missing Flask session for request"
