#!/usr/bin/env python3
"""Tests for e-commerce pricing engine example."""


import pytest
from pricing_engine import PricingEngine


class TestPricingEngine:
    """Test cases for the pricing engine."""

    @pytest.fixture
    def engine(self):
        """Create a pricing engine instance."""
        return PricingEngine()

    @pytest.fixture
    def sample_customer_gold(self):
        """Gold tier customer data."""
        return {
            "id": "cust_gold_001",
            "tier": "gold",
            "purchase_count": 25,
            "total_spent": 1500.0,
            "signup_date": "2022-01-15",
        }

    @pytest.fixture
    def sample_customer_silver(self):
        """Silver tier customer data."""
        return {
            "id": "cust_silver_001",
            "tier": "silver",
            "purchase_count": 5,
            "total_spent": 200.0,
            "signup_date": "2023-06-01",
        }

    @pytest.fixture
    def sample_product_electronics(self):
        """Electronics product with low inventory."""
        return {
            "id": "prod_electronics_001",
            "category": "electronics",
            "price": 299.99,
            "inventory_count": 3,
            "brand": "TechCorp",
        }

    @pytest.fixture
    def sample_order_large(self):
        """Large order over $100."""
        return {"id": "order_large_001", "total": 150.0, "item_count": 2, "shipping_zip": "90210", "date": "2023-12-15"}

    @pytest.fixture
    def sample_order_small(self):
        """Small order under $100."""
        return {"id": "order_small_001", "total": 75.0, "item_count": 1, "shipping_zip": "10001", "date": "2023-08-20"}

    @pytest.fixture
    def sample_order_bulk(self):
        """Bulk order with many items."""
        return {"id": "order_bulk_001", "total": 200.0, "item_count": 12, "shipping_zip": "60601", "date": "2023-10-10"}

    def test_engine_initialization(self, engine):
        """Test that the pricing engine initializes correctly."""
        assert engine.schema is not None
        assert len(engine.pricing_rules) > 0
        assert all("id" in rule for rule in engine.pricing_rules)
        assert all("rule" in rule for rule in engine.pricing_rules)
        assert all("metadata" in rule for rule in engine.pricing_rules)

    def test_custom_functions(self, engine):
        """Test that custom functions work correctly."""
        # Test calculate_discount
        discounted = engine._calculate_discount(100.0, 15.0)
        assert discounted == 85.0

        # Test is_holiday_season
        assert engine._is_holiday_season("2023-12-15") == True
        assert engine._is_holiday_season("2023-11-25") == True
        assert engine._is_holiday_season("2023-07-04") == False

        # Test get_shipping_cost
        free_shipping = engine._get_shipping_cost("10001", 100.0)
        assert free_shipping == 0.0

        regular_shipping = engine._get_shipping_cost("10001", 50.0)
        assert regular_shipping == 9.99

        west_coast_shipping = engine._get_shipping_cost("90210", 50.0)
        assert west_coast_shipping == 11.99

    def test_gold_customer_discount(self, engine, sample_customer_gold, sample_product_electronics, sample_order_large):
        """Test that gold customers get discount on orders over $100."""
        pricing = engine.calculate_price(sample_customer_gold, sample_product_electronics, sample_order_large)

        assert pricing["original_total"] == 150.0
        assert pricing["final_total"] < pricing["original_total"]
        assert len(pricing["applied_discounts"]) > 0

        discount = pricing["applied_discounts"][0]
        assert discount["rule_id"] == "gold_customer_discount"
        assert discount["discount_percent"] == 15
        assert pricing["final_total"] == 127.5  # 150 * 0.85

    def test_gold_customer_no_discount_small_order(self, engine, sample_order_small):
        """Test that gold customers don't get discount on small orders."""
        # Use a gold customer that doesn't qualify for loyal customer bonus
        gold_customer_new = {
            "id": "cust_gold_new_001",
            "tier": "gold",
            "purchase_count": 15,  # Less than 20 to avoid loyal customer bonus
            "total_spent": 800.0,  # Less than 1000 to avoid loyal customer bonus
            "signup_date": "2023-01-15",
        }

        # Use high inventory product to avoid clearance discount
        high_inventory_product = {
            "id": "prod_electronics_002",
            "category": "electronics",
            "price": 299.99,
            "inventory_count": 100,  # High inventory to avoid clearance
            "brand": "TechCorp",
        }

        pricing = engine.calculate_price(gold_customer_new, high_inventory_product, sample_order_small)

        assert pricing["original_total"] == 75.0
        assert pricing["final_total"] == pricing["original_total"]
        assert len(pricing["applied_discounts"]) == 0

    def test_bulk_order_discount(self, engine, sample_customer_silver, sample_product_electronics, sample_order_bulk):
        """Test bulk order discount for 10+ items."""
        pricing = engine.calculate_price(sample_customer_silver, sample_product_electronics, sample_order_bulk)

        assert pricing["original_total"] == 200.0
        assert pricing["final_total"] < pricing["original_total"]
        assert len(pricing["applied_discounts"]) > 0

        discount = pricing["applied_discounts"][0]
        assert discount["rule_id"] == "bulk_order_discount"
        assert discount["discount_percent"] == 10
        assert pricing["final_total"] == 180.0  # 200 * 0.90

    def test_clearance_electronics(
        self, engine, sample_customer_silver, sample_product_electronics, sample_order_small
    ):
        """Test clearance discount for low-inventory electronics."""
        pricing = engine.calculate_price(sample_customer_silver, sample_product_electronics, sample_order_small)

        # Should get clearance discount since inventory_count < 5
        assert pricing["original_total"] == 75.0
        assert pricing["final_total"] < pricing["original_total"]
        assert len(pricing["applied_discounts"]) > 0

        discount = pricing["applied_discounts"][0]
        assert discount["rule_id"] == "clearance_electronics"
        assert discount["discount_percent"] == 25
        assert pricing["final_total"] == 56.25  # 75 * 0.75

    def test_holiday_season_discount(self, engine, sample_customer_silver, sample_product_electronics):
        """Test holiday season promotion."""
        holiday_order = {
            "id": "order_holiday_001",
            "total": 75.0,
            "item_count": 2,
            "shipping_zip": "10001",
            "date": "2023-12-15",  # December = holiday season
        }

        # Modify product to have high inventory to avoid clearance discount
        high_inventory_product = sample_product_electronics.copy()
        high_inventory_product["inventory_count"] = 100

        pricing = engine.calculate_price(sample_customer_silver, high_inventory_product, holiday_order)

        assert len(pricing["applied_discounts"]) > 0
        discount = pricing["applied_discounts"][0]
        assert discount["rule_id"] == "holiday_promotion"
        assert discount["discount_percent"] == 12

    def test_loyal_customer_bonus(self, engine, sample_product_electronics, sample_order_large):
        """Test loyal customer bonus for high purchase count and spend."""
        loyal_customer = {
            "id": "cust_loyal_001",
            "tier": "silver",  # Even silver customers can get this
            "purchase_count": 25,
            "total_spent": 1200.0,
            "signup_date": "2020-01-15",
        }

        # Modify product to avoid clearance discount
        high_inventory_product = sample_product_electronics.copy()
        high_inventory_product["inventory_count"] = 100

        # Modify order to avoid holiday discount
        non_holiday_order = sample_order_large.copy()
        non_holiday_order["date"] = "2023-08-15"

        pricing = engine.calculate_price(loyal_customer, high_inventory_product, non_holiday_order)

        assert len(pricing["applied_discounts"]) > 0
        discount = pricing["applied_discounts"][0]
        assert discount["rule_id"] == "loyal_customer_bonus"
        assert discount["discount_percent"] == 20

    def test_shipping_calculations(self, engine, sample_customer_silver, sample_product_electronics):
        """Test shipping cost calculations."""
        # Test free shipping for orders over $75
        large_order = {
            "id": "order_001",
            "total": 100.0,
            "item_count": 1,
            "shipping_zip": "10001",
            "date": "2023-08-15",
        }

        # Modify product to avoid clearance
        high_inventory_product = sample_product_electronics.copy()
        high_inventory_product["inventory_count"] = 100

        pricing = engine.calculate_price(sample_customer_silver, high_inventory_product, large_order)
        assert pricing["shipping_cost"] == 0.0

        # Test regular shipping for small orders
        small_order = {"id": "order_002", "total": 50.0, "item_count": 1, "shipping_zip": "10001", "date": "2023-08-15"}

        pricing = engine.calculate_price(sample_customer_silver, high_inventory_product, small_order)
        assert pricing["shipping_cost"] == 9.99

        # Test west coast shipping premium
        west_coast_order = small_order.copy()
        west_coast_order["shipping_zip"] = "90210"

        pricing = engine.calculate_price(sample_customer_silver, high_inventory_product, west_coast_order)
        assert pricing["shipping_cost"] == 11.99

    def test_rule_priority(self, engine, sample_product_electronics):
        """Test that rules are applied in priority order (first match wins)."""
        # Create a customer and order that could match multiple rules
        multi_rule_customer = {
            "id": "cust_multi_001",
            "tier": "gold",  # Could match gold customer rule
            "purchase_count": 25,  # Could match loyal customer rule
            "total_spent": 1500.0,
            "signup_date": "2020-01-15",
        }

        bulk_holiday_order = {
            "id": "order_multi_001",
            "total": 150.0,
            "item_count": 12,  # Could match bulk order rule
            "shipping_zip": "10001",
            "date": "2023-12-15",  # Could match holiday rule
        }

        pricing = engine.calculate_price(multi_rule_customer, sample_product_electronics, bulk_holiday_order)

        # Should get the first matching rule by priority (gold_customer_discount has ordering: 1)
        assert len(pricing["applied_discounts"]) > 0
        discount = pricing["applied_discounts"][0]
        assert discount["rule_id"] == "gold_customer_discount"

    def test_no_applicable_rules(self, engine, sample_product_electronics):
        """Test behavior when no rules apply."""
        basic_customer = {
            "id": "cust_basic_001",
            "tier": "bronze",
            "purchase_count": 1,
            "total_spent": 50.0,
            "signup_date": "2023-12-01",
        }

        small_summer_order = {
            "id": "order_basic_001",
            "total": 40.0,  # Too small for most discounts
            "item_count": 1,  # Not bulk
            "shipping_zip": "10001",
            "date": "2023-07-15",  # Not holiday season
        }

        # Modify product to avoid clearance
        high_inventory_product = sample_product_electronics.copy()
        high_inventory_product["inventory_count"] = 100

        pricing = engine.calculate_price(basic_customer, high_inventory_product, small_summer_order)

        assert pricing["original_total"] == 40.0
        assert pricing["final_total"] == 40.0
        assert len(pricing["applied_discounts"]) == 0
        assert pricing["savings"] == 0.0

    def test_pricing_structure(self, engine, sample_customer_gold, sample_product_electronics, sample_order_large):
        """Test that pricing result has correct structure."""
        pricing = engine.calculate_price(sample_customer_gold, sample_product_electronics, sample_order_large)

        # Check required fields
        required_fields = [
            "original_total",
            "final_total",
            "shipping_cost",
            "grand_total",
            "applied_discounts",
            "savings",
        ]

        for field in required_fields:
            assert field in pricing, f"Missing field: {field}"

        # Check types
        assert isinstance(pricing["original_total"], (int, float))
        assert isinstance(pricing["final_total"], (int, float))
        assert isinstance(pricing["shipping_cost"], (int, float))
        assert isinstance(pricing["grand_total"], (int, float))
        assert isinstance(pricing["applied_discounts"], list)
        assert isinstance(pricing["savings"], (int, float))

        # Check logical consistency
        assert pricing["final_total"] <= pricing["original_total"]
        assert pricing["savings"] == pricing["original_total"] - pricing["final_total"]
        assert pricing["grand_total"] == pricing["final_total"] + pricing["shipping_cost"]

    def test_edge_cases(self, engine):
        """Test edge cases and error handling."""
        customer = {"id": "test", "tier": "gold", "purchase_count": 0, "total_spent": 0.0, "signup_date": "2023-01-01"}
        product = {"id": "test", "category": "other", "price": 0.0, "inventory_count": 0, "brand": "test"}

        # Zero dollar order
        zero_order = {"id": "test", "total": 0.0, "item_count": 0, "shipping_zip": "00000", "date": "2023-01-01"}
        pricing = engine.calculate_price(customer, product, zero_order)
        assert pricing["original_total"] == 0.0

        # Invalid date format
        invalid_date_order = {"id": "test", "total": 50.0, "item_count": 1, "shipping_zip": "10001", "date": "invalid"}
        pricing = engine.calculate_price(customer, product, invalid_date_order)
        # Should not crash, holiday season should return False for invalid dates
        assert "original_total" in pricing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
