"""
Apebot Custom Exceptions
Centralized error handling for economy and item interactions.
"""

class ApebotError(Exception):
    """Base class for all Apebot exceptions."""
    pass

class EconomyError(ApebotError):
    """Base class for economy-related errors."""
    pass

class InsufficientTokens(EconomyError):
    """Raised when a user does not have enough tokens for an action."""
    def __init__(self, required, actual):
        self.required = required
        self.actual = actual
        super().__init__(f"Insufficient tokens: required {required}, but only have {actual}.")

class UserNotFoundError(EconomyError):
    """Raised when an operation is attempted on a non-existent user."""
    pass

class ItemError(ApebotError):
    """Base class for item-related errors."""
    pass

class ItemNotFoundError(ItemError):
    """Raised when an item is not found in the registry."""
    pass

class InventoryError(ItemError):
    """Raised when an item cannot be used or purchased due to inventory issues."""
    pass

class InsufficientInventory(InventoryError):
    """Raised when a user attempts to use an item they don't own."""
    def __init__(self, item_name):
        self.item_name = item_name
        super().__init__(f"User does not have any '{item_name}' in inventory.")

class CurseError(ItemError):
    """Raised when a curse cannot be applied due to existing effects or protections."""
    pass

class ActiveCurseError(CurseError):
    """Raised when target already has an active curse."""
    pass
