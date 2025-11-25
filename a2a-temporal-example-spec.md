# Food Finder: A2A Multi-Agent System with Human-in-the-Loop

A personal assistant queries multiple food service agents in parallel to find menu options, then waits for human approval before placing an order.

## The A2A Value Proposition

**A2A is the cross-boundary protocol between different Temporal systems.**

Each agent runs its own Temporal workflow for durability. A2A provides the standard protocol for these independent systems to communicate. The PersonalAssistant doesn't need to know that BurgerBot and TacoTime use Temporal internally - it just speaks A2A.

Key concepts demonstrated:
- **Agent Discovery**: Fetching Agent Cards to learn capabilities
- **Parallel Queries**: Coordinator queries multiple services simultaneously via A2A
- **Task Lifecycle**: submitted → working → input-required → completed
- **Human-in-the-Loop**: Workflow waits for human approval before proceeding
- **Cross-Boundary Protocol**: Each agent could be on a different Temporal cluster, different cloud, different company

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  User: "Find me food under $15"                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PersonalAssistantWorkflow (COORDINATOR)                         │
│  - Your Temporal cluster                                         │
│                                                                  │
│  1. activity: fetch_agent_card(burgerbot)      ─┐               │
│  2. activity: fetch_agent_card(tacotime)       ─┘ Discovery     │
│                                                                  │
│  3. activity: query_menu(burgerbot, $15)       ─┐               │
│  4. activity: query_menu(tacotime, $15)        ─┘ PARALLEL      │
│                                                                  │
│  5. Synthesize menu options from both services                   │
│                                                                  │
│  6. WAIT for human approval (signal: confirm_order)  ← HUMAN    │
│                                                                  │
│  7. activity: place_order(selected_restaurant, items)            │
└─────────────────────────────────────────────────────────────────┘
         │ A2A Protocol (HTTP)               │ A2A Protocol (HTTP)
         ▼                                   ▼
┌─────────────────────┐         ┌─────────────────────┐
│     BurgerBot       │         │      TacoTime       │
│   (SERVICE Agent)   │         │   (SERVICE Agent)   │
│                     │         │                     │
│  Their Temporal     │         │  Their Temporal     │
│  cluster            │         │  cluster            │
│                     │         │                     │
│  Skills:            │         │  Skills:            │
│  - get_menu         │         │  - get_menu         │
│  - place_order      │         │  - place_order      │
└─────────────────────┘         └─────────────────────┘
```

---

## Agents

| Agent | Role | Port | Task Queue | Skills |
|-------|------|------|------------|--------|
| PersonalAssistant | COORDINATOR | 8000 | personal-assistant-queue | `find_food` |
| BurgerBot | SERVICE | 8001 | burger-bot-queue | `get_menu`, `place_order` |
| TacoTime | SERVICE | 8002 | taco-time-queue | `get_menu`, `place_order` |

---

## Shared Types

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class FoodQuery:
    """Query parameters for finding food."""
    max_price: float
    cuisine_preference: Optional[str] = None


@dataclass
class MenuItem:
    """A menu item from a food service."""
    name: str
    price: float
    description: str
    restaurant: str  # Which service this came from


@dataclass
class OrderItem:
    """An item to order."""
    name: str
    quantity: int


@dataclass
class OrderRequest:
    """Request to place an order."""
    items: list[OrderItem]
    restaurant: str  # burger_bot or taco_time
    customer_name: str
    delivery_address: str


@dataclass
class OrderConfirmation:
    """Confirmation of a placed order."""
    order_id: str
    restaurant: str
    estimated_time: str
    items: list[OrderItem]
    total: float
```

---

## Agent Cards

### PersonalAssistant Agent Card

```python
PERSONAL_ASSISTANT_AGENT_CARD = {
    "name": "PersonalAssistant",
    "description": "Helps users find and order food from multiple restaurants",
    "url": "http://localhost:8000",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False
    },
    "skills": [
        {
            "id": "find_food",
            "name": "Find Food",
            "description": "Search multiple restaurants for menu items under a price limit, then place an order after user approval",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "max_price": {"type": "number", "description": "Maximum price per item"},
                    "cuisine_preference": {"type": "string", "description": "Optional cuisine preference"}
                },
                "required": ["max_price"]
            }
        }
    ]
}
```

### BurgerBot Agent Card

```python
BURGER_BOT_AGENT_CARD = {
    "name": "BurgerBot",
    "description": "Burger restaurant ordering service",
    "url": "http://localhost:8001",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False
    },
    "skills": [
        {
            "id": "get_menu",
            "name": "Get Menu",
            "description": "Get menu items under a price limit",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "max_price": {"type": "number", "description": "Maximum price per item"}
                },
                "required": ["max_price"]
            }
        },
        {
            "id": "place_order",
            "name": "Place Order",
            "description": "Place an order for delivery",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "items": {"type": "array", "items": {"type": "object"}},
                    "customer_name": {"type": "string"},
                    "delivery_address": {"type": "string"}
                },
                "required": ["items", "customer_name", "delivery_address"]
            }
        }
    ]
}
```

### TacoTime Agent Card

```python
TACO_TIME_AGENT_CARD = {
    "name": "TacoTime",
    "description": "Taco restaurant ordering service",
    "url": "http://localhost:8002",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False
    },
    "skills": [
        {
            "id": "get_menu",
            "name": "Get Menu",
            "description": "Get menu items under a price limit",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "max_price": {"type": "number", "description": "Maximum price per item"}
                },
                "required": ["max_price"]
            }
        },
        {
            "id": "place_order",
            "name": "Place Order",
            "description": "Place an order for delivery",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "items": {"type": "array", "items": {"type": "object"}},
                    "customer_name": {"type": "string"},
                    "delivery_address": {"type": "string"}
                },
                "required": ["items", "customer_name", "delivery_address"]
            }
        }
    ]
}
```

---

## Activities

### PersonalAssistant Activities

```python
from temporalio import activity
import httpx
import json


@activity.defn
async def fetch_agent_card(agent_url: str) -> dict:
    """Fetch an agent's capabilities via A2A discovery."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{agent_url}/.well-known/agent.json")
        return response.json()


@activity.defn
async def query_menu_via_a2a(agent_url: str, max_price: float) -> list[dict]:
    """Query a food service for menu items via A2A protocol."""
    request = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "id": str(uuid.uuid4()),
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": json.dumps({"max_price": max_price})}]
            },
            "skill": "get_menu"
        }
    }

    async with httpx.AsyncClient() as client:
        # Send task
        response = await client.post(agent_url, json=request)
        result = response.json()
        task_id = result["result"]["id"]

        # Poll for completion
        while True:
            status_request = {
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "id": str(uuid.uuid4()),
                "params": {"id": task_id}
            }
            status_response = await client.post(agent_url, json=status_request)
            status_result = status_response.json()
            state = status_result["result"]["status"]["state"]

            if state == "completed":
                return status_result["result"].get("artifacts", [])
            elif state == "failed":
                raise Exception(status_result["result"]["status"]["error"]["message"])

            await asyncio.sleep(1)


@activity.defn
async def place_order_via_a2a(agent_url: str, order: OrderRequest) -> dict:
    """Place an order with a food service via A2A protocol."""
    request = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "id": str(uuid.uuid4()),
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": json.dumps({
                    "items": [{"name": item.name, "quantity": item.quantity} for item in order.items],
                    "customer_name": order.customer_name,
                    "delivery_address": order.delivery_address
                })}]
            },
            "skill": "place_order"
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(agent_url, json=request)
        result = response.json()
        task_id = result["result"]["id"]

        # Poll for completion
        while True:
            status_request = {
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "id": str(uuid.uuid4()),
                "params": {"id": task_id}
            }
            status_response = await client.post(agent_url, json=status_request)
            status_result = status_response.json()
            state = status_result["result"]["status"]["state"]

            if state == "completed":
                return status_result["result"].get("artifacts", [{}])[0]
            elif state == "failed":
                raise Exception(status_result["result"]["status"]["error"]["message"])

            await asyncio.sleep(1)
```

### BurgerBot Activities

```python
from temporalio import activity


@activity.defn
async def get_burger_menu(max_price: float) -> list[MenuItem]:
    """Get burger menu items under the price limit."""
    # Mock menu data
    all_items = [
        MenuItem(name="Classic Burger", price=12.99, description="Beef patty with lettuce, tomato, onion", restaurant="BurgerBot"),
        MenuItem(name="Cheese Burger", price=13.99, description="Classic with American cheese", restaurant="BurgerBot"),
        MenuItem(name="Bacon Burger", price=15.99, description="Topped with crispy bacon", restaurant="BurgerBot"),
        MenuItem(name="Veggie Burger", price=11.99, description="Plant-based patty", restaurant="BurgerBot"),
        MenuItem(name="Cheese Fries", price=6.99, description="Crispy fries with melted cheese", restaurant="BurgerBot"),
        MenuItem(name="Onion Rings", price=5.99, description="Beer-battered onion rings", restaurant="BurgerBot"),
    ]
    return [item for item in all_items if item.price <= max_price]


@activity.defn
async def submit_burger_order(items: list[OrderItem], customer_name: str, delivery_address: str) -> OrderConfirmation:
    """Submit a burger order to the kitchen."""
    total = sum(
        12.99 if item.name == "Classic Burger" else
        13.99 if item.name == "Cheese Burger" else
        6.99 if item.name == "Cheese Fries" else 10.0
        for item in items
        for _ in range(item.quantity)
    )

    return OrderConfirmation(
        order_id=f"BB-{uuid.uuid4().hex[:8].upper()}",
        restaurant="BurgerBot",
        estimated_time="20-25 minutes",
        items=items,
        total=total
    )
```

### TacoTime Activities

```python
from temporalio import activity


@activity.defn
async def get_taco_menu(max_price: float) -> list[MenuItem]:
    """Get taco menu items under the price limit."""
    # Mock menu data
    all_items = [
        MenuItem(name="Taco Trio", price=10.99, description="Three tacos: beef, chicken, carnitas", restaurant="TacoTime"),
        MenuItem(name="Burrito Supreme", price=13.99, description="Loaded burrito with all the fixings", restaurant="TacoTime"),
        MenuItem(name="Quesadilla", price=9.99, description="Cheese quesadilla with salsa", restaurant="TacoTime"),
        MenuItem(name="Nachos Grande", price=12.99, description="Loaded nachos for sharing", restaurant="TacoTime"),
        MenuItem(name="Churros", price=5.99, description="Cinnamon sugar churros", restaurant="TacoTime"),
        MenuItem(name="Guacamole & Chips", price=7.99, description="Fresh guacamole with tortilla chips", restaurant="TacoTime"),
    ]
    return [item for item in all_items if item.price <= max_price]


@activity.defn
async def submit_taco_order(items: list[OrderItem], customer_name: str, delivery_address: str) -> OrderConfirmation:
    """Submit a taco order to the kitchen."""
    total = sum(
        10.99 if item.name == "Taco Trio" else
        13.99 if item.name == "Burrito Supreme" else
        9.99 if item.name == "Quesadilla" else 10.0
        for item in items
        for _ in range(item.quantity)
    )

    return OrderConfirmation(
        order_id=f"TT-{uuid.uuid4().hex[:8].upper()}",
        restaurant="TacoTime",
        estimated_time="15-20 minutes",
        items=items,
        total=total
    )
```

---

## Workflows

### PersonalAssistantWorkflow (COORDINATOR)

```python
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta
from typing import Optional
import asyncio

with workflow.unsafe.imports_passed_through():
    from .activities import fetch_agent_card, query_menu_via_a2a, place_order_via_a2a
    from shared.types import FoodQuery, MenuItem, OrderRequest, OrderConfirmation


@workflow.defn
class PersonalAssistantWorkflow:
    """
    Coordinator workflow that:
    1. Discovers food service agents
    2. Queries them IN PARALLEL for menus
    3. Waits for human approval
    4. Places order with selected restaurant
    """

    def __init__(self) -> None:
        self._menu_options: list[MenuItem] = []
        self._selected_order: Optional[OrderRequest] = None
        self._order_confirmed: bool = False
        self._order_cancelled: bool = False

    @workflow.run
    async def run(self, query: FoodQuery) -> dict:
        workflow.logger.info(f"Starting food search: max_price=${query.max_price}")

        # Service endpoints (in production, these could be discovered dynamically)
        services = [
            {"name": "BurgerBot", "url": "http://localhost:8001"},
            {"name": "TacoTime", "url": "http://localhost:8002"},
        ]

        # Step 1: Discover agents (optional - fetch agent cards)
        workflow.logger.info("Discovering food service agents...")
        agent_cards = []
        for service in services:
            card = await workflow.execute_activity(
                fetch_agent_card,
                service["url"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            agent_cards.append(card)
            workflow.logger.info(f"  Found: {card['name']} with skills: {[s['id'] for s in card['skills']]}")

        # Step 2: Query all services IN PARALLEL
        workflow.logger.info("Querying services for menus IN PARALLEL...")

        menu_tasks = [
            workflow.execute_activity(
                query_menu_via_a2a,
                args=[service["url"], query.max_price],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            for service in services
        ]

        # Wait for all queries to complete (fan-out/fan-in)
        results = await asyncio.gather(*menu_tasks, return_exceptions=True)

        # Step 3: Synthesize results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                workflow.logger.warning(f"Failed to query {services[i]['name']}: {result}")
            else:
                for item_data in result:
                    if isinstance(item_data, dict) and "data" in item_data:
                        for menu_item in item_data["data"]:
                            self._menu_options.append(MenuItem(**menu_item))

        workflow.logger.info(f"Found {len(self._menu_options)} menu options total")

        if not self._menu_options:
            return {"status": "no_results", "message": "No menu items found under price limit"}

        # Step 4: WAIT for human approval
        workflow.logger.info("Waiting for human approval...")
        workflow.logger.info("  Query 'get_menu_options' to see available items")
        workflow.logger.info("  Signal 'confirm_order' with OrderRequest to proceed")
        workflow.logger.info("  Signal 'cancel' to abort")

        await workflow.wait_condition(
            lambda: self._order_confirmed or self._order_cancelled
        )

        if self._order_cancelled:
            return {"status": "cancelled", "message": "Order cancelled by user"}

        # Step 5: Place order with selected restaurant
        if self._selected_order:
            workflow.logger.info(f"Placing order with {self._selected_order.restaurant}...")

            restaurant_url = next(
                (s["url"] for s in services if s["name"].lower().replace(" ", "_") == self._selected_order.restaurant.lower()),
                None
            )

            if not restaurant_url:
                # Try matching by partial name
                restaurant_url = "http://localhost:8001" if "burger" in self._selected_order.restaurant.lower() else "http://localhost:8002"

            confirmation = await workflow.execute_activity(
                place_order_via_a2a,
                args=[restaurant_url, self._selected_order],
                start_to_close_timeout=timedelta(minutes=2),
            )

            return {
                "status": "ordered",
                "order": confirmation,
                "message": f"Order placed with {self._selected_order.restaurant}!"
            }

        return {"status": "error", "message": "No order provided"}

    @workflow.signal
    def confirm_order(self, order_data: dict) -> None:
        """Human confirms which items to order.

        Args:
            order_data: Dict with items, restaurant, customer_name, delivery_address
        """
        self._selected_order = OrderRequest(
            items=[OrderItem(**item) for item in order_data.get("items", [])],
            restaurant=order_data.get("restaurant", ""),
            customer_name=order_data.get("customer_name", "Customer"),
            delivery_address=order_data.get("delivery_address", ""),
        )
        self._order_confirmed = True
        workflow.logger.info(f"Order confirmed: {len(self._selected_order.items)} items from {self._selected_order.restaurant}")

    @workflow.signal
    def cancel(self) -> None:
        """Human cancels the order."""
        self._order_cancelled = True
        workflow.logger.info("Order cancelled by user")

    @workflow.query
    def get_menu_options(self) -> list[dict]:
        """Query current menu options (for human to review)."""
        return [
            {
                "name": item.name,
                "price": item.price,
                "description": item.description,
                "restaurant": item.restaurant
            }
            for item in self._menu_options
        ]

    @workflow.query
    def get_status(self) -> dict:
        """Query current workflow status."""
        return {
            "menu_options_count": len(self._menu_options),
            "order_confirmed": self._order_confirmed,
            "order_cancelled": self._order_cancelled,
            "waiting_for_approval": len(self._menu_options) > 0 and not self._order_confirmed and not self._order_cancelled
        }
```

### BurgerBotWorkflow (SERVICE)

```python
from temporalio import workflow
from datetime import timedelta

with workflow.unsafe.imports_passed_through():
    from .activities import get_burger_menu, submit_burger_order
    from shared.types import MenuItem, OrderItem, OrderConfirmation


@workflow.defn
class BurgerBotWorkflow:
    """
    Service workflow for BurgerBot.
    Handles get_menu and place_order skills.
    """

    @workflow.run
    async def run(self, skill_id: str, params: dict) -> dict:
        workflow.logger.info(f"BurgerBot executing skill: {skill_id}")

        if skill_id == "get_menu":
            max_price = params.get("max_price", 100.0)
            menu_items = await workflow.execute_activity(
                get_burger_menu,
                max_price,
                start_to_close_timeout=timedelta(seconds=30),
            )
            return {
                "items": [
                    {
                        "name": item.name,
                        "price": item.price,
                        "description": item.description,
                        "restaurant": item.restaurant
                    }
                    for item in menu_items
                ]
            }

        elif skill_id == "place_order":
            items = [OrderItem(**item) for item in params.get("items", [])]
            confirmation = await workflow.execute_activity(
                submit_burger_order,
                args=[items, params.get("customer_name", ""), params.get("delivery_address", "")],
                start_to_close_timeout=timedelta(seconds=30),
            )
            return {
                "order_id": confirmation.order_id,
                "restaurant": confirmation.restaurant,
                "estimated_time": confirmation.estimated_time,
                "total": confirmation.total
            }

        else:
            raise ValueError(f"Unknown skill: {skill_id}")
```

### TacoTimeWorkflow (SERVICE)

```python
from temporalio import workflow
from datetime import timedelta

with workflow.unsafe.imports_passed_through():
    from .activities import get_taco_menu, submit_taco_order
    from shared.types import MenuItem, OrderItem, OrderConfirmation


@workflow.defn
class TacoTimeWorkflow:
    """
    Service workflow for TacoTime.
    Handles get_menu and place_order skills.
    """

    @workflow.run
    async def run(self, skill_id: str, params: dict) -> dict:
        workflow.logger.info(f"TacoTime executing skill: {skill_id}")

        if skill_id == "get_menu":
            max_price = params.get("max_price", 100.0)
            menu_items = await workflow.execute_activity(
                get_taco_menu,
                max_price,
                start_to_close_timeout=timedelta(seconds=30),
            )
            return {
                "items": [
                    {
                        "name": item.name,
                        "price": item.price,
                        "description": item.description,
                        "restaurant": item.restaurant
                    }
                    for item in menu_items
                ]
            }

        elif skill_id == "place_order":
            items = [OrderItem(**item) for item in params.get("items", [])]
            confirmation = await workflow.execute_activity(
                submit_taco_order,
                args=[items, params.get("customer_name", ""), params.get("delivery_address", "")],
                start_to_close_timeout=timedelta(seconds=30),
            )
            return {
                "order_id": confirmation.order_id,
                "restaurant": confirmation.restaurant,
                "estimated_time": confirmation.estimated_time,
                "total": confirmation.total
            }

        else:
            raise ValueError(f"Unknown skill: {skill_id}")
```

---

## Demo Flow

### Step 1: Start the System

```bash
# Terminal 1: Temporal server
temporal server start-dev

# Terminal 2: Start all workers and gateways
uv run orchestrator start
```

### Step 2: Send a Food Query

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "id": "1",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "{\"max_price\": 15.0}"}]
      }
    }
  }'

# Response:
# {"jsonrpc": "2.0", "id": "1", "result": {"id": "food-query-abc123", "status": {"state": "working"}}}
```

### Step 3: Check Menu Options (Query the Workflow)

```bash
# Using temporal CLI or interact.py
uv run interact --workflow-id food-query-abc123 --query get_menu_options

# Output:
# [
#   {"name": "Classic Burger", "price": 12.99, "restaurant": "BurgerBot"},
#   {"name": "Veggie Burger", "price": 11.99, "restaurant": "BurgerBot"},
#   {"name": "Cheese Fries", "price": 6.99, "restaurant": "BurgerBot"},
#   {"name": "Taco Trio", "price": 10.99, "restaurant": "TacoTime"},
#   {"name": "Quesadilla", "price": 9.99, "restaurant": "TacoTime"},
#   ...
# ]
```

### Step 4: Approve Order (Signal the Workflow)

```bash
uv run interact --workflow-id food-query-abc123 --signal confirm_order \
  --data '{
    "items": [{"name": "Classic Burger", "quantity": 1}, {"name": "Cheese Fries", "quantity": 1}],
    "restaurant": "burger_bot",
    "customer_name": "Demo User",
    "delivery_address": "123 Main Street"
  }'
```

### Step 5: Get Final Result

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "id": "2",
    "params": {"id": "food-query-abc123"}
  }'

# Response:
# {
#   "jsonrpc": "2.0",
#   "id": "2",
#   "result": {
#     "id": "food-query-abc123",
#     "status": {"state": "completed"},
#     "artifacts": [{
#       "type": "data",
#       "data": {
#         "status": "ordered",
#         "order": {
#           "order_id": "BB-A1B2C3D4",
#           "restaurant": "BurgerBot",
#           "estimated_time": "20-25 minutes",
#           "total": 19.98
#         }
#       }
#     }]
#   }
# }
```

---

## What This Demonstrates

1. **A2A Discovery**: PersonalAssistant fetches Agent Cards to learn what BurgerBot and TacoTime can do
2. **Parallel Queries**: Both services are queried simultaneously using `asyncio.gather()`
3. **Cross-Boundary Protocol**: Each agent runs its own Temporal workflow; A2A is the protocol between them
4. **Human-in-the-Loop**: Workflow pauses and waits for human signal before placing order
5. **Durable Execution**: If PersonalAssistant crashes while waiting for approval, it resumes exactly where it left off
6. **Task Lifecycle**: submitted → working → (waiting for input) → completed

---

## Key A2A Patterns Demonstrated

### Coordinator Pattern
```
COORDINATOR queries multiple SERVICES in parallel:
  - Uses asyncio.gather() for fan-out
  - Collects results from all services
  - Synthesizes into unified response
  - Handles partial failures gracefully
```

### Human-in-the-Loop Pattern
```
Workflow reaches decision point:
  - Exposes query handler for current state
  - Waits for signal from human
  - Signal provides decision (approve/cancel + details)
  - Workflow continues based on decision
```

### Service Pattern
```
SERVICE receives A2A task:
  - Gateway starts Temporal workflow
  - Workflow executes skill-specific logic
  - Returns result via A2A response
```
