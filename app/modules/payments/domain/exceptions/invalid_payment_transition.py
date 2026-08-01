class InvalidPaymentTransitionError(Exception):
    """Raised when a payment's current state does not allow the attempted transition."""
