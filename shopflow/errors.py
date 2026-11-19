"""Errors the shop's rules raise. The API turns them into 404, 409 and 400 responses."""


class NotFound(Exception):
    """The thing asked for doesn't exist."""


class Conflict(Exception):
    """The request is valid, but the current state doesn't allow it (no stock, already returned...)."""


class Invalid(Exception):
    """The request itself is wrong (unknown coupon, empty order...)."""
