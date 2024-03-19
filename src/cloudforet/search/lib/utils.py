def save_to_dict_value(
    data: dict,
    dotted_key: str,
    value: any,
    default_value: any = None,
    overwrite: bool = False,
) -> dict:
    if "." in dotted_key:
        key, rest_dotted_key = dotted_key.split(".", 1)
        print("key, rest_dotted_key", key, rest_dotted_key)
        if key not in data:
            data[key] = {}

        if len(rest_dotted_key) > 0:
            print("nested")
            save_to_dict_value(data[key], rest_dotted_key, value, default_value)
    else:
        if dotted_key not in data or overwrite is True:
            data[dotted_key] = value
            print("not dotted", data, dotted_key, value)

    return data
