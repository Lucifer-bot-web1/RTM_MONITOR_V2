import bcrypt
from datetime import datetime, timezone
from core.database import User


class SecurityManager:
    @staticmethod
    def hash_password(plain_password):
        return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_password(plain_password, hashed_password):
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except ValueError:
            return False

    @staticmethod
    def is_system_expired():
        """
        Checks if the system is valid.
        Returns False if at least one Admin has a valid future date OR no expiry set.
        """
        admins = User.query.filter_by(role='ADMIN', active=True).all()

        # If no admins exist yet (Fresh Install), allow access to create one
        if not admins:
            return False

        now = datetime.now(timezone.utc)

        for admin in admins:
            # FIX: If expires_at is None, it means LIFETIME validity.
            if admin.expires_at is None:
                return False

                # Check date
            if admin.expires_at.replace(tzinfo=timezone.utc) > now:
                return False

        return True  # All admins expired