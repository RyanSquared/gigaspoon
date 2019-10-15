def sanitize(validator_name: str, fields: dict) -> dict:
    return {f"{validator_name}_{k}": v for k, v in fields.items()}
