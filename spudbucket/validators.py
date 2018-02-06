import re
from . import errors as e


class Validator(object):
    def __init__(self):
        raise NotImplementedError()

    def validate(self, form, value):
        raise NotImplementedError()

    def populate(self):
        pass

    def raise_error(self, key, value):
        raise e.ValidationError(key, value, self)


class RegexValidator(Validator):
    def __init__(self, name, pattern):
        self.name = name
        self._pattern = re.compile(pattern)

    def __repr__(self):
        return "%r <%r>" % (type(self), self._pattern.pattern)

    def validate(self, form, key, value):
        if not self._pattern.match(value):
            self.raise_error(key, value)
