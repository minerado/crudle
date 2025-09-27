import re


def build_tsquery_string(term: str) -> str:
    """
    Formats a string into a tsquery format.

    Example:
        >>> build_tsquery_string("John Doe")
        >>> "John:* & Doe:*"
    """
    # Duplicate single quotes to escape them
    term = term.replace("'", "''")

    # Sanitize term by removing special characters
    term = re.sub(r"[^\w\s]", "", term)

    # Split each word and join them with '&' while adding the prefix search operator ':*'
    return " & ".join([f"{w}:*" for w in term.split()])


def flatten_dict(nested_dict: dict, parent_key="", sep="."):
    """
    Flattens a nested dictionary into a list of tuples with dot-separated keys.

    Args:
        nested_dict (dict): The dictionary to flatten.
        parent_key (str): The base key to use for the flattened keys.
        sep (str): The separator to use between keys.

    Returns:
        list: A list of tuples where each tuple contains a dot-separated key and its corresponding value.
    """
    items = []

    for key, value in nested_dict.items():
        # Construct the new key by appending the current key to the parent key
        new_key = f"{parent_key}{sep}{key}" if parent_key else key

        if isinstance(value, dict):
            # Recursively flatten the nested dictionary
            items.extend(flatten_dict(value, new_key, sep=sep))
        else:
            # Append the key-value pair to the result list
            items.append((new_key, value))

    return items


def filter_none_values(data):
    """
    Filters out None values from a dictionary.

    Args:
        data (dict): The dictionary to filter.

    Returns:
        dict: A dictionary with None values filtered out.
    """
    return {k: v for k, v in data.items() if v is not None}
