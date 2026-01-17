import subprocess
import hashlib
import platform
import uuid
from datetime import datetime


class SecurityManager:
    LICENSE_SECRET = "RTM_SUPER_SECRET_SALT_V99"

    @staticmethod
    def get_system_id():
        """
        Robust Hardware ID Generation.
        Tries WMIC -> CPUID -> MAC Address (UUID)
        """
        serial = ""
        try:
            # Method 1: Windows WMIC (Primary)
            if platform.system() == "Windows":
                try:
                    cmd = "wmic baseboard get serialnumber"
                    serial = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
                except:
                    pass

            # Method 2: UUID (MAC Address Based) - 100% Works if Method 1 fails
            if not serial or "To be filled" in serial:
                serial = str(uuid.getnode())

            return hashlib.sha256(serial.encode()).hexdigest()
        except:
            return "FALLBACK_HW_ID_000"

    @staticmethod
    def generate_license_hash(expiry_date_str, hw_id):
        # Seal = Date + HW_ID + Secret
        raw_data = f"{expiry_date_str}|{hw_id}|{SecurityManager.LICENSE_SECRET}"
        return hashlib.sha256(raw_data.encode()).hexdigest()

    @staticmethod
    def verify_license(user):
        if not user or not user.expires_at or not user.license_hash:
            return False, "License Not Found."

        # 1. Date Check
        days_left = (user.expires_at - datetime.now()).days
        if days_left < 0:
            return False, "License Expired."

        # 2. Hardware/Tamper Check
        current_hw = SecurityManager.get_system_id()
        expiry_str = user.expires_at.strftime('%Y-%m-%d')
        calculated_seal = SecurityManager.generate_license_hash(expiry_str, current_hw)

        if user.license_hash != calculated_seal:
            return False, "CRITICAL: Hardware Mismatch or Date Tampered!"

        return True, "Valid"