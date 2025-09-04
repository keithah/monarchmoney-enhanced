"""
Input validation for MonarchMoney Enhanced.

Provides comprehensive validation for user inputs and API parameters.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from .exceptions import ValidationError


class InputValidator:
    """Comprehensive input validator for MonarchMoney operations."""

    @staticmethod
    def validate_email(email: str) -> str:
        """
        Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            Normalized email address

        Raises:
            ValidationError: If email format is invalid
        """
        if not email or not isinstance(email, str):
            raise ValidationError("Email is required and must be a string")

        email = email.strip().lower()

        # Basic email regex validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValidationError(
                "Invalid email format",
                details={"email": email, "expected_format": "user@domain.com"},
            )

        # Check reasonable length limits
        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError("Email address too long (max 254 characters)")

        return email

    @staticmethod
    def validate_password(password: str) -> str:
        """
        Validate password requirements.

        Args:
            password: Password to validate

        Returns:
            Original password if valid

        Raises:
            ValidationError: If password doesn't meet requirements
        """
        if not password or not isinstance(password, str):
            raise ValidationError("Password is required and must be a string")

        # Basic password requirements
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")

        if len(password) > 128:  # Reasonable upper limit
            raise ValidationError("Password too long (max 128 characters)")

        return password

    @staticmethod
    def validate_mfa_code(code: str) -> str:
        """
        Validate MFA code format.

        Args:
            code: MFA code to validate

        Returns:
            Normalized MFA code

        Raises:
            ValidationError: If MFA code format is invalid
        """
        if not code or not isinstance(code, str):
            raise ValidationError("MFA code is required and must be a string")

        # Remove spaces and normalize
        code = re.sub(r"\s+", "", code)

        # MFA codes are typically 6-8 digits
        if not re.match(r"^\d{6,8}$", code):
            raise ValidationError(
                "Invalid MFA code format",
                details={"expected_format": "6-8 digit numeric code"},
            )

        return code

    @staticmethod
    def validate_account_id(account_id: Union[str, int]) -> str:
        """
        Validate account ID.

        Args:
            account_id: Account ID to validate

        Returns:
            Normalized account ID as string

        Raises:
            ValidationError: If account ID is invalid
        """
        if account_id is None:
            raise ValidationError("Account ID is required")

        # Convert to string and validate
        account_id_str = str(account_id).strip()

        if not account_id_str:
            raise ValidationError("Account ID cannot be empty")

        # Account IDs should be reasonable length
        if len(account_id_str) > 100:
            raise ValidationError("Account ID too long")

        return account_id_str

    @staticmethod
    def validate_transaction_id(transaction_id: Union[str, int]) -> str:
        """
        Validate transaction ID.

        Args:
            transaction_id: Transaction ID to validate

        Returns:
            Normalized transaction ID as string

        Raises:
            ValidationError: If transaction ID is invalid
        """
        if transaction_id is None:
            raise ValidationError("Transaction ID is required")

        # Convert to string and validate
        transaction_id_str = str(transaction_id).strip()

        if not transaction_id_str:
            raise ValidationError("Transaction ID cannot be empty")

        if len(transaction_id_str) > 100:
            raise ValidationError("Transaction ID too long")

        return transaction_id_str

    @staticmethod
    def validate_amount(amount: Union[str, int, float]) -> float:
        """
        Validate monetary amount.

        Args:
            amount: Amount to validate

        Returns:
            Validated amount as float

        Raises:
            ValidationError: If amount is invalid
        """
        if amount is None:
            raise ValidationError("Amount is required")

        try:
            amount_float = float(amount)
        except (ValueError, TypeError):
            raise ValidationError(
                "Invalid amount format",
                details={"provided": amount, "type": type(amount)},
            )

        # Check for reasonable limits (adjust as needed)
        if abs(amount_float) > 999999999.99:  # 999 million
            raise ValidationError("Amount exceeds maximum limit")

        return round(amount_float, 2)  # Round to 2 decimal places

    @staticmethod
    def validate_date_string(date_str: str) -> str:
        """
        Validate date string format.

        Args:
            date_str: Date string to validate (YYYY-MM-DD)

        Returns:
            Validated date string

        Raises:
            ValidationError: If date format is invalid
        """
        if not date_str or not isinstance(date_str, str):
            raise ValidationError("Date is required and must be a string")

        # Validate YYYY-MM-DD format
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(date_pattern, date_str):
            raise ValidationError(
                "Invalid date format",
                details={"provided": date_str, "expected_format": "YYYY-MM-DD"},
            )

        # Additional validation could include checking if date is valid
        try:
            from datetime import datetime

            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValidationError(
                "Invalid date", details={"provided": date_str, "format": "YYYY-MM-DD"}
            )

        return date_str

    @staticmethod
    def validate_limit(limit: Union[str, int, None]) -> Optional[int]:
        """
        Validate record limit parameter.

        Args:
            limit: Record limit to validate

        Returns:
            Validated limit as int or None

        Raises:
            ValidationError: If limit is invalid
        """
        if limit is None:
            return None

        try:
            limit_int = int(limit)
        except (ValueError, TypeError):
            raise ValidationError(
                "Invalid limit format", details={"provided": limit, "type": type(limit)}
            )

        if limit_int <= 0:
            raise ValidationError("Limit must be positive")

        if limit_int > 10000:  # Reasonable upper bound
            raise ValidationError("Limit too large (max 10,000)")

        return limit_int

    @staticmethod
    def validate_string_length(
        value: str, field_name: str, min_length: int = 0, max_length: int = 1000
    ) -> str:
        """
        Validate string length.

        Args:
            value: String to validate
            field_name: Name of the field for error messages
            min_length: Minimum allowed length
            max_length: Maximum allowed length

        Returns:
            Validated string

        Raises:
            ValidationError: If string length is invalid
        """
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        if len(value) < min_length:
            raise ValidationError(
                f"{field_name} too short (minimum {min_length} characters)"
            )

        if len(value) > max_length:
            raise ValidationError(
                f"{field_name} too long (maximum {max_length} characters)"
            )

        return value

    @staticmethod
    def validate_graphql_variables(variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate GraphQL variables for injection attacks.

        Args:
            variables: GraphQL variables dictionary

        Returns:
            Validated variables

        Raises:
            ValidationError: If variables contain suspicious content
        """
        if not isinstance(variables, dict):
            raise ValidationError("GraphQL variables must be a dictionary")

        # Check for suspicious patterns that might indicate injection attempts
        suspicious_patterns = [
            r"__typename",
            r"fragment",
            r"mutation\s*{",
            r"query\s*{",
            r"subscription\s*{",
        ]

        def check_value(value: Any, path: str = "") -> None:
            if isinstance(value, str):
                for pattern in suspicious_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        raise ValidationError(
                            f"Suspicious content detected in GraphQL variables",
                            details={"path": path, "pattern": pattern},
                        )
            elif isinstance(value, dict):
                for key, val in value.items():
                    check_value(val, f"{path}.{key}" if path else key)
            elif isinstance(value, list):
                for i, val in enumerate(value):
                    check_value(val, f"{path}[{i}]" if path else f"[{i}]")

        check_value(variables)
        return variables


# Convenience functions for common validations
def validate_login_credentials(email: str, password: str) -> Tuple[str, str]:
    """
    Validate login credentials.

    Args:
        email: Email address
        password: Password

    Returns:
        Tuple of (normalized_email, password)

    Raises:
        ValidationError: If credentials are invalid
    """
    validated_email = InputValidator.validate_email(email)
    validated_password = InputValidator.validate_password(password)
    return validated_email, validated_password


def validate_mfa_credentials(
    email: str, password: str, code: str
) -> Tuple[str, str, str]:
    """
    Validate MFA credentials.

    Args:
        email: Email address
        password: Password
        code: MFA code

    Returns:
        Tuple of (normalized_email, password, normalized_code)

    Raises:
        ValidationError: If credentials are invalid
    """
    validated_email = InputValidator.validate_email(email)
    validated_password = InputValidator.validate_password(password)
    validated_code = InputValidator.validate_mfa_code(code)
    return validated_email, validated_password, validated_code
