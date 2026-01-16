from datetime import datetime, timezone
from passlib.hash import bcrypt
from core.database import User


class SecurityManager:
    @staticmethod
    def hash_password(password):
        return bcrypt.hash(password)

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return bcrypt.verify(plain_password, hashed_password)

    @staticmethod
    def is_system_expired():
        """
        Checks if the system is expired.
        Logic: If NO active admin exists with a valid future expiry date -> Expired.
        """
        admins = User.query.filter_by(role='ADMIN', active=True).all()
        if not admins:
            return True  # No admins = Locked out/Expired

        now = datetime.now(timezone.utc)
        for admin in admins:
            if admin.expires_at and admin.expires_at.replace(tzinfo=timezone.utc) > now:
                return False  # At least one valid license exists

        return True  # All admins expired