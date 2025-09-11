# E-commerce Pricing Engine

This example demonstrates how to build a flexible pricing and promotions engine using Amino, where business users can create and modify pricing rules without requiring code changes.

## Use Case

An e-commerce platform needs to:
- Apply different discounts based on customer tiers and purchase history
- Create seasonal promotions and clearance sales
- Implement bulk order discounts
- Allow business teams to adjust rules without developer intervention

## Key Features

- **Dynamic Rule Evaluation**: Rules are evaluated in priority order (first match wins)
- **Custom Functions**: Business logic like holiday detection and shipping calculations
- **Rich Data Context**: Rules can access customer, product, and order data
- **Metadata Support**: Rules carry additional information like discount percentages

## Schema

The `schema.amino` file defines the data structure:
- **Customer**: tier, purchase history, signup date
- **Product**: category, price, inventory levels
- **Order**: total, item count, shipping info

## Sample Rules

```python
# Gold customers get 15% off orders over $100
"customer.tier = 'gold' and order.total > 100"

# 10% off bulk orders (10+ items)
"order.item_count >= 10"

# 25% clearance on low-stock electronics
"product.category = 'electronics' and product.inventory_count < 5"

# Holiday promotion for orders over $50
"is_holiday_season(order.date) and order.total > 50"
```

## Running the Example

```bash
cd examples/ecommerce
python pricing_engine.py
```

## Expected Output

The demo shows different pricing scenarios:
- Gold customer during holiday season → Holiday promotion applied
- Silver customer with bulk order → Bulk discount applied
- Various combinations showing rule priority and matching

## Business Benefits

1. **Rapid Iteration**: Marketing teams can test new promotions instantly
2. **A/B Testing**: Easy to create rule variants for testing
3. **Seasonal Flexibility**: Holiday rules can be added/removed as needed
4. **Audit Trail**: All pricing decisions are traceable to specific rules