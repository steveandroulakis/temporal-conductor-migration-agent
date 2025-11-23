"""Workflow definition for shopping_cart.

Temporal workflow migrated from Conductor workflow: shopping_cart

This workflow implements a shopping cart state machine with human interaction
at multiple stages. The workflow loops until the user moves to checkout, then
handles the checkout process with confirmation.

Control Flow:
1. Initialize cart with input items
2. DO_WHILE loop: Continue shopping until cart status is 'checkout'
   - Store previous cart state
   - Wait for user to update cart (Update handler: update_cart)
   - Update cart variables with new data
   - SWITCH on cart status:
     - If 'checkout': Execute checkout flow
       - Run checkout sub-workflow
       - Wait for checkout confirmation (Update handler: confirm_checkout)
       - Nested SWITCH on checkout success:
         - If 'checkout_failed': Reset to shopping mode (loop continues)
         - Else: Clear cart items (loop exits)
     - Else: Execute inline JavaScript equivalent (continue shopping)
3. Return final cart state

Original Conductor workflow: conductor-definition/shopping_cart_1.json
Complexity: HIGH
Max nesting depth: 4 (DO_WHILE > SWITCH > SUB_WORKFLOW/WAIT > nested SWITCH)

Human Interaction:
- update_cart Update: Receives cart updates from user during shopping phase
- confirm_checkout Update: Receives checkout completion confirmation
- Query get_cart_status: Allows checking current cart state
"""
import asyncio
from datetime import timedelta
from typing import Optional, Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from .shared import (
        WorkflowInput,
        WorkflowOutput,
        CartUpdate,
        CartUpdateResult,
        CheckoutConfirmation,
        CheckoutConfirmationResult,
    )


# Default retry policy for sub-workflow execution
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=100),
    maximum_attempts=3,
    backoff_coefficient=2.0
)


@workflow.defn
class ShoppingCartWorkflow:
    """Shopping cart workflow with human interaction and checkout process.

    This workflow manages a shopping cart lifecycle:
    - User can update cart multiple times
    - User can move to checkout
    - Checkout can succeed or fail (with retry loop)
    - Final cart state is returned

    The workflow waits for external input at two points:
    1. Cart updates during shopping (update_cart)
    2. Checkout confirmation after sub-workflow (confirm_checkout)
    """

    def __init__(self) -> None:
        """Initialize workflow state variables."""
        # Cart state variables (correspond to Conductor workflow.variables)
        self._cart: str = ""
        self._cart_items: str = ""
        self._last_cart_items: str = ""

        # Human interaction state
        self._cart_update: Optional[CartUpdate] = None
        self._checkout_result: Optional[CheckoutConfirmation] = None

        # Status tracking for queries
        self._status: str = "initialized"
        self._loop_iteration: int = 0

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        """Execute the shopping cart workflow.

        Args:
            input: Workflow input containing initial items list

        Returns:
            WorkflowOutput containing final cart status and items

        Raises:
            ApplicationError: On unrecoverable errors
        """
        workflow.logger.info(f"Starting shopping cart workflow with items: {input.items}")

        # Task: cart_creation (SET_VARIABLE)
        # Original: cart_creation_ref
        # Initialize shopping cart with workflow input items
        self._cart = "shopping"
        self._cart_items = ", ".join(input.items) if input.items else ""
        workflow.logger.info(f"Cart initialized: cart={self._cart}, items={self._cart_items}")

        # Task: checkout_success (DO_WHILE)
        # Original: checkout_success_ref
        # Loop until cart status is 'checkout'
        # Conductor loopCondition: if("${workflow.variables.cart}"!="checkout") { true; } else { false; }
        self._status = "shopping"
        max_iterations = 100  # Prevent infinite loops

        while self._cart != "checkout" and self._loop_iteration < max_iterations:
            self._loop_iteration += 1
            workflow.logger.info(f"Shopping loop iteration {self._loop_iteration}")

            # Task: last_cart (SET_VARIABLE)
            # Original: last_cart_ref (nesting level 1)
            # Store previous cart state before waiting for updates
            self._last_cart_items = self._cart_items
            workflow.logger.info(f"Stored last cart items: {self._last_cart_items}")

            # Task: cart_wait (WAIT)
            # Original: cart_wait_ref (nesting level 1)
            # Wait for external cart update from user
            # This is a WAIT task expecting external data: cart and cart_items
            # Implemented as Update handler with wait_condition
            workflow.logger.info("Waiting for cart update from user...")
            self._cart_update = None  # Reset for new update
            await workflow.wait_condition(
                lambda: self._cart_update is not None,
                timeout=timedelta(hours=24)  # Allow 24 hours for user to update
            )

            # If wait times out, we'll get asyncio.TimeoutError
            # For now, we don't catch it - workflow will fail if user doesn't respond
            # Production implementation should handle timeout gracefully

            workflow.logger.info(f"Cart update received: {self._cart_update}")

            # Task: cart_update (SET_VARIABLE)
            # Original: cart_update_ref (nesting level 1)
            # Update cart variables with data received from external signal
            # Conductor: cart = ${cart_wait_ref.output.cart}
            # Conductor: cart_items = ${cart_wait_ref.output.cart_items}
            if self._cart_update is not None:
                self._cart = self._cart_update.cart
                self._cart_items = self._cart_update.cart_items
                workflow.logger.info(f"Cart updated: cart={self._cart}, items={self._cart_items}")
            else:
                # This should never happen as we wait_condition above
                raise ApplicationError("Cart update is None after wait_condition", non_retryable=True)

            # Task: shopping_checkout (SWITCH)
            # Original: shopping_checkout_ref (nesting level 1)
            # Conditional logic based on cart status
            # Conductor evaluatorType: value-param, expression: switchCaseValue
            # Conductor switchCaseValue: ${workflow.variables.cart}

            if self._cart == "checkout":
                # SWITCH case: checkout
                # Execute checkout flow with sub-workflow and confirmation
                workflow.logger.info("Cart status is 'checkout' - initiating checkout flow")

                # Task: checkout_task (SUB_WORKFLOW)
                # Original: checkout_task_ref (nesting level 2)
                # Execute checkout sub-workflow
                # Conductor: subWorkflowParam.name = "pi_calc_test", version = 1
                workflow.logger.info("Executing checkout sub-workflow: pi_calc_test")

                # Note: The sub-workflow "pi_calc_test" must be migrated separately
                # For now, we'll create a placeholder child workflow execution
                # In production, replace with actual PiCalcTestWorkflow class
                try:
                    # Placeholder for sub-workflow execution
                    # TODO: Migrate pi_calc_test workflow and uncomment below
                    # child_result = await workflow.execute_child_workflow(
                    #     PiCalcTestWorkflow.run,
                    #     id=f"{workflow.info().workflow_id}-checkout-{self._loop_iteration}",
                    #     task_queue="pi-calc-task-queue",
                    #     retry_policy=DEFAULT_RETRY_POLICY
                    # )

                    # For now, log that sub-workflow would be executed
                    workflow.logger.info("Sub-workflow pi_calc_test completed (placeholder)")

                except Exception as e:
                    workflow.logger.error(f"Sub-workflow failed: {e}")
                    # In production, handle sub-workflow failures appropriately
                    raise

                # Task: checkout_wait (WAIT)
                # Original: checkout_wait_ref (nesting level 2)
                # Wait for checkout completion confirmation
                # This is a WAIT task expecting external data: success status
                # Implemented as Update handler with wait_condition
                workflow.logger.info("Waiting for checkout confirmation...")
                self._checkout_result = None  # Reset for new confirmation
                await workflow.wait_condition(
                    lambda: self._checkout_result is not None,
                    timeout=timedelta(hours=24)  # Allow 24 hours for confirmation
                )

                workflow.logger.info(f"Checkout confirmation received: {self._checkout_result}")

                # Task: sample_task_name_switch (SWITCH)
                # Original: sample_task_name_vn45m_ref (nesting level 3)
                # Nested conditional checking checkout success status
                # Conductor evaluatorType: value-param, expression: switchCaseValue
                # Conductor switchCaseValue: ${checkout_wait_ref.output.success}

                if self._checkout_result is None:
                    # This should never happen as we wait_condition above
                    raise ApplicationError("Checkout result is None after wait_condition", non_retryable=True)

                if self._checkout_result.success == "checkout_failed":
                    # Nested SWITCH case: checkout_failed
                    workflow.logger.info("Checkout failed - resetting to shopping mode")

                    # Task: continue_shopping (SET_VARIABLE)
                    # Original: continue_shopping_ref (nesting level 4)
                    # Reset cart to shopping mode after failed checkout
                    # This allows the DO_WHILE loop to continue
                    self._cart = "shopping"
                    workflow.logger.info("Cart reset to 'shopping' - loop will continue")

                else:
                    # Nested SWITCH default case: successful checkout
                    workflow.logger.info("Checkout successful - clearing cart items")

                    # Task: empty_cart_exit (SET_VARIABLE)
                    # Original: empty_cart_exit_ref (nesting level 4)
                    # Clear cart items after successful checkout
                    # Cart remains "checkout" so loop will exit
                    self._cart_items = ""
                    workflow.logger.info("Cart items cleared - loop will exit")

            else:
                # SWITCH default case: not in checkout mode (still shopping)
                workflow.logger.info(f"Cart status is '{self._cart}' - continuing shopping")

                # Task: sample_task_name_inline (INLINE)
                # Original: sample_task_name_skwrs_ref (nesting level 2)
                # Execute inline JavaScript when not in checkout mode
                # Conductor expression: "({ someKey: 'someValue' })"
                # Conductor evaluatorType: javascript

                # Translate inline JavaScript to Python equivalent
                inline_result = {"someKey": "someValue"}
                workflow.logger.info(f"Inline task result: {inline_result}")
                # Result is not used downstream, just executed for side effects

            # Check if we should suggest continue-as-new
            # This prevents workflow history from growing too large
            if workflow.info().is_continue_as_new_suggested():
                workflow.logger.info("Continue-as-new suggested - restarting workflow")
                # Create new input with current state
                new_input = WorkflowInput(items=self._cart_items.split(", ") if self._cart_items else [])
                workflow.continue_as_new(new_input)

        # Loop exited - cart status is "checkout" or max iterations reached
        if self._loop_iteration >= max_iterations:
            workflow.logger.warning(f"Max iterations ({max_iterations}) reached")
            self._status = "max_iterations_reached"
        else:
            workflow.logger.info("Checkout complete - workflow finishing")
            self._status = "completed"

        # Return final cart state
        return WorkflowOutput(
            cart=self._cart,
            cart_items=self._cart_items
        )

    @workflow.update
    async def update_cart(self, cart_update: CartUpdate) -> CartUpdateResult:
        """Handle cart update from user.

        This Update handler receives cart updates during the shopping phase.
        It corresponds to the cart_wait_ref WAIT task in Conductor.

        Args:
            cart_update: Cart update data with new cart status and items

        Returns:
            CartUpdateResult confirming acceptance and current state

        Raises:
            ApplicationError: If cart update is invalid or already received
        """
        workflow.logger.info(f"Update handler called: update_cart with {cart_update}")

        # Validation: Ensure we're waiting for a cart update
        if self._cart_update is not None:
            raise ApplicationError(
                "Cart update already submitted for this iteration",
                non_retryable=True
            )

        # Validation: Ensure cart status is valid
        valid_statuses = ["shopping", "checkout"]
        if cart_update.cart not in valid_statuses:
            raise ApplicationError(
                f"Invalid cart status: {cart_update.cart}. Must be one of {valid_statuses}",
                non_retryable=True
            )

        # Store the cart update
        self._cart_update = cart_update

        # Return confirmation to caller
        return CartUpdateResult(
            status="accepted",
            message="Cart update received successfully",
            current_cart=cart_update.cart,
            current_items=cart_update.cart_items
        )

    @workflow.update
    async def confirm_checkout(self, confirmation: CheckoutConfirmation) -> CheckoutConfirmationResult:
        """Handle checkout confirmation.

        This Update handler receives checkout completion confirmation after
        the checkout sub-workflow completes. It corresponds to the
        checkout_wait_ref WAIT task in Conductor.

        Args:
            confirmation: Checkout confirmation with success status

        Returns:
            CheckoutConfirmationResult confirming acceptance

        Raises:
            ApplicationError: If confirmation is invalid or already received
        """
        workflow.logger.info(f"Update handler called: confirm_checkout with {confirmation}")

        # Validation: Ensure we're waiting for checkout confirmation
        if self._checkout_result is not None:
            raise ApplicationError(
                "Checkout confirmation already submitted",
                non_retryable=True
            )

        # Validation: Ensure we're in checkout phase
        if self._cart != "checkout":
            raise ApplicationError(
                f"Cannot confirm checkout - cart status is '{self._cart}', not 'checkout'",
                non_retryable=True
            )

        # Store the checkout result
        self._checkout_result = confirmation

        # Return confirmation to caller
        return CheckoutConfirmationResult(
            status="accepted",
            message="Checkout confirmation received successfully",
            checkout_status=confirmation.success
        )

    @workflow.query
    def get_cart_status(self) -> Dict[str, Any]:
        """Query current cart status without modifying workflow.

        This query allows external systems to check the current state of the
        shopping cart workflow without affecting execution.

        Returns:
            Dict containing current cart state, status, and iteration info
        """
        return {
            "status": self._status,
            "cart": self._cart,
            "cart_items": self._cart_items,
            "last_cart_items": self._last_cart_items,
            "loop_iteration": self._loop_iteration,
            "waiting_for_cart_update": self._cart_update is None and self._status == "shopping",
            "waiting_for_checkout_confirmation": self._checkout_result is None and self._cart == "checkout"
        }
