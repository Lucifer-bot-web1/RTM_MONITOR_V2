import subprocess
import hashlib
import platform
from datetime import datetime


class SecurityManager:
    """
    RTM Enterprise Security Module
    Handles Hardware Locking & License Verification
    """

    # Secret Key for Digital Seal (Don't change this after deployment)
    LICENSE_SECRET = "RTM_SECURE_SALT_V2_2026"

    @staticmethod
    def get_system_id():
        """Get Motherboard Serial Number (Unique Hardware ID)"""
        try:
            if platform.system() == "Windows":
                # Command to get Board Serial
                cmd = "wmic baseboard get serialnumber"
                serial = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()

                # If Serial is empty (Common in some VMs), get CPU ID
                if not serial:
                    serial = subprocess.check_output("wmic cpu get processorid", shell=True).decode().split('\n')[
                        1].strip()

                # Hash it so it looks clean
                return hashlib.sha256(serial.encode()).hexdigest()
            else:
                return "NON_WINDOWS_GENERIC_ID"
        except:
            return "UNKNOWN_HW_ID_000"

    @staticmethod
    def generate_license_hash(expiry_date_str, hw_id):
        """
        Create Digital Seal:
        Hash( Date + HardwareID + SecretKey )
        """
        raw_data = f"{expiry_date_str}|{hw_id}|{SecurityManager.LICENSE_SECRET}"
        return hashlib.sha256(raw_data.encode()).hexdigest()

    @staticmethod
    def verify_license(user):
        """
        Check if License is Valid, Expired, or Tampered
        Returns: (True/False, "Message")
        """
        if not user or not user.expires_at or not user.license_hash:
            return False, "License Missing or Invalid."

        # 1. Check Date Expiry
        days_left = (user.expires_at - datetime.now()).days
        if days_left < 0:
            return False, "License Expired. Contact Support."

        # 2. Check Integrity (Hardware Lock + Tamper Proof)
        current_hw = SecurityManager.get_system_id()
        expiry_str = user.expires_at.strftime('%Y-%m-%d')

        # Re-calculate what the seal SHOULD be
        calculated_seal = SecurityManager.generate_license_hash(expiry_str, current_hw)

        # Compare with what is in the Database
        if user.license_hash != calculated_seal:
            return False, "CRITICAL: System Mismatch or Data Tampered!"

        return True, "Valid"

    @staticmethod
    def is_system_expired(user=None):
        # Helper function for Routes
        if not user: return False
        valid, msg = SecurityManager.verify_license(user)
        return not valid