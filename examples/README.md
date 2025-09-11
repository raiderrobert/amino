# Amino Examples

This directory contains comprehensive examples demonstrating how to use Amino to build flexible rule engines for different domains. Each example shows how to empower non-technical users to create and modify business logic without code deployments.

## 🛒 E-commerce Pricing Engine

**Use Case**: Dynamic pricing and promotions system where business teams can create discount rules.

**Key Features**:
- Customer tier-based pricing (gold, silver customers)
- Bulk order discounts and seasonal promotions
- Inventory-based clearance rules
- Loyalty program integration

**[View Example →](./ecommerce/)**

```python
# Example rule: Gold customers get 15% off orders over $100
"customer.tier = 'gold' and order.total > 100"
```

---

## 🛡️ Content Moderation System

**Use Case**: AI-powered content moderation where safety teams can rapidly respond to new threats.

**Key Features**:
- Multi-signal toxicity detection (ML + user reports)
- Crisis intervention for self-harm content
- Graduated responses (flag, quarantine, remove)
- New user restrictions and spam detection

**[View Example →](./content_moderation/)**

```python
# Example rule: Immediate removal for extremely toxic content
"toxicity_score(content.text) > 0.9"
```

---

## 🏠 IoT Smart Home Automation

**Use Case**: Smart home automation system where users can customize device behavior.

**Key Features**:
- Multi-device coordination (climate, lights, security)
- Context-aware automation (occupancy, time, weather)
- Energy optimization and usage alerts
- Personalized comfort settings

**[View Example →](./iot_automation/)**

```python
# Example rule: Auto-lights in evening when dark
"user_preferences.auto_lights and home_context.time_of_day = 'evening' and sensor_data.light_level < 30"
```

---

## 🚀 Getting Started

Each example is self-contained and can be run independently:

### Prerequisites

```bash
# Install Amino (from the root directory)
pip install -e .

# Or if using the examples directly
pip install amino
```

### Running Examples

```bash
# E-commerce pricing demo
cd examples/ecommerce
python pricing_engine.py

# Content moderation demo
cd examples/content_moderation
python moderation_system.py

# IoT automation demo
cd examples/iot_automation
python smart_home.py
```

### Running Tests

```bash
# Run validation for all examples
uv run python examples/validate_examples.py

# Run tests for a specific example
uv run python -m pytest examples/ecommerce/
uv run python -m pytest examples/content_moderation/
uv run python -m pytest examples/iot_automation/

# Run validation for just one example
uv run python examples/validate_examples.py ecommerce
```

## 📁 Example Structure

Each example includes:

- **`schema.amino`** - Defines data structures and available functions
- **`*.py`** - Main implementation with rule engine and demo
- **`test_*.py`** - Comprehensive test suite validating functionality
- **`README.md`** - Detailed explanation and usage guide

## 🎯 Key Patterns Demonstrated

### 1. **Rule Priority and Matching**
- **First Match**: High-priority safety rules override others
- **All Matches**: Process multiple applicable rules
- **Ordered Evaluation**: Business priority determines rule order

### 2. **Custom Functions**
- **ML Integration**: Sentiment analysis, toxicity detection
- **Business Logic**: Discount calculations, shipping costs
- **External APIs**: Weather data, notification services

### 3. **Rich Data Context**
- **Multi-entity Rules**: Combine user, product, and order data
- **Temporal Logic**: Time-based and seasonal rules
- **State Management**: Device status and user preferences

### 4. **Action Systems**
- **Graduated Responses**: Different action types based on severity
- **Metadata-Driven**: Rule metadata defines action parameters
- **Human Escalation**: Complex cases route to manual review

## 🔧 Customization Tips

### Adding New Rules

```python
new_rule = {
    "id": "my_custom_rule",
    "rule": "field.value > 100 and custom_function(data)",
    "ordering": 1,
    "metadata": {
        "action": "custom_action",
        "description": "My business rule"
    }
}
```

### Custom Functions

```python
def my_custom_logic(value: float) -> bool:
    # Your business logic here
    return value > threshold

schema.add_function('custom_function', my_custom_logic)
```

### Schema Extensions

```amino
# Add new data structures
struct my_data {
    field1: str,
    field2: int,
    field3: bool
}

# Add new functions
my_function: (str, int) -> bool
```

## 🎓 Learning Path

1. **Start with E-commerce** - Shows basic rule evaluation and business logic
2. **Explore Content Moderation** - Demonstrates ML integration and safety patterns
3. **Try IoT Automation** - Shows real-time processing and device coordination

## 📝 Next Steps

- Modify the example rules to see different behaviors
- Add your own custom functions and data fields
- Integrate with your existing systems and databases
- Build a web UI for non-technical users to manage rules

## 💡 Need Help?

- Check the main [Amino README](../README.md) for core concepts
- Review the [API documentation](../docs/) for detailed usage
- Look at test files for additional examples
- Open an issue for questions or suggestions

---

*These examples demonstrate the power of Amino to make complex business logic accessible to domain experts, enabling rapid iteration without technical bottlenecks.*
