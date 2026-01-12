"""
User Service - 用户服务

提供用户管理相关的业务逻辑。
"""

from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from AICrews.observability.logging import get_logger
import bcrypt

from .base import BaseService
from AICrews.database.models.user import User, UserPortfolio
from AICrews.schemas.user import UserCreate, UserResponse, UserPortfolioCreate
from AICrews.schemas.profile import ProfileUpdateRequest, EmailVerificationResponse

logger = get_logger(__name__)

BCRYPT_PASSWORD_MAX_BYTES = 72
BCRYPT_DEFAULT_ROUNDS = 12


def _bcrypt_secret(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_PASSWORD_MAX_BYTES]


class UserService(BaseService[User]):
    """用户服务类"""
    
    def __init__(self, db: Session):
        """初始化用户服务"""
        super().__init__(db, User)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户
        
        Args:
            email: 用户邮箱
            
        Returns:
            用户对象，如果不存在则返回 None
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def create_user(self, user_data: UserCreate) -> User:
        """创建新用户
        
        Args:
            user_data: 用户创建数据
            
        Returns:
            新创建的用户对象
            
        Raises:
            ValueError: 如果邮箱或用户名已存在
        """
        # 检查邮箱是否已存在
        existing = self.get_by_email(user_data.email)
        if existing:
            raise ValueError(f"Email {user_data.email} already exists")
        
        # 检查用户名是否已存在
        existing_username = self.db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            raise ValueError(f"Username {user_data.username} already exists")
        
        # 加密密码
        hashed_password = bcrypt.hashpw(
            _bcrypt_secret(user_data.password),
            bcrypt.gensalt(rounds=BCRYPT_DEFAULT_ROUNDS),
        ).decode("utf-8")
        
        # 创建用户
        user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
            subscription_level="free"  # Default subscription level
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def verify_password(self, user: User, password: str) -> bool:
        """验证用户密码
        
        Args:
            user: 用户对象
            password: 明文密码
            
        Returns:
            密码正确返回 True，否则返回 False
        """
        try:
            return bcrypt.checkpw(
                _bcrypt_secret(password),
                user.password_hash.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """验证用户身份
        
        Args:
            email: 用户邮箱
            password: 明文密码
            
        Returns:
            用户对象 (验证成功) 或 None
        """
        user = self.get_by_email(email)
        if not user:
            return None
        if not self.verify_password(user, password):
            return None
        return user
    
    def update_portfolio(
        self,
        user_id: int,
        ticker: str,
        portfolio_data: UserPortfolioCreate
    ) -> UserPortfolio:
        """更新或创建用户投资组合
        
        Args:
            user_id: 用户 ID
            ticker: 资产代码
            portfolio_data: 投资组合数据
            
        Returns:
            更新后的投资组合对象
        """
        # 检查是否已存在
        existing = self.db.query(UserPortfolio).filter(
            UserPortfolio.user_id == user_id,
            UserPortfolio.ticker == ticker
        ).first()
        
        if existing:
            # 更新现有记录
            if portfolio_data.notes is not None:
                existing.notes = portfolio_data.notes
            if portfolio_data.target_price is not None:
                existing.target_price = portfolio_data.target_price
        else:
            # 创建新记录
            existing = UserPortfolio(
                user_id=user_id,
                ticker=ticker,
                notes=portfolio_data.notes,
                target_price=portfolio_data.target_price
            )
            self.db.add(existing)
        
        self.db.commit()
        self.db.refresh(existing)
        
        return existing
    
    def remove_from_portfolio(self, user_id: int, ticker: str) -> bool:
        """从用户投资组合中移除资产
        
        Args:
            user_id: 用户 ID
            ticker: 资产代码
            
        Returns:
            移除成功返回 True，否则返回 False
        """
        portfolio = self.db.query(UserPortfolio).filter(
            UserPortfolio.user_id == user_id,
            UserPortfolio.ticker == ticker
        ).first()
        
        if not portfolio:
            return False
        
        self.db.delete(portfolio)
        self.db.commit()
        
        return True
    
    def get_user_portfolio(self, user_id: int) -> List[UserPortfolio]:
        """获取用户投资组合

        Args:
            user_id: 用户 ID

        Returns:
            投资组合列表
        """
        return self.db.query(UserPortfolio).filter(
            UserPortfolio.user_id == user_id
        ).all()

    def update_user_profile(self, user_id: int, update_data: ProfileUpdateRequest) -> User:
        """更新用户个人资料 (Settings v2.x)

        Implements sensitive vs non-sensitive field update rules:
        - Non-sensitive (full_name, avatar_url): NO password required
        - Sensitive (email, phone_number, new_password): REQUIRES current_password

        Args:
            user_id: 用户 ID
            update_data: 更新数据 (ProfileUpdateRequest)

        Returns:
            更新后的用户对象

        Raises:
            ValueError: 密码错误、邮箱已存在或用户不存在
        """
        try:
            # SQLAlchemy 2.0 style - get user
            stmt = select(User).where(User.id == user_id)
            user = self.db.execute(stmt).scalar_one_or_none()
            if not user:
                raise ValueError("User not found")

            # Determine if any sensitive fields are being updated
            sensitive_fields_present = any([
                update_data.email is not None,
                update_data.phone_number is not None,
                update_data.new_password is not None,
            ])

            # If sensitive fields are present, validate current_password
            if sensitive_fields_present:
                if not update_data.current_password:
                    raise ValueError("Updating sensitive fields requires current password")

                if not self.verify_password(user, update_data.current_password):
                    raise ValueError("Invalid current password")

            # === Process Non-Sensitive Fields (no password check) ===

            if update_data.full_name is not None:
                user.full_name = update_data.full_name

            if update_data.avatar_url is not None:
                user.avatar_url = update_data.avatar_url

            # === Process Sensitive Fields (password already verified above) ===

            # Email change: Set pending_email, NOT email directly
            if update_data.email is not None and update_data.email != user.email:
                # SQLAlchemy 2.0 style - check if email already exists
                check_stmt = select(User).where(User.email == update_data.email)
                existing = self.db.execute(check_stmt).scalar_one_or_none()
                if existing:
                    raise ValueError(f"Email {update_data.email} already exists")

                # Set pending_email (actual email change happens after verification)
                user.pending_email = update_data.email
                # Note: user.email remains unchanged until verification

                # Security event logging
                logger.info("Email change requested", extra={"user_id": user_id})

            # Phone number change: Update directly
            if update_data.phone_number is not None:
                user.phone_number = update_data.phone_number

            # Password change: Hash new password and update timestamp
            if update_data.new_password:
                hashed_password = bcrypt.hashpw(
                    _bcrypt_secret(update_data.new_password),
                    bcrypt.gensalt(rounds=BCRYPT_DEFAULT_ROUNDS),
                ).decode("utf-8")
                user.password_hash = hashed_password
                user.last_password_change = datetime.now()

                # Security event logging
                logger.info("Password changed", extra={"user_id": user_id})

            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            raise

    def verify_email_change(self, user_id: int, token: str) -> EmailVerificationResponse:
        """Verify pending email change with a token."""
        try:
            stmt = select(User).where(User.id == user_id)
            user = self.db.execute(stmt).scalar_one_or_none()
            if not user:
                raise ValueError("User not found")

            if not user.pending_email or not user.email_verification_token:
                raise ValueError("No pending email change")

            if user.email_verification_token != token:
                raise ValueError("Invalid or expired verification token")

            user.email = user.pending_email
            user.pending_email = None
            user.email_verification_token = None
            user.email_verified = True
            user.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(user)

            logger.info("Email verification completed", extra={"user_id": user_id})

            return EmailVerificationResponse(
                success=True,
                email=user.email,
                message="Email successfully verified and updated",
            )
        except Exception:
            self.db.rollback()
            raise
