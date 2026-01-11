"""
Simple decimal math library for handling penny math with configurable decimal precision.
Pure string conversion - no external libraries, no Decimal objects.
All operations work with strings and convert to integers internally for calculations.
"""

import re
from typing import List, Union
from hh.gateway.error.error_store import report_error


class DecimalMath:
    """
    Simple decimal math operations with configurable precision.
    All values are stored and manipulated as strings to avoid floating point errors.
    Uses pure string-to-integer conversion without any external libraries.
    """

    # Default decimal places for penny math
    DEFAULT_DECIMAL_PLACES = 2

    @staticmethod
    def _string_to_units(value: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> int:
        """Convert string currency value to integer units using pure string operations."""
        if not value or value == '':
            return 0

        # Remove any existing formatting (commas, currency symbols, etc.)
        clean_value = re.sub(r'[^\d.-]', '', value)

        # Handle negative numbers
        is_negative = clean_value.startswith('-')
        if is_negative:
            clean_value = clean_value[1:]

        # Split into integer and decimal parts
        if '.' in clean_value:
            integer_part, decimal_part = clean_value.split('.', 1)
            # Truncate or pad decimal part to required precision
            decimal_part = decimal_part[:decimal_places].ljust(decimal_places, '0')
        else:
            integer_part = clean_value
            decimal_part = '0' * decimal_places

        # Combine into units string
        units_str = integer_part + decimal_part

        # Convert to integer
        units = int(units_str)

        return -units if is_negative else units

    @staticmethod
    def _units_to_string(units: int, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Convert integer units back to string representation using pure string operations."""
        if units == 0:
            return ''

        # Handle negative
        is_negative = units < 0
        abs_units = abs(units)

        # Convert to string
        units_str = str(abs_units)

        # Pad with leading zeros if necessary
        units_str = units_str.zfill(decimal_places + 1)

        # Split into integer and decimal parts
        integer_part = units_str[:-decimal_places]
        decimal_part = units_str[-decimal_places:]

        # Remove leading zeros from integer part
        integer_part = integer_part.lstrip('0')
        if not integer_part:
            integer_part = '0'

        # Remove trailing zeros from decimal part
        decimal_part = decimal_part.rstrip('0')

        # Format result
        if decimal_part:
            result = f"{integer_part}.{decimal_part}"
        else:
            result = integer_part

        return f"-{result}" if is_negative else result

    @staticmethod
    def add(value1: str, value2: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Add two decimal values."""
        units1 = DecimalMath._string_to_units(value1, decimal_places)
        units2 = DecimalMath._string_to_units(value2, decimal_places)
        result_units = units1 + units2
        return DecimalMath._units_to_string(result_units, decimal_places)

    @staticmethod
    def subtract(value1: str, value2: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Subtract value2 from value1."""
        units1 = DecimalMath._string_to_units(value1, decimal_places)
        units2 = DecimalMath._string_to_units(value2, decimal_places)
        result_units = units1 - units2
        return DecimalMath._units_to_string(result_units, decimal_places)

    @staticmethod
    def multiply(value: str, multiplier: Union[int, str], decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Multiply decimal value by an integer or decimal multiplier."""
        units = DecimalMath._string_to_units(value, decimal_places)

        if isinstance(multiplier, str):
            multiplier_units = DecimalMath._string_to_units(multiplier, decimal_places)
            result_units = units * multiplier_units // (10 ** decimal_places)
        else:
            result_units = units * multiplier

        return DecimalMath._units_to_string(result_units, decimal_places)

    @staticmethod
    def divide(dividend: str, divisor: Union[int, str], decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Divide decimal value by an integer or decimal divisor."""
        dividend_units = DecimalMath._string_to_units(dividend, decimal_places)

        if isinstance(divisor, str):
            divisor_units = DecimalMath._string_to_units(divisor, decimal_places)
            if divisor_units == 0:
                raise ValueError("Division by zero")
            result_units = (dividend_units * (10 ** decimal_places)) // divisor_units
        else:
            if divisor == 0:
                raise ValueError("Division by zero")
            result_units = dividend_units // divisor

        return DecimalMath._units_to_string(result_units, decimal_places)

    @staticmethod
    def sum(values: List[str], decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Sum a list of decimal values."""
        total_units = 0
        for value in values:
            total_units += DecimalMath._string_to_units(value, decimal_places)
        return DecimalMath._units_to_string(total_units, decimal_places)

    @staticmethod
    def average(values: List[str], decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Calculate average of decimal values."""
        if not values:
            return ''
        total = DecimalMath.sum(values, decimal_places)
        return DecimalMath.divide(total, len(values), decimal_places)

    @staticmethod
    def max(values: List[str], decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Find maximum value in list."""
        if not values:
            return ''
        max_units = max(DecimalMath._string_to_units(v, decimal_places) for v in values)
        return DecimalMath._units_to_string(max_units, decimal_places)

    @staticmethod
    def min(values: List[str], decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Find minimum value in list."""
        if not values:
            return ''
        min_units = min(DecimalMath._string_to_units(v, decimal_places) for v in values)
        return DecimalMath._units_to_string(min_units, decimal_places)

    @staticmethod
    def compare(value1: str, value2: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> int:
        """Compare two values: returns -1, 0, or 1."""
        units1 = DecimalMath._string_to_units(value1, decimal_places)
        units2 = DecimalMath._string_to_units(value2, decimal_places)
        if units1 < units2:
            return -1
        elif units1 > units2:
            return 1
        else:
            return 0

    @staticmethod
    def equals(value1: str, value2: str, decimal_places: int = DEFAULT_DECIMAL_PLACES, tolerance_units: int = 0) -> bool:
        """Check if two values are equal within tolerance."""
        units1 = DecimalMath._string_to_units(value1, decimal_places)
        units2 = DecimalMath._string_to_units(value2, decimal_places)
        return abs(units1 - units2) <= tolerance_units

    @staticmethod
    def is_zero(value: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> bool:
        """Check if value is zero."""
        return DecimalMath._string_to_units(value, decimal_places) == 0

    @staticmethod
    def is_negative(value: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> bool:
        """Check if value is negative."""
        return DecimalMath._string_to_units(value, decimal_places) < 0

    @staticmethod
    def is_positive(value: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> bool:
        """Check if value is positive."""
        return DecimalMath._string_to_units(value, decimal_places) > 0

    @staticmethod
    def abs(value: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Get absolute value."""
        units = abs(DecimalMath._string_to_units(value, decimal_places))
        return DecimalMath._units_to_string(units, decimal_places)

    @staticmethod
    def negate(value: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Negate the value."""
        units = -DecimalMath._string_to_units(value, decimal_places)
        return DecimalMath._units_to_string(units, decimal_places)

    @staticmethod
    def round(value: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Round to specified decimal places."""
        units = DecimalMath._string_to_units(value, decimal_places)
        return DecimalMath._units_to_string(units, decimal_places)

    @staticmethod
    def validate(value: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> bool:
        """Validate that string represents a valid decimal."""
        try:
            DecimalMath._string_to_units(value, decimal_places)
            return True
        except ValueError:
            return False

    @staticmethod
    def normalize(value: str, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
        """Normalize and format a decimal string with complete validation."""
        if not value or value.strip() == '':
            error_msg = f"Empty or whitespace-only input: {repr(value)}"
            report_error("validation", error_msg)
            raise ValueError(error_msg)

        # Check for obviously malformed input before processing
        clean_value = value.strip()
        if not clean_value:
            error_msg = f"Empty input after trimming: {repr(value)}"
            report_error("validation", error_msg)
            raise ValueError(error_msg)

        # Check for invalid characters - only allow digits, decimal point, minus sign, and basic formatting
        import re
        if not re.match(r'^[-+]?\s*[\d\s,]*\.?\d*\s*$', clean_value):
            error_msg = f"Input contains invalid characters: {repr(value)}"
            report_error("validation", error_msg)
            raise ValueError(error_msg)

        # Check for multiple decimal points
        if clean_value.count('.') > 1:
            error_msg = f"Multiple decimal points not allowed: {repr(value)}"
            report_error("validation", error_msg)
            raise ValueError(error_msg)

        # Check for multiple minus signs
        minus_count = clean_value.count('-') + clean_value.count('+')
        if minus_count > 1:
            error_msg = f"Multiple sign characters not allowed: {repr(value)}"
            report_error("validation", error_msg)
            raise ValueError(error_msg)

        # Check for minus/plus sign in wrong position
        if ('-' in clean_value and clean_value.find('-') > 0) or ('+' in clean_value and clean_value.find('+') > 0):
            error_msg = f"Sign character must be at start: {repr(value)}"
            report_error("validation", error_msg)
            raise ValueError(error_msg)

        try:
            units = DecimalMath._string_to_units(value, decimal_places)

            # Validate reasonable range (currency should be between -999999.99 and 999999.99)
            if units < -99999999 or units > 99999999:  # -999999.99 to 999999.99 in cents
                error_msg = f"Currency value out of range (-999999.99 to 999999.99): {DecimalMath._units_to_string(units, decimal_places)}"
                report_error("validation", error_msg)
                raise ValueError(error_msg)

            return DecimalMath._units_to_string(units, decimal_places)
        except (ValueError, OverflowError) as e:
            error_msg = f"Invalid currency value: {repr(value)} - {e}"
            report_error("validation", error_msg)
            raise ValueError(error_msg)
