"""Arithmetic tools and a deterministic boundary for a small math agent."""

import json
import re
from dataclasses import dataclass
from decimal import Decimal, DecimalException, localcontext

FALLBACK = "Sorry could not resolve your request"
MAX_PROMPT_LENGTH = 500
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
OPERATORS = {
    "+": "add", "plus": "add", "added to": "add",
    "-": "subtract", "minus": "subtract", "less": "subtract",
    "*": "multiply", "x": "multiply", "times": "multiply",
    "multiplied by": "multiply", "/": "divide", "divided by": "divide",
}


@dataclass(frozen=True)
class MathRequest:
    name: str
    left: Decimal
    right: Decimal


def parse_request(prompt: str) -> MathRequest | None:
    """Recognize only complete two-operand requests, never embedded arithmetic."""
    if not prompt.strip() or len(prompt) > MAX_PROMPT_LENGTH:
        return None
    text = prompt.strip().lower().rstrip("?.").strip()
    text = re.sub(r"^(?:please\s+)?(?:what is|what's|calculate|compute|evaluate|solve)\s+", "", text)
    alternatives = "|".join(re.escape(operator) for operator in OPERATORS)
    match = re.fullmatch(rf"({NUMBER})\s*({alternatives})\s*({NUMBER})", text)
    if match:
        left, operator, right = match.groups()
        name = OPERATORS[operator]
    else:
        match = re.fullmatch(rf"(add|subtract|substract|multiply|divide)\s+({NUMBER})\s+(and|to|from|by)\s+({NUMBER})", text)
        if not match:
            return None
        name, left, connector, right = match.groups()
        name = "subtract" if name == "substract" else name
        connectors = {"add": {"and", "to"}, "subtract": {"from"}, "multiply": {"and", "by"}, "divide": {"by"}}
        if connector not in connectors[name]:
            return None
        if name == "subtract":
            left, right = right, left
    if len(left) > 64 or len(right) > 64:
        return None
    return MathRequest(name, Decimal(left), Decimal(right))


def format_number(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("A finite result is required")
    text = format(value, "f")
    return (text.rstrip("0").rstrip(".") if "." in text else text) if value else "0"


def add(left: Decimal, right: Decimal) -> Decimal:
    return left + right


def subtract(left: Decimal, right: Decimal) -> Decimal:
    return left - right


def multiply(left: Decimal, right: Decimal) -> Decimal:
    return left * right


def divide(left: Decimal, right: Decimal) -> Decimal:
    if not right:
        raise ValueError("Division by zero is unsupported")
    return left / right


def reject_request() -> str:
    return FALLBACK


ARITHMETIC_TOOLS = {"add": add, "subtract": subtract, "multiply": multiply, "divide": divide}


def execute_tool(prompt: str, name: str, arguments: str) -> str:
    """Run only a tool call matching the entire user request; fail closed."""
    try:
        if len(arguments) > 1000:
            return reject_request()
        payload = json.loads(arguments, parse_float=Decimal, parse_int=Decimal)
        if name == "reject_request":
            return reject_request()
        expected = parse_request(prompt)
        if expected is None or name != expected.name or name not in ARITHMETIC_TOOLS:
            return reject_request()
        if not isinstance(payload, dict) or set(payload) != {"left", "right"}:
            return reject_request()
        left, right = payload["left"], payload["right"]
        if not isinstance(left, Decimal) or not isinstance(right, Decimal):
            return reject_request()
        if not left.is_finite() or not right.is_finite():
            return reject_request()
        if left != expected.left or right != expected.right:
            return reject_request()
        with localcontext() as context:
            context.prec = 28
            return format_number(ARITHMETIC_TOOLS[name](left, right))
    except (ValueError, TypeError, DecimalException, RecursionError):
        return reject_request()