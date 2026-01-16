from netmiko import ConnectHandler
import json
import os
from config import Config


class SSHManager:
    """
    Handles SSH connections securely.
    Uses drivers.json to determine commands.
    """

    @staticmethod
    def load_drivers():
        driver_path = os.path.join(Config.BASE_DIR, 'network', 'drivers.json')
        with open(driver_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def execute_port_action(ip, username, password, device_type, port, action):
        """
        Action: 'shutdown' or 'no_shutdown'
        """
        drivers = SSHManager.load_drivers()
        driver = drivers.get(device_type, drivers['cisco_ios'])  # Default to Cisco

        device_params = {
            'device_type': device_type if device_type in drivers else 'cisco_ios',
            'host': ip,
            'username': username,
            'password': password,
        }

        try:
            with ConnectHandler(**device_params) as ssh:
                # Enter Config Mode
                if driver['cmd_enter_config']:
                    ssh.send_command(driver['cmd_enter_config'])

                # Select Interface
                cmd_port = driver['cmd_port_mode'].format(port=port)
                ssh.send_command(cmd_port)

                # Execute Action
                cmd_action = driver[f'cmd_{action}']
                output = ssh.send_command(cmd_action)

                # Save
                if driver['cmd_save']:
                    ssh.send_command(driver['cmd_save'])

                return True, f"Success: {output}"
        except Exception as e:
            return False, str(e)