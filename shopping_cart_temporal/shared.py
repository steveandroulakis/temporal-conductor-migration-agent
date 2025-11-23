"""Shared data types for workflow and activities.

This module contains dataclass definitions for:
- Workflow input/output types
- Update handler types for human interaction
- Activity-specific input/output types (if needed)

All types are strongly typed for mypy strict compliance.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class WorkflowInput:
    """Input parameters for the shopping_cart workflow.

    Migrated from Conductor workflow inputs.
    """
    items: List[str]


@dataclass
class WorkflowOutput:
    """Output from the shopping_cart workflow.

    Migrated from Conductor workflow outputs.
    """
    cart: str
    cart_items: str


@dataclass
class CartUpdate:
    """Cart update data from user.

    Used with workflow Updates for updating cart state during shopping.
    This corresponds to the cart_wait_ref WAIT task in Conductor.
    """
    cart: str
    cart_items: str


@dataclass
class CartUpdateResult:
    """Result returned from cart update handler.

    Provides feedback to the cart update submitter.
    """
    status: str  # "accepted", "rejected", "invalid"
    message: str
    current_cart: str
    current_items: str


@dataclass
class CheckoutConfirmation:
    """Checkout confirmation from user or external system.

    Used with workflow Updates for confirming checkout completion.
    This corresponds to the checkout_wait_ref WAIT task in Conductor.
    """
    success: str  # "checkout_failed" or other success status


@dataclass
class CheckoutConfirmationResult:
    """Result returned from checkout confirmation handler.

    Provides feedback to the checkout confirmation submitter.
    """
    status: str  # "accepted", "rejected", "invalid"
    message: str
    checkout_status: str
