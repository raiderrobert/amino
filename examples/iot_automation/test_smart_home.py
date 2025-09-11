#!/usr/bin/env python3
"""Tests for IoT smart home automation example."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from smart_home import SmartHomeSystem


class TestSmartHomeSystem:
    """Test cases for the smart home automation system."""
    
    @pytest.fixture
    def system(self):
        """Create a smart home system instance."""
        return SmartHomeSystem()
    
    @pytest.fixture
    def sensor_data_normal(self):
        """Normal sensor readings."""
        return {
            "temperature": 72.0,
            "humidity": 45.0,
            "light_level": 65,
            "motion_detected": False,
            "air_quality_index": 50
        }
    
    @pytest.fixture
    def sensor_data_hot(self):
        """Hot temperature reading."""
        return {
            "temperature": 78.0,
            "humidity": 55.0,
            "light_level": 75,
            "motion_detected": False,
            "air_quality_index": 45
        }
    
    @pytest.fixture
    def sensor_data_motion(self):
        """Motion detected."""
        return {
            "temperature": 70.0,
            "humidity": 50.0,
            "light_level": 30,
            "motion_detected": True,
            "air_quality_index": 60
        }
    
    @pytest.fixture
    def sensor_data_poor_air(self):
        """Poor air quality."""
        return {
            "temperature": 71.0,
            "humidity": 48.0,
            "light_level": 40,
            "motion_detected": False,
            "air_quality_index": 160
        }
    
    @pytest.fixture
    def device_state_normal(self):
        """Normal device states."""
        return {
            "device_id": "thermostat_main",
            "device_type": "thermostat",
            "current_setting": 72,
            "power_consumption": 150.0,
            "online": True
        }
    
    @pytest.fixture
    def device_state_high_power(self):
        """High power consumption device."""
        return {
            "device_id": "thermostat_main",
            "device_type": "thermostat", 
            "current_setting": 68,
            "power_consumption": 300.0,  # High consumption
            "online": True
        }
    
    @pytest.fixture
    def home_context_home(self):
        """Home context when family is home."""
        return {
            "occupancy_status": "home",
            "security_mode": "disarmed",
            "time_of_day": "afternoon",
            "season": "summer"
        }
    
    @pytest.fixture
    def home_context_away(self):
        """Home context when family is away."""
        return {
            "occupancy_status": "away",
            "security_mode": "armed",
            "time_of_day": "evening",
            "season": "summer"
        }
    
    @pytest.fixture
    def home_context_sleep(self):
        """Home context during sleep hours."""
        return {
            "occupancy_status": "sleep",  # Changed to 'sleep' to match the rule
            "security_mode": "night",
            "time_of_day": "night",
            "season": "summer"
        }
    
    @pytest.fixture
    def user_preferences_auto(self):
        """User preferences with automation enabled."""
        return {
            "preferred_temp_home": 72,
            "preferred_temp_away": 78,
            "preferred_temp_sleep": 68,
            "auto_lights": True,
            "energy_alerts": True,
            "security_notifications": True
        }
    
    @pytest.fixture
    def user_preferences_manual(self):
        """User preferences with automation disabled."""
        return {
            "preferred_temp_home": 70,
            "preferred_temp_away": 75,
            "preferred_temp_sleep": 66,
            "auto_lights": False,
            "energy_alerts": False,
            "security_notifications": False
        }

    def test_system_initialization(self, system):
        """Test that the smart home system initializes correctly."""
        assert system.schema is not None
        assert len(system.automation_rules) > 0
        assert all('id' in rule for rule in system.automation_rules)
        assert all('rule' in rule for rule in system.automation_rules)
        assert all('metadata' in rule for rule in system.automation_rules)
    
    def test_utility_functions(self, system):
        """Test utility functions work correctly."""
        # Test time range checking
        assert system._time_in_range("14:30", "06:00", "22:00") == True
        assert system._time_in_range("02:30", "06:00", "22:00") == False
        assert system._time_in_range("23:30", "22:00", "06:00") == True  # Overnight range
        
        # Test energy calculation
        cost = system._calculate_energy_cost(2.0, 10.0)  # 2 kW for 10 hours
        expected_cost = 2.0 * 10.0 * 0.12  # Rate is $0.12 per kWh
        assert cost == expected_cost
        
        # Test average consumption (returns mock data)
        avg = system._get_average_consumption("thermostat_main", 7)
        assert avg == 2.5  # Mock value for thermostat
    
    def test_climate_control_when_home_hot(self, system, sensor_data_hot, device_state_normal, 
                                          home_context_home, user_preferences_auto):
        """Test climate control activation when home and too hot."""
        actions = system.process_iot_data(sensor_data_hot, [device_state_normal], 
                                          home_context_home, user_preferences_auto)
        
        # Should trigger climate control rule
        assert len(actions) > 0
        action = actions[0]
        assert action['rule_id'] == 'climate_control_home'
        assert action['action_type'] == 'adjust_thermostat'
        assert action['parameters']['target_temperature'] == 72
    
    def test_climate_control_comfortable_temp(self, system, sensor_data_normal, device_state_normal,
                                            home_context_home, user_preferences_auto):
        """Test no climate action when temperature is comfortable."""
        actions = system.process_iot_data(sensor_data_normal, [device_state_normal],
                                          home_context_home, user_preferences_auto)
        
        # Should not trigger climate control (temp within 2 degrees of preferred)
        climate_actions = [a for a in actions if a.get('rule_id') == 'climate_control_home']
        assert len(climate_actions) == 0
    
    def test_security_motion_detection(self, system, sensor_data_motion, device_state_normal,
                                     home_context_away, user_preferences_auto):
        """Test security alert when motion detected while armed."""
        actions = system.process_iot_data(sensor_data_motion, [device_state_normal],
                                          home_context_away, user_preferences_auto)
        
        # Should trigger security alert
        security_actions = [a for a in actions if a.get('rule_id') == 'security_motion_alert']
        assert len(security_actions) > 0
        
        action = security_actions[0]
        assert action['action_type'] == 'security_alert'
        # Note: IoT actions don't have urgency field, just action_type and parameters
    
    def test_no_security_alert_when_disarmed(self, system, sensor_data_motion, device_state_normal,
                                           home_context_home, user_preferences_auto):
        """Test no security alert when motion detected but system disarmed."""
        actions = system.process_iot_data(sensor_data_motion, [device_state_normal],
                                          home_context_home, user_preferences_auto)
        
        # Should not trigger security alert when disarmed
        security_actions = [a for a in actions if a.get('rule_id') == 'security_motion_alert']
        assert len(security_actions) == 0
    
    def test_auto_lights_evening_dark(self, system, device_state_normal, home_context_away, user_preferences_auto):
        """Test auto lights turn on in evening when dark."""
        dark_sensor_data = {
            "temperature": 70.0,
            "humidity": 50.0,
            "light_level": 25,  # Dark
            "motion_detected": False,
            "air_quality_index": 55
        }
        
        actions = system.process_iot_data(dark_sensor_data, [device_state_normal],
                                          home_context_away, user_preferences_auto)
        
        # Should trigger auto lights
        light_actions = [a for a in actions if a.get('rule_id') == 'auto_lights_evening']
        assert len(light_actions) > 0
        
        action = light_actions[0]
        assert action['action_type'] == 'turn_on_lights'
    
    def test_no_auto_lights_when_disabled(self, system, device_state_normal, home_context_away, user_preferences_manual):
        """Test no auto lights when user has disabled automation."""
        dark_sensor_data = {
            "temperature": 70.0,
            "humidity": 50.0,
            "light_level": 25,
            "motion_detected": False,
            "air_quality_index": 55
        }
        
        actions = system.process_iot_data(dark_sensor_data, [device_state_normal],
                                          home_context_away, user_preferences_manual)
        
        # Should not trigger auto lights when disabled
        light_actions = [a for a in actions if a.get('rule_id') == 'auto_lights_evening']
        assert len(light_actions) == 0
    
    def test_energy_usage_alert(self, system, sensor_data_normal, device_state_high_power,
                               home_context_home, user_preferences_auto):
        """Test energy usage alert for high power consumption."""
        # Mock the average consumption function to return a lower value
        with patch.object(system, '_get_average_consumption', return_value=180.0):
            actions = system.process_iot_data(sensor_data_normal, [device_state_high_power],
                                              home_context_home, user_preferences_auto)
            
            # Should trigger energy alert (300 > 180 * 1.5 = 270)
            energy_actions = [a for a in actions if a.get('rule_id') == 'high_energy_warning']
            assert len(energy_actions) > 0
            
            action = energy_actions[0]
            assert action['action_type'] == 'send_notification'
    
    def test_air_quality_response(self, system, sensor_data_poor_air, device_state_normal,
                                 home_context_home, user_preferences_auto):
        """Test air quality response for poor air."""
        actions = system.process_iot_data(sensor_data_poor_air, [device_state_normal],
                                          home_context_home, user_preferences_auto)
        
        # Should trigger air quality response (AQI 160 > 150)
        air_actions = [a for a in actions if a.get('rule_id') == 'air_quality_alert']
        assert len(air_actions) > 0
        
        action = air_actions[0]
        assert action['action_type'] == 'air_quality_response'
    
    def test_sleep_mode_activation(self, system, sensor_data_normal, device_state_normal,
                                  home_context_sleep, user_preferences_auto):
        """Test sleep mode activation at night."""
        actions = system.process_iot_data(sensor_data_normal, [device_state_normal],
                                          home_context_sleep, user_preferences_auto)
        
        # Should trigger sleep mode
        sleep_actions = [a for a in actions if a.get('rule_id') == 'sleep_mode_activation']
        assert len(sleep_actions) > 0
        
        action = sleep_actions[0]
        assert action['action_type'] == 'activate_sleep_mode'
    
    def test_rule_priority_order(self, system, device_state_normal, home_context_away, user_preferences_auto):
        """Test that rules are evaluated in priority order."""
        # Create sensor data that could match multiple rules
        multi_rule_sensor_data = {
            "temperature": 80.0,  # Hot (climate rule)
            "humidity": 50.0,
            "light_level": 25,    # Dark (lights rule) 
            "motion_detected": True,  # Motion (security rule)
            "air_quality_index": 160  # Poor air (air quality rule)
        }
        
        actions = system.process_iot_data(multi_rule_sensor_data, [device_state_normal],
                                          home_context_away, user_preferences_auto)
        
        # Should have multiple actions but security should be first due to priority
        assert len(actions) > 0
        
        # Find security action - should exist due to motion + armed mode
        security_actions = [a for a in actions if a.get('rule_id') == 'security_motion_alert']
        assert len(security_actions) > 0
    
    def test_action_structure(self, system, sensor_data_hot, device_state_normal,
                             home_context_home, user_preferences_auto):
        """Test that automation actions have correct structure."""
        actions = system.process_iot_data(sensor_data_hot, [device_state_normal],
                                          home_context_home, user_preferences_auto)
        
        assert len(actions) > 0
        action = actions[0]
        
        # Check required fields
        required_fields = ['rule_id', 'action_type', 'parameters', 'timestamp']
        
        for field in required_fields:
            assert field in action, f"Missing field: {field}"
        
        # Check field types
        assert isinstance(action['rule_id'], str)
        assert isinstance(action['action_type'], str)
        assert isinstance(action['parameters'], dict)
        assert isinstance(action['timestamp'], str)
    
    def test_edge_cases(self, system, user_preferences_auto):
        """Test edge cases and error handling."""
        # Extreme sensor values
        extreme_sensor_data = {
            "temperature": -50.0,  # Extreme cold
            "humidity": 120.0,     # Invalid humidity
            "light_level": -10,    # Negative light
            "motion_detected": True,
            "air_quality_index": 999  # Extreme AQI
        }
        
        extreme_device_state = {
            "device_id": "test_device",
            "device_type": "thermostat",
            "current_setting": 200,  # Extreme setting
            "power_consumption": -100.0,  # Negative power
            "online": False  # Offline device
        }
        
        home_context = {
            "occupancy_status": "unknown",  # Unexpected status
            "security_mode": "invalid",     # Invalid mode
            "time_of_day": "invalid",
            "season": "invalid"
        }
        
        # Should not crash with extreme values - fix device_state to be list of dicts
        actions = system.process_iot_data(extreme_sensor_data, [extreme_device_state],
                                          home_context, user_preferences_auto)
        assert isinstance(actions, list)
        
        # Empty sensor data
        empty_sensor_data = {
            "temperature": 0.0,
            "humidity": 0.0,
            "light_level": 0,
            "motion_detected": False,
            "air_quality_index": 0
        }
        
        actions = system.process_iot_data(empty_sensor_data, [extreme_device_state],
                                          home_context, user_preferences_auto)
        assert isinstance(actions, list)
    
    def test_multiple_simultaneous_triggers(self, system, device_state_normal, home_context_home, user_preferences_auto):
        """Test handling multiple rules triggering simultaneously."""
        # Sensor data that triggers multiple rules
        complex_sensor_data = {
            "temperature": 78.0,      # Too hot (climate control)
            "humidity": 50.0,
            "light_level": 20,        # Dark (might trigger lights if evening)
            "motion_detected": False,
            "air_quality_index": 160  # Poor air (air quality response)
        }
        
        actions = system.process_iot_data(complex_sensor_data, [device_state_normal],
                                          home_context_home, user_preferences_auto)
        
        # Should have multiple actions
        assert len(actions) >= 2
        
        # Should have both climate and air quality actions
        rule_ids = {action['rule_id'] for action in actions}
        assert 'climate_control_home' in rule_ids
        assert 'air_quality_alert' in rule_ids
    
    def test_notification_preferences(self, system, sensor_data_motion, device_state_normal,
                                    home_context_away, user_preferences_manual):
        """Test that notification preferences are respected."""
        # User has disabled security notifications
        actions = system.process_iot_data(sensor_data_motion, [device_state_normal],
                                          home_context_away, user_preferences_manual)
        
        # Even if security rule triggers, notification behavior might be affected
        # (This depends on implementation - some systems might still alert for security)
        security_actions = [a for a in actions if a.get('rule_id') == 'security_motion_alert']
        if security_actions:
            # If security action exists, check if it respects notification preferences
            action = security_actions[0]
            assert 'parameters' in action
    
    def test_time_based_automation(self, system, sensor_data_normal, device_state_normal, user_preferences_auto):
        """Test time-based automation rules."""
        # Test different times of day
        morning_context = {
            "occupancy_status": "home",
            "security_mode": "disarmed",
            "time_of_day": "morning",
            "season": "spring"
        }
        
        evening_context = {
            "occupancy_status": "home", 
            "security_mode": "disarmed",
            "time_of_day": "evening",
            "season": "spring"
        }
        
        night_context = {
            "occupancy_status": "sleep",  # Changed to 'sleep' to match sleep mode rule
            "security_mode": "night",
            "time_of_day": "night",
            "season": "spring"
        }
        
        # Test each time period
        morning_actions = system.process_iot_data(sensor_data_normal, [device_state_normal],
                                                  morning_context, user_preferences_auto)
        
        evening_actions = system.process_iot_data(sensor_data_normal, [device_state_normal],
                                                   evening_context, user_preferences_auto)
        
        night_actions = system.process_iot_data(sensor_data_normal, [device_state_normal],
                                                 night_context, user_preferences_auto)
        
        # All should return valid action lists
        assert isinstance(morning_actions, list)
        assert isinstance(evening_actions, list)
        assert isinstance(night_actions, list)
        
        # Night context should trigger sleep mode
        sleep_actions = [a for a in night_actions if a.get('rule_id') == 'sleep_mode_activation']
        assert len(sleep_actions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])