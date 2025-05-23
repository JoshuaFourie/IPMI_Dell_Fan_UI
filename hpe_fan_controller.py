import requests
import json
import time
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
import threading

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class HPEiLOController:
    def __init__(self, server_config, log_callback=None):
        self.server_config = server_config
        self.log_callback = log_callback
        self.session = None
        self.session_key = None
        self.base_url = f"https://{server_config['ip']}"
        
    def log_message(self, message):
        """Log message with timestamp"""
        if self.log_callback:
            timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            log_entry = f"[{timestamp}] [{self.server_config['name']}] {message}"
            self.log_callback(log_entry)
    
    def create_session(self):
        """Create authenticated session with iLO"""
        try:
            self.session = requests.Session()
            self.session.verify = False  # Disable SSL verification for self-signed certs
            self.session.auth = HTTPBasicAuth(
                self.server_config['username'], 
                self.server_config['password']
            )
            
            # Test connection with a simple GET request
            response = self.session.get(
                f"{self.base_url}/redfish/v1/Systems/1",
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_message("✓ Session created successfully")
                return True
            else:
                self.log_message(f"✗ Authentication failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_message(f"✗ Connection failed: {str(e)}")
            return False
    
    def test_connection(self):
        """Test connection to iLO"""
        self.log_message("Testing connection to iLO...")
        return self.create_session()
    
    def get_thermal_status(self):
        """Get current thermal status including fans and temperatures"""
        if not self.session:
            if not self.create_session():
                return None
                
        try:
            response = self.session.get(
                f"{self.base_url}/redfish/v1/Chassis/1/Thermal",
                timeout=10
            )
            
            if response.status_code == 200:
                thermal_data = response.json()
                return thermal_data
            else:
                self.log_message(f"✗ Failed to get thermal status: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.log_message(f"✗ Error getting thermal status: {str(e)}")
            return None
    
    def get_temperatures(self):
        """Get current temperature readings"""
        thermal_data = self.get_thermal_status()
        if not thermal_data:
            return None
            
        temperatures = {}
        if 'Temperatures' in thermal_data:
            for temp in thermal_data['Temperatures']:
                name = temp.get('Name', 'Unknown')
                reading = temp.get('ReadingCelsius')
                if reading is not None:
                    temperatures[name] = reading
                    
        return temperatures
    
    def get_fan_status(self):
        """Get current fan status and speeds"""
        thermal_data = self.get_thermal_status()
        if not thermal_data:
            return None
            
        fans = {}
        if 'Fans' in thermal_data:
            for fan in thermal_data['Fans']:
                name = fan.get('Name', 'Unknown')
                rpm = fan.get('Reading')
                percent = fan.get('ReadingPercent')
                status = fan.get('Status', {}).get('Health', 'Unknown')
                
                fans[name] = {
                    'rpm': rpm,
                    'percent': percent,
                    'status': status
                }
                
        return fans
    
    def set_fan_control_mode(self, mode='Manual'):
        """Set fan control mode (Manual or Automatic)"""
        if not self.session:
            if not self.create_session():
                return False
                
        try:
            # This endpoint may vary by iLO version
            payload = {"FanControlMode": mode}
            
            response = self.session.patch(
                f"{self.base_url}/redfish/v1/Managers/1/ThermalSubsystem/FanControl",
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                self.log_message(f"✓ Fan control mode set to {mode}")
                return True
            else:
                self.log_message(f"✗ Failed to set fan control mode: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_message(f"✗ Error setting fan control mode: {str(e)}")
            return False
    
    def set_fan_speed_percent(self, fan_index=None, speed_percent=30):
        """Set specific fan speed percentage"""
        if not self.session:
            if not self.create_session():
                return False
                
        try:
            # First try to set manual mode
            self.set_fan_control_mode('Manual')
            
            # Prepare payload for fan speed
            if fan_index is not None:
                # Set specific fan
                payload = {
                    "Fans": [{
                        "@odata.id": f"/redfish/v1/Chassis/1/Thermal#/Fans/{fan_index}",
                        "FanSpeedPercent": speed_percent
                    }]
                }
            else:
                # Set all fans (this approach may vary by iLO version)
                thermal_data = self.get_thermal_status()
                if not thermal_data or 'Fans' not in thermal_data:
                    self.log_message("✗ Cannot get fan information")
                    return False
                    
                fans_payload = []
                for i, fan in enumerate(thermal_data['Fans']):
                    fans_payload.append({
                        "@odata.id": f"/redfish/v1/Chassis/1/Thermal#/Fans/{i}",
                        "FanSpeedPercent": speed_percent
                    })
                
                payload = {"Fans": fans_payload}
            
            response = self.session.patch(
                f"{self.base_url}/redfish/v1/Chassis/1/Thermal",
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                target = f"fan {fan_index}" if fan_index is not None else "all fans"
                self.log_message(f"✓ Set {target} to {speed_percent}%")
                return True
            else:
                self.log_message(f"✗ Failed to set fan speed: {response.status_code}")
                # Try alternative method for older iLO versions
                return self.set_thermal_profile_custom(speed_percent)
                
        except requests.exceptions.RequestException as e:
            self.log_message(f"✗ Error setting fan speed: {str(e)}")
            return False
    
    def set_thermal_profile_custom(self, min_fan_speed=30):
        """Set custom thermal profile with minimum fan speed"""
        if not self.session:
            if not self.create_session():
                return False
                
        try:
            payload = {
                "ThermalProfile": "Custom",
                "CustomFanProfile": {
                    "MinimumFanSpeed": min_fan_speed,
                    "MaximumFanSpeed": 100
                }
            }
            
            response = self.session.patch(
                f"{self.base_url}/redfish/v1/Managers/1/ThermalSubsystem",
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                self.log_message(f"✓ Set custom thermal profile with {min_fan_speed}% minimum")
                return True
            else:
                self.log_message(f"✗ Failed to set thermal profile: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_message(f"✗ Error setting thermal profile: {str(e)}")
            return False
    
    def set_thermal_profile(self, profile='Acoustic'):
        """Set predefined thermal profile (Performance, Acoustic, Custom)"""
        if not self.session:
            if not self.create_session():
                return False
                
        try:
            payload = {"ThermalProfile": profile}
            
            response = self.session.patch(
                f"{self.base_url}/redfish/v1/Managers/1/ThermalSubsystem",
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                self.log_message(f"✓ Thermal profile set to {profile}")
                return True
            else:
                self.log_message(f"✗ Failed to set thermal profile: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_message(f"✗ Error setting thermal profile: {str(e)}")
            return False
    
    def enable_automatic_control(self):
        """Enable automatic thermal control"""
        success1 = self.set_fan_control_mode('Automatic')
        success2 = self.set_thermal_profile('Performance')
        return success1 or success2
    
    def disable_automatic_control(self):
        """Disable automatic thermal control"""
        return self.set_fan_control_mode('Manual')
    
    def get_system_info(self):
        """Get basic system information"""
        if not self.session:
            if not self.create_session():
                return None
                
        try:
            response = self.session.get(
                f"{self.base_url}/redfish/v1/Systems/1",
                timeout=10
            )
            
            if response.status_code == 200:
                system_data = response.json()
                return {
                    'manufacturer': system_data.get('Manufacturer', 'Unknown'),
                    'model': system_data.get('Model', 'Unknown'),
                    'serial': system_data.get('SerialNumber', 'Unknown'),
                    'power_state': system_data.get('PowerState', 'Unknown')
                }
            else:
                self.log_message(f"✗ Failed to get system info: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.log_message(f"✗ Error getting system info: {str(e)}")
            return None
    
    def monitor_temperatures(self, threshold=45, callback=None):
        """Monitor temperatures and return current status"""
        temperatures = self.get_temperatures()
        if not temperatures:
            return None
            
        max_temp = max(temperatures.values()) if temperatures else 0
        above_threshold = max_temp > threshold
        
        status = {
            'max_temperature': max_temp,
            'above_threshold': above_threshold,
            'temperatures': temperatures,
            'threshold': threshold
        }
        
        if callback:
            callback(status)
            
        return status
    
    def close_session(self):
        """Close the session"""
        if self.session:
            try:
                self.session.close()
                self.log_message("✓ Session closed")
            except:
                pass
        self.session = None