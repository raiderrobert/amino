# IoT Smart Home Automation

This example demonstrates how to build a flexible IoT automation system using Amino, where users can create custom rules for their smart home devices without requiring technical programming knowledge.

## Use Case

A smart home platform needs to:
- Automatically adjust climate, lighting, and security based on occupancy and conditions
- Allow users to customize automation behavior without writing code
- Respond to sensor data in real-time with appropriate actions
- Balance comfort, security, and energy efficiency

## Key Features

- **Multi-Device Coordination**: Rules can involve multiple sensors and actuators
- **Context Awareness**: Decisions based on occupancy, time of day, and user preferences
- **Real-time Processing**: Immediate response to sensor readings and state changes
- **User Customization**: Rules can be easily modified by homeowners

## Schema

The `schema.amino` file defines:
- **Sensor Data**: temperature, humidity, light, motion, air quality
- **Device State**: current settings, power consumption, online status
- **Home Context**: occupancy, security mode, time of day, season
- **User Preferences**: temperature settings, automation preferences
- **Utility Functions**: time ranges, energy calculations, notifications

## Sample Rules

```python
# Climate control when home
"home_context.occupancy_status = 'home' and sensor_data.temperature > user_preferences.preferred_temp_home + 2"

# Security alert for motion when armed
"sensor_data.motion_detected and home_context.security_mode = 'armed'"

# Auto-lights in evening when dark
"user_preferences.auto_lights and home_context.time_of_day = 'evening' and sensor_data.light_level < 30"

# Energy usage warning
"device_state.power_consumption > get_average_consumption(device_state.device_id, 7) * 1.5"

# Air quality response
"sensor_data.air_quality_index > 150"
```

## Automation Actions

- **adjust_thermostat**: Change temperature setting
- **security_alert**: Send motion detection alert
- **turn_on_lights**: Control lighting with brightness
- **send_notification**: Alert user via mobile app
- **air_quality_response**: Turn on air purifier
- **activate_sleep_mode**: Night time optimization

## Running the Example

```bash
cd examples/iot_automation  
python smart_home.py
```

## Expected Output

The demo shows a scenario where the house is in "away" mode with:
- High temperature triggering energy-saving mode
- Motion detection while security armed → Security alert
- Poor air quality → Air purifier activation + notification
- Dark evening conditions → Auto-lights (if enabled)

## Smart Home Benefits

1. **Personalization**: Each family can customize automation to their lifestyle
2. **Energy Efficiency**: Rules can optimize power usage based on occupancy
3. **Security Integration**: Coordinated response across security devices
4. **Comfort Automation**: Proactive climate and lighting adjustments
5. **Easy Modification**: Users can tweak rules through a simple interface

## Extension Ideas

- Weather-based automation (close blinds on sunny days)
- Seasonal rule variations (different summer/winter behavior) 
- Device learning (adjust based on usage patterns)
- Integration with calendar/schedule data
- Voice control rule creation