"""
Utility functions for MonarchMoney Enhanced.

Common utilities used across the codebase.
"""

from typing import Any, Dict, Optional, TypeVar, Union

T = TypeVar('T')


def safe_get(data: Dict[str, Any], key: str, default: T = None) -> Union[Any, T]:
    """
    Safely get a value from a dictionary with optional default.

    Args:
        data: Dictionary to get value from
        key: Key to look for
        default: Default value if key not found

    Returns:
        Value from dictionary or default
    """
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def normalize_amount(amount: Union[str, int, float]) -> float:
    """
    Normalize monetary amount to float with 2 decimal places.

    Args:
        amount: Amount to normalize

    Returns:
        Normalized amount as float

    Raises:
        ValueError: If amount cannot be converted to float
    """
    try:
        return round(float(amount), 2)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert amount to float: {amount}") from e


def format_date_for_api(date_obj: Any) -> Optional[str]:
    """
    Format date object to API-compatible string format (YYYY-MM-DD).

    Args:
        date_obj: Date object (datetime, date, or string)

    Returns:
        Formatted date string or None if invalid
    """
    if date_obj is None:
        return None

    if isinstance(date_obj, str):
        return date_obj  # Assume already formatted

    try:
        return date_obj.strftime("%Y-%m-%d")
    except AttributeError:
        return None


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to specified length with optional suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if not isinstance(text, str):
        return str(text)

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def flatten_dict(data: Dict[str, Any], prefix: str = "", separator: str = ".") -> Dict[str, Any]:
    """
    Flatten nested dictionary structure.

    Args:
        data: Dictionary to flatten
        prefix: Prefix for keys
        separator: Separator for nested keys

    Returns:
        Flattened dictionary
    """
    result = {}

    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key

        if isinstance(value, dict):
            result.update(flatten_dict(value, new_key, separator))
        else:
            result[new_key] = value

    return result


def batch_items(items: list, batch_size: int):
    """
    Yield batches of items from a list.

    Args:
        items: List of items to batch
        batch_size: Size of each batch

    Yields:
        Batches of items
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]