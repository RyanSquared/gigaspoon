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
