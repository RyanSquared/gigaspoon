from collections.abc import Iterable


def sanitize(validator_name: str, fields: dict) -> dict:
    return {f"{validator_name}_{k}": v for k, v in fields.items()}


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
