#!/usr/bin/env python3
"""
IoT Smart Home Automation Example

This example demonstrates how to use Amino to build a flexible IoT automation
system where users can create custom rules for their smart home devices without
technical programming knowledge.
"""

import random
from datetime import datetime
from typing import Any

import amino


class SmartHomeSystem:
    """IoT automation system with user-configurable rules."""

    def __init__(self):
        # Load the schema
        with open("examples/iot_automation/schema.amino") as f:
            schema_content = f.read()

        self.schema = amino.Schema(schema_content)

        # Register utility functions
        self.schema.add_function("time_in_range", self._time_in_range)
        self.schema.add_function("calculate_energy_cost", self._calculate_energy_cost)
        self.schema.add_function("get_weather_forecast", self._get_weather_forecast)
        self.schema.add_function("send_notification", self._send_notification)
        self.schema.add_function("get_average_consumption", self._get_average_consumption)
        self.schema.add_function("temp_above_preferred", self._temp_above_preferred)
        self.schema.add_function("power_above_threshold", self._power_above_threshold)

        # User-defined automation rules
        self.automation_rules = [
            {
                "id": "climate_control_home",
                "rule": "home_context.occupancy_status = 'home' and temp_above_preferred(sensor_data.temperature, user_preferences.preferred_temp_home, 2.0)",
                "ordering": 1,
                "metadata": {
                    "action": "adjust_thermostat",
                    "target_temp": "user_preferences.preferred_temp_home",
                    "description": "Cool down when home and too warm",
                },
            },
            {
                "id": "climate_control_away",
                "rule": "home_context.occupancy_status = 'away' and home_context.energy_saving_mode",
                "ordering": 2,
                "metadata": {
                    "action": "adjust_thermostat",
                    "target_temp": "user_preferences.preferred_temp_away",
                    "description": "Energy saving when away",
                },
            },
            {
                "id": "security_motion_alert",
                "rule": "sensor_data.motion_detected and home_context.security_mode = 'armed'",
                "ordering": 3,
                "metadata": {
                    "action": "security_alert",
                    "notification_message": "Motion detected while security system armed!",
                    "description": "Security alert for motion when armed",
                },
            },
            {
                "id": "auto_lights_evening",
                "rule": "user_preferences.auto_lights and home_context.time_of_day = 'evening' and sensor_data.light_level < 30",
                "ordering": 4,
                "metadata": {
                    "action": "turn_on_lights",
                    "brightness": 70,
                    "description": "Automatically turn on lights in evening when dark",
                },
            },
            {
                "id": "auto_lights_morning",
                "rule": "home_context.time_of_day = 'morning' and home_context.occupancy_status = 'home'",
                "ordering": 5,
                "metadata": {
                    "action": "turn_on_lights",
                    "brightness": 40,
                    "description": "Gentle morning lights when home",
                },
            },
            {
                "id": "high_energy_warning",
                "rule": "power_above_threshold(device_state.power_consumption, get_average_consumption(device_state.device_id, 7), 1.5)",
                "ordering": 6,
                "metadata": {
                    "action": "send_notification",
                    "notification_message": "High energy usage detected on device",
                    "description": "Alert for unusual energy consumption",
                },
            },
            {
                "id": "air_quality_alert",
                "rule": "sensor_data.air_quality_index > 150",
                "ordering": 7,
                "metadata": {
                    "action": "air_quality_response",
                    "turn_on_purifier": True,
                    "notification_message": "Poor air quality detected - turning on air purifier",
                    "description": "Respond to poor air quality",
                },
            },
            {
                "id": "sleep_mode_activation",
                "rule": "home_context.time_of_day = 'night' and home_context.occupancy_status = 'sleep'",
                "ordering": 8,
                "metadata": {
                    "action": "activate_sleep_mode",
                    "target_temp": "user_preferences.preferred_temp_sleep",
                    "lights_off": True,
                    "description": "Activate sleep mode at bedtime",
                },
            },
            {
                "id": "extreme_temp_alert",
                "rule": "sensor_data.temperature > user_preferences.notification_threshold_temp or sensor_data.temperature < 10",
                "ordering": 9,
                "metadata": {
                    "action": "temperature_alert",
                    "notification_message": "Extreme temperature detected!",
                    "description": "Alert for dangerously high/low temperatures",
                },
            },
        ]

        # Track notifications sent
        self.notifications = []

    def _time_in_range(self, current_time: str, start_time: str, end_time: str) -> bool:
        """Check if current time is within specified range."""
        try:
            current = datetime.strptime(current_time, "%H:%M").time()
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()

            if start <= end:
                return start <= current <= end
            else:  # Range crosses midnight
                return current >= start or current <= end
        except:
            return False

    def _calculate_energy_cost(self, power_kw: float, hours: float) -> float:
        """Calculate energy cost based on power consumption."""
        rate_per_kwh = 0.12  # $0.12 per kWh
        return power_kw * hours * rate_per_kwh

    def _get_weather_forecast(self, location: str) -> str:
        """Mock weather forecast."""
        return random.choice(["sunny", "rainy", "cloudy"])

    def _send_notification(self, user_id: str, message: str) -> bool:
        """Send notification to user."""
        self.notifications.append({"user_id": user_id, "message": message, "timestamp": datetime.now().isoformat()})
        return True

    def _get_average_consumption(self, device_id: str, days: int) -> float:
        """Get average power consumption for device over specified days."""
        # Mock historical data
        base_consumption = {"thermostat": 2.5, "lights": 0.8, "security": 0.3, "fan": 1.2, "blinds": 0.1}

        device_type = device_id.split("_")[0] if "_" in device_id else device_id
        return base_consumption.get(device_type, 1.0)

    def _temp_above_preferred(self, current_temp: float, preferred_temp: float, threshold: float) -> bool:
        """Check if current temperature is above preferred temperature by threshold."""
        return current_temp > (preferred_temp + threshold)

    def _power_above_threshold(self, current_power: float, average_power: float, multiplier: float) -> bool:
        """Check if current power consumption is above average by multiplier."""
        return current_power > (average_power * multiplier)

    def process_iot_data(
        self,
        sensor_data: dict[str, Any],
        device_states: list[dict[str, Any]],
        home_context: dict[str, Any],
        user_preferences: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Process IoT data and determine automation actions."""

        actions = []

        # Process each device state against the rules
        for device_state in device_states:
            # Combine all data for rule evaluation
            automation_data = {
                "sensor_data": sensor_data,
                "device_state": device_state,
                "home_context": home_context,
                "user_preferences": user_preferences,
            }

            # Compile rules for evaluation (process all matching rules)
            compiled_rules = self.schema.compile(self.automation_rules, match={"option": "all"})

            # Evaluate rules against the current state
            results = compiled_rules.eval([{"id": f"automation_{device_state['device_id']}", **automation_data}])

            if results and results[0].results:
                # Process all matching rules
                for matched_rule_id in results[0].results:
                    # Find the rule metadata
                    for rule in self.automation_rules:
                        if rule["id"] == matched_rule_id:
                            metadata = rule["metadata"]

                            action = {
                                "device_id": device_state["device_id"],
                                "rule_id": matched_rule_id,
                                "action_type": metadata["action"],
                                "description": metadata["description"],
                                "timestamp": datetime.now().isoformat(),
                                "parameters": {},
                            }

                            # Add action-specific parameters
                            if "target_temp" in metadata:
                                if metadata["target_temp"].startswith("user_preferences."):
                                    pref_key = metadata["target_temp"].split(".")[-1]
                                    action["parameters"]["target_temperature"] = user_preferences.get(pref_key, 72)
                                else:
                                    action["parameters"]["target_temperature"] = metadata.get("target_temp", 72)

                            if "brightness" in metadata:
                                action["parameters"]["brightness"] = metadata["brightness"]

                            if "notification_message" in metadata:
                                action["parameters"]["message"] = metadata["notification_message"]
                                # Actually send the notification
                                self._send_notification("user_001", metadata["notification_message"])

                            if "turn_on_purifier" in metadata:
                                action["parameters"]["turn_on_purifier"] = metadata["turn_on_purifier"]

                            if "lights_off" in metadata:
                                action["parameters"]["lights_off"] = metadata["lights_off"]

                            actions.append(action)
                            break

        return actions


def main():
    """Demo the IoT automation system."""
    system = SmartHomeSystem()

    # Sample sensor data
    sensor_readings = {
        "device_id": "main_sensor_001",
        "temperature": 78.5,
        "humidity": 65.0,
        "light_level": 25,
        "motion_detected": True,
        "air_quality_index": 180,
        "timestamp": "2023-12-15T19:30:00",
    }

    # Sample device states
    device_states = [
        {
            "device_id": "thermostat_001",
            "device_type": "thermostat",
            "is_online": True,
            "current_setting": 75.0,
            "power_consumption": 3.2,
            "last_updated": "2023-12-15T19:25:00",
        },
        {
            "device_id": "lights_living_room",
            "device_type": "lights",
            "is_online": True,
            "current_setting": 0.0,  # Off
            "power_consumption": 0.0,
            "last_updated": "2023-12-15T18:00:00",
        },
        {
            "device_id": "security_front_door",
            "device_type": "security",
            "is_online": True,
            "current_setting": 1.0,  # Armed
            "power_consumption": 0.3,
            "last_updated": "2023-12-15T17:00:00",
        },
    ]

    # Home context
    home_context = {
        "occupancy_status": "away",  # Nobody home
        "security_mode": "armed",
        "time_of_day": "evening",
        "season": "winter",
        "energy_saving_mode": True,
    }

    # User preferences
    user_preferences = {
        "preferred_temp_home": 72.0,
        "preferred_temp_away": 68.0,
        "preferred_temp_sleep": 65.0,
        "auto_lights": True,
        "energy_conscious": True,
        "notification_threshold_temp": 85.0,
    }

    print("🏠 IoT Smart Home Automation Demo")
    print("=" * 50)

    print("📊 Current Conditions:")
    print(f"   🌡️  Temperature: {sensor_readings['temperature']}°F")
    print(f"   💡 Light Level: {sensor_readings['light_level']}%")
    print(f"   🏃 Motion: {'Detected' if sensor_readings['motion_detected'] else 'None'}")
    print(f"   🌬️  Air Quality: {sensor_readings['air_quality_index']} AQI")
    print(f"   🏠 Status: {home_context['occupancy_status']} | Security: {home_context['security_mode']}")

    # Process the IoT data
    actions = system.process_iot_data(sensor_readings, device_states, home_context, user_preferences)

    print("\n🤖 Automation Actions Triggered:")
    if not actions:
        print("   No actions needed - all systems nominal")
    else:
        for i, action in enumerate(actions, 1):
            action_emoji = {
                "adjust_thermostat": "🌡️",
                "security_alert": "🚨",
                "turn_on_lights": "💡",
                "send_notification": "📱",
                "air_quality_response": "🌬️",
                "activate_sleep_mode": "😴",
                "temperature_alert": "⚠️",
            }.get(action["action_type"], "⚙️")

            print(f"   {action_emoji} {action['description']}")
            print(f"      Device: {action['device_id']}")
            print(f"      Rule: {action['rule_id']}")

            if action["parameters"]:
                print(f"      Parameters: {action['parameters']}")

    # Show notifications
    if system.notifications:
        print("\n📱 Notifications Sent:")
        for notif in system.notifications:
            print(f"   • {notif['message']}")

    print("\n💡 Try different scenarios by modifying:")
    print("   • home_context.occupancy_status = 'home'")
    print("   • sensor_readings.temperature = 65")
    print("   • home_context.security_mode = 'disarmed'")


if __name__ == "__main__":
    main()
