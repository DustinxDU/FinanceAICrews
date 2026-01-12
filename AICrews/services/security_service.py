"""
Security Service - 2FA (TOTP), backup codes, and session management
"""

from AICrews.observability.logging import get_logger
import pyotp
import qrcode
import io
import base64
import secrets
import os
import hashlib
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from cryptography.fernet import Fernet

from AICrews.database.models.user import User
from AICrews.database.models.security import UserSecurity
from AICrews.schemas.security import TwoFactorSetupResponse, TwoFactorStatusResponse
from AICrews.services.notification_service import NotificationService

logger = get_logger(__name__)


class TwoFactorAuthService:
    """Service for 2FA (TOTP) operations"""

    def __init__(self, db: Session):
        self.db = db

    def setup_totp(self, user_id: int, app_name: str = "FinanceAICrews") -> TwoFactorSetupResponse:
        """
        Start TOTP setup for user

        Generates:
        - TOTP secret
        - QR code (data URL)
        - 10 backup recovery codes

        Args:
            user_id: User ID
            app_name: Application name for QR code label

        Returns:
            TwoFactorSetupResponse with secret, QR code, and backup codes

        Note:
            - Does NOT enable 2FA yet (requires verification first)
            - Overwrites any existing setup (allows re-setup)
        """
        # 1. Get user
        user = self.db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        # 2. Generate TOTP secret (Base32 encoded, 16 characters = 128 bits)
        totp_secret = pyotp.random_base32()

        # 3. Create TOTP URI for QR code
        totp = pyotp.TOTP(totp_secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=app_name
        )

        # 4. Generate QR code image (data URL)
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        qr_code_url = f"data:image/png;base64,{img_base64}"

        # 5. Generate 10 backup codes (8 characters each, format: XXXX-XXXX)
        backup_codes = self._generate_backup_codes(count=10)

        # 6. Get or create UserSecurity record
        user_security = self.db.execute(
            select(UserSecurity).where(UserSecurity.user_id == user_id)
        ).scalar_one_or_none()

        if not user_security:
            user_security = UserSecurity(user_id=user_id)
            self.db.add(user_security)

        # 7. Store secret and backup codes (NOT enabled yet)
        user_security.totp_secret = self._encrypt_secret(totp_secret)
        user_security.backup_codes = self._hash_backup_codes(backup_codes)  # store hashed codes
        user_security.backup_codes_used = []
        user_security.totp_enabled = False  # Not enabled until verified

        self.db.commit()

        logger.info(f"User {user_id} started 2FA setup")

        return TwoFactorSetupResponse(
            secret=totp_secret,
            qr_code_url=qr_code_url,
            backup_codes=backup_codes
        )

    def verify_and_enable_totp(self, user_id: int, code: str) -> TwoFactorStatusResponse:
        """
        Verify TOTP code and enable 2FA

        Args:
            user_id: User ID
            code: 6-digit TOTP code

        Returns:
            TwoFactorStatusResponse with enabled=True

        Raises:
            ValueError: If code is invalid or no setup found
        """
        # 1. Get UserSecurity
        user_security = self.db.execute(
            select(UserSecurity).where(UserSecurity.user_id == user_id)
        ).scalar_one_or_none()

        if not user_security or not user_security.totp_secret:
            raise ValueError("No 2FA setup found. Please start setup first.")

        # 2. Verify TOTP code (decrypt secret before verification)
        secret = self._decrypt_secret(user_security.totp_secret)
        if not self.verify_totp_code(secret, code):
            raise ValueError("Invalid verification code")

        # 3. Enable 2FA
        user_security.totp_enabled = True
        self.db.commit()

        logger.info(f"User {user_id} enabled 2FA")

        return TwoFactorStatusResponse(
            enabled=True,
            method="totp",
            backup_codes_remaining=len(user_security.backup_codes or [])
        )

    def verify_totp_code(self, secret: str, code: str, window: int = 1) -> bool:
        """
        Verify TOTP code with time window tolerance

        Args:
            secret: TOTP secret (Base32)
            code: 6-digit code to verify
            window: Time window tolerance (default 1 = ±30 seconds)

        Returns:
            True if code is valid, False otherwise
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=window)
        except Exception as e:
            logger.warning(f"TOTP verification failed: {e}")
            return False

    def disable_totp(self, user_id: int, password: str, code: str) -> TwoFactorStatusResponse:
        """
        Disable 2FA (requires password + current TOTP code)

        Args:
            user_id: User ID
            password: Current password
            code: Current TOTP code or backup code

        Returns:
            TwoFactorStatusResponse with enabled=False

        Raises:
            ValueError: If password or code is invalid
        """
        # 1. Get user and verify password
        user = self.db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        # Import UserService to verify password
        from AICrews.services.user_service import UserService
        user_service = UserService(self.db)
        if not user_service.verify_password(user, password):
            raise ValueError("Invalid password")

        # 2. Get UserSecurity
        user_security = self.db.execute(
            select(UserSecurity).where(UserSecurity.user_id == user_id)
        ).scalar_one_or_none()

        if not user_security or not user_security.totp_enabled:
            raise ValueError("2FA is not enabled")

        # 3. Verify TOTP code or backup code
        code_valid = False
        secret = self._decrypt_secret(user_security.totp_secret)
        if self.verify_totp_code(secret, code):
            code_valid = True
        elif self._verify_backup_code(user_security, code):
            code_valid = True

        if not code_valid:
            raise ValueError("Invalid verification code")

        # 4. Disable 2FA and clear secret
        user_security.totp_enabled = False
        user_security.totp_secret = None
        user_security.backup_codes = None
        user_security.backup_codes_used = None

        self.db.commit()

        logger.info(f"User {user_id} disabled 2FA")

        return TwoFactorStatusResponse(
            enabled=False,
            method=None,
            backup_codes_remaining=0
        )

    def get_2fa_status(self, user_id: int) -> TwoFactorStatusResponse:
        """
        Get current 2FA status for user

        Args:
            user_id: User ID

        Returns:
            TwoFactorStatusResponse
        """
        # Expire all to get fresh data
        self.db.expire_all()
        user_security = self.db.execute(
            select(UserSecurity).where(UserSecurity.user_id == user_id)
        ).scalar_one_or_none()

        if not user_security or not user_security.totp_enabled:
            return TwoFactorStatusResponse(
                enabled=False,
                method=None,
                backup_codes_remaining=0
            )

        backup_codes = user_security.backup_codes or []
        backup_codes_used = user_security.backup_codes_used or []
        remaining = len([c for c in backup_codes if c not in backup_codes_used])

        return TwoFactorStatusResponse(
            enabled=True,
            method="totp",
            backup_codes_remaining=remaining
        )

    def verify_backup_code(self, user_id: int, code: str) -> bool:
        """
        Verify and mark backup code as used

        Args:
            user_id: User ID
            code: Backup code (format: XXXX-XXXX)

        Returns:
            True if code is valid and unused, False otherwise
        """
        user_security = self.db.execute(
            select(UserSecurity).where(UserSecurity.user_id == user_id)
        ).scalar_one_or_none()

        if not user_security:
            return False

        return self._verify_backup_code(user_security, code, mark_used=True)

    def _verify_backup_code(self, user_security: UserSecurity, code: str, mark_used: bool = False) -> bool:
        """
        Internal: Verify backup code

        Args:
            user_security: UserSecurity record
            code: Backup code
            mark_used: If True, mark code as used

        Returns:
            True if valid, False otherwise
        """
        # Get fresh data from database to avoid stale cache
        self.db.refresh(user_security)

        backup_codes = user_security.backup_codes or []
        backup_codes_used = user_security.backup_codes_used or []

        # Normalize code (remove spaces, uppercase) then hash for comparison
        code_normalized = code.replace(" ", "").replace("-", "").upper()
        code_hash = self._hash_backup_code(code_normalized)

        # Check if code exists and is not used
        for bc_hash in backup_codes:
            if bc_hash == code_hash and bc_hash not in backup_codes_used:
                if mark_used:
                    backup_codes_used.append(bc_hash)
                    user_security.backup_codes_used = backup_codes_used
                    # Mark as modified for SQLAlchemy to detect change
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(user_security, "backup_codes_used")
                    self.db.commit()
                    logger.info(f"Backup code used for user {user_security.user_id}")
                return True

        return False

    def _generate_backup_codes(self, count: int = 10) -> List[str]:
        """
        Generate backup recovery codes

        Args:
            count: Number of codes to generate

        Returns:
            List of backup codes (format: XXXX-XXXX)
        """
        codes = []
        for _ in range(count):
            # Generate 8 random hex characters, format as XXXX-XXXX
            code = secrets.token_hex(4).upper()
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        return codes

    # ------------------------------------------------------------------
    # Helpers: encryption + hashing
    # ------------------------------------------------------------------

    def _get_fernet(self) -> Fernet:
        """Get Fernet instance. Uses env SECURITY_ENCRYPTION_KEY or dev fallback."""
        key = os.environ.get("SECURITY_ENCRYPTION_KEY")
        if not key:
            # Dev/test fallback to keep functionality; warns loudly.
            fallback = "TEST_INSECURE_KEY_FOR_DEV__CHANGE_ME"
            key = base64.urlsafe_b64encode(fallback.encode()[:32].ljust(32, b"0"))
            logger.warning("SECURITY_ENCRYPTION_KEY not set; using insecure dev key. Configure a strong key in prod.")
        else:
            # Ensure key is URL-safe base64 32-byte
            key = key.encode()
            if len(key) != 44:
                # If user provided raw 32 bytes, encode it
                key = base64.urlsafe_b64encode(key[:32].ljust(32, b"0"))
        return Fernet(key)

    def _encrypt_secret(self, secret: str) -> str:
        f = self._get_fernet()
        return f.encrypt(secret.encode()).decode()

    def _decrypt_secret(self, encrypted: str) -> str:
        f = self._get_fernet()
        return f.decrypt(encrypted.encode()).decode()

    def _hash_backup_code(self, code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    def _hash_backup_codes(self, codes: List[str]) -> List[str]:
        return [self._hash_backup_code(c.replace(" ", "").replace("-", "").upper()) for c in codes]


class SessionService:
    """Service for login session management"""

    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        user_id: int,
        token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        location: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> "LoginSession":
        """
        Create new login session

        Args:
            user_id: User ID
            token: Session token (JWT or similar)
            device_info: Device description (browser, OS)
            ip_address: IP address
            location: Geographic location
            expires_at: Expiration timestamp

        Returns:
            LoginSession object
        """
        from AICrews.database.models.security import LoginSession

        session = LoginSession(
            user_id=user_id,
            token=token,
            device_info=device_info,
            ip_address=ip_address,
            location=location,
            expires_at=expires_at
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        logger.info(f"Created session {session.id} for user {user_id}")
        return session

    def get_active_sessions(self, user_id: int, current_token: Optional[str] = None) -> List["LoginSession"]:
        """
        Get all active (non-revoked, non-expired) sessions for user

        Args:
            user_id: User ID
            current_token: Current session token (to mark as is_current in response)

        Returns:
            List of LoginSession objects
        """
        from AICrews.database.models.security import LoginSession

        now = datetime.now()

        sessions = self.db.execute(
            select(LoginSession)
            .where(LoginSession.user_id == user_id)
            .where(LoginSession.is_revoked == False)
            .where((LoginSession.expires_at.is_(None)) | (LoginSession.expires_at > now))
            .order_by(LoginSession.last_active.desc())
        ).scalars().all()

        return list(sessions)

    def revoke_session(self, session_id: int, user_id: Optional[int] = None) -> bool:
        """
        Revoke a specific session

        Args:
            session_id: Session ID to revoke
            user_id: User ID (for authorization check)

        Returns:
            True if revoked, False if not found

        Raises:
            ValueError: If session doesn't belong to user
        """
        from AICrews.database.models.security import LoginSession

        session = self.db.execute(
            select(LoginSession).where(LoginSession.id == session_id)
        ).scalar_one_or_none()

        if not session:
            return False

        # Authorization check
        if user_id and session.user_id != user_id:
            raise ValueError("Session does not belong to user")

        session.is_revoked = True
        self.db.commit()

        logger.info(f"Revoked session {session_id} for user {session.user_id}")

        # Emit webhook event (best-effort, after all DB operations)
        NotificationService(self.db).emit_event(
            session.user_id,
            "security.session_revoked",
            {"session_id": session_id}
        )

        return True

    def revoke_all_sessions(self, user_id: int, except_token: Optional[str] = None) -> int:
        """
        Revoke all sessions for user (except current)

        Args:
            user_id: User ID
            except_token: Token to keep active (current session)

        Returns:
            Number of sessions revoked
        """
        from AICrews.database.models.security import LoginSession

        query = select(LoginSession).where(
            LoginSession.user_id == user_id,
            LoginSession.is_revoked == False
        )

        if except_token:
            query = query.where(LoginSession.token != except_token)

        sessions = self.db.execute(query).scalars().all()

        count = 0
        for session in sessions:
            session.is_revoked = True
            count += 1

        self.db.commit()

        logger.info(f"Revoked {count} sessions for user {user_id}")
        return count

    def update_session_activity(self, token: str) -> bool:
        """
        Update session last_active timestamp

        Args:
            token: Session token

        Returns:
            True if updated, False if not found
        """
        from AICrews.database.models.security import LoginSession

        session = self.db.execute(
            select(LoginSession).where(LoginSession.token == token)
        ).scalar_one_or_none()

        if not session or session.is_revoked:
            return False

        session.last_active = datetime.now()
        self.db.commit()

        return True

    def get_login_history(self, user_id: int, limit: int = 30) -> List["LoginEvent"]:
        """
        Get login history for user

        Args:
            user_id: User ID
            limit: Max number of events to return

        Returns:
            List of LoginEvent objects
        """
        from AICrews.database.models.security import LoginEvent

        events = self.db.execute(
            select(LoginEvent)
            .where(LoginEvent.user_id == user_id)
            .order_by(LoginEvent.created_at.desc())
            .limit(limit)
        ).scalars().all()

        return list(events)

    def create_login_event(
        self,
        user_id: int,
        event_type: str,
        status: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        location: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> "LoginEvent":
        """
        Create login event for audit log

        Args:
            user_id: User ID
            event_type: Event type (login_success, login_failed, 2fa_failed, etc.)
            status: Event status (success, failed, suspicious)
            device_info: Device description
            ip_address: IP address
            location: Geographic location
            failure_reason: Failure reason (if failed)

        Returns:
            LoginEvent object
        """
        from AICrews.database.models.security import LoginEvent

        event = LoginEvent(
            user_id=user_id,
            event_type=event_type,
            status=status,
            device_info=device_info,
            ip_address=ip_address,
            location=location,
            failure_reason=failure_reason
        )

        self.db.add(event)
        self.db.commit()

        logger.info(f"Created login event {event_type} for user {user_id}: {status}")
        return event
