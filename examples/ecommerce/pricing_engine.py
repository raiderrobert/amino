#!/usr/bin/env python3
"""
E-commerce Pricing Engine Example

This example demonstrates how to use Amino to build a flexible pricing engine
where business users can create and modify pricing rules without code changes.
"""

from datetime import datetime
from typing import Any

import amino


class PricingEngine:
    """Dynamic pricing engine using Amino rules."""

    def __init__(self):
        # Load the schema
        with open("examples/ecommerce/schema.amino") as f:
            schema_content = f.read()

        self.schema = amino.Schema(schema_content)

        # Register custom functions that rules can use
        self.schema.add_function("calculate_discount", self._calculate_discount)
        self.schema.add_function("is_holiday_season", self._is_holiday_season)
        self.schema.add_function("get_shipping_cost", self._get_shipping_cost)

        # Business-defined pricing rules
        self.pricing_rules = [
            {
                "id": "gold_customer_discount",
                "rule": "customer.tier = 'gold' and order.total > 100",
                "ordering": 1,
                "metadata": {"discount_percent": 15, "description": "Gold customers get 15% off orders over $100"},
            },
            {
                "id": "bulk_order_discount",
                "rule": "order.item_count >= 10",
                "ordering": 2,
                "metadata": {"discount_percent": 10, "description": "10% off orders with 10+ items"},
            },
            {
                "id": "clearance_electronics",
                "rule": "product.category = 'electronics' and product.inventory_count < 5",
                "ordering": 3,
                "metadata": {"discount_percent": 25, "description": "25% off electronics with low inventory"},
            },
            {
                "id": "loyal_customer_bonus",
                "rule": "customer.purchase_count > 20 and customer.total_spent > 1000",
                "ordering": 4,
                "metadata": {"discount_percent": 20, "description": "20% off for very loyal customers"},
            },
            {
                "id": "holiday_promotion",
                "rule": "is_holiday_season(order.date) and order.total > 50",
                "ordering": 5,
                "metadata": {"discount_percent": 12, "description": "Holiday season promotion"},
            },
        ]

    def _calculate_discount(self, original_price: float, discount_percent: float) -> float:
        """Calculate discounted price."""
        return original_price * (1 - discount_percent / 100)

    def _is_holiday_season(self, date_str: str) -> bool:
        """Check if date falls in holiday season (Nov-Dec)."""
        try:
            date = datetime.fromisoformat(date_str)
            return date.month in [11, 12]
        except:
            return False

    def _get_shipping_cost(self, zip_code: str, order_total: float) -> float:
        """Calculate shipping cost based on zip and order total."""
        base_cost = 9.99
        if order_total > 75:
            return 0.0  # Free shipping
        if zip_code.startswith(("9", "8")):  # West coast
            return base_cost + 2.0
        return base_cost

    def calculate_price(
        self, customer_data: dict[str, Any], product_data: dict[str, Any], order_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate final pricing with applicable discounts."""

        # Combine all data for rule evaluation
        rule_data = {"customer": customer_data, "product": product_data, "order": order_data}

        # Compile rules for evaluation
        compiled_rules = self.schema.compile(
            self.pricing_rules, match={"option": "first", "key": "ordering", "ordering": "asc"}
        )

        # Evaluate rules against the data
        results = compiled_rules.eval([{"id": "pricing_decision", **rule_data}])

        # Calculate final pricing
        original_total = order_data["total"]
        applied_discounts = []
        final_total = original_total

        if results and results[0].results:
            # Get the first matching rule (highest priority)
            matched_rule_id = results[0].results[0]

            # Find the rule metadata
            for rule in self.pricing_rules:
                if rule["id"] == matched_rule_id:
                    discount_percent = rule["metadata"]["discount_percent"]
                    final_total = self._calculate_discount(original_total, discount_percent)
                    applied_discounts.append(
                        {
                            "rule_id": matched_rule_id,
                            "description": rule["metadata"]["description"],
                            "discount_percent": discount_percent,
                            "discount_amount": original_total - final_total,
                        }
                    )
                    break

        shipping_cost = self._get_shipping_cost(order_data["shipping_zip"], final_total)

        return {
            "original_total": original_total,
            "final_total": final_total,
            "shipping_cost": shipping_cost,
            "grand_total": final_total + shipping_cost,
            "applied_discounts": applied_discounts,
            "savings": original_total - final_total,
        }


def main():
    """Demo the pricing engine with sample data."""
    engine = PricingEngine()

    # Sample customer data
    customers = [
        {"id": "cust_001", "tier": "gold", "purchase_count": 25, "total_spent": 1500.0, "signup_date": "2022-01-15"},
        {"id": "cust_002", "tier": "silver", "purchase_count": 5, "total_spent": 200.0, "signup_date": "2023-06-01"},
    ]

    # Sample product
    product = {"id": "prod_001", "category": "electronics", "price": 299.99, "inventory_count": 3, "brand": "TechCorp"}

    # Sample orders
    orders = [
        {"id": "order_001", "total": 150.0, "item_count": 2, "shipping_zip": "90210", "date": "2023-12-15"},
        {"id": "order_002", "total": 75.0, "item_count": 12, "shipping_zip": "10001", "date": "2023-08-20"},
    ]

    print("🛒 E-commerce Pricing Engine Demo")
    print("=" * 50)

    for i, customer in enumerate(customers):
        for j, order in enumerate(orders):
            print(f"\n📦 Scenario {i + 1}.{j + 1}: {customer['tier'].title()} Customer, ${order['total']} order")

            pricing = engine.calculate_price(customer, product, order)

            print(f"   Original Total: ${pricing['original_total']:.2f}")
            print(f"   Final Total:    ${pricing['final_total']:.2f}")
            print(f"   Shipping:       ${pricing['shipping_cost']:.2f}")
            print(f"   Grand Total:    ${pricing['grand_total']:.2f}")

            if pricing["applied_discounts"]:
                discount = pricing["applied_discounts"][0]
                print(f"   💰 Applied: {discount['description']} (-${discount['discount_amount']:.2f})")
            else:
                print("   💸 No discounts applied")


if __name__ == "__main__":
    main()
