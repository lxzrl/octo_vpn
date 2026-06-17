"""Database models for VPN Telegram Bot (SQLAlchemy 2.0 Async)"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import BigInteger, String, DateTime, Boolean, ForeignKey, Text, Float, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Базовый класс для моделей SQLAlchemy 2.0
# AsyncAttrs позволяет безопасно работать со связями в асинхронной среде
class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    """User model"""
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    # КРИТИЧЕСКИ ВАЖНО: BigInteger для Telegram ID
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    language_code: Mapped[str] = mapped_column(String(10), default='ru')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Рекомендуется использовать timezone-aware datetime
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Referral system
    referrer_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'))
    referral_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    referral_balance: Mapped[float] = mapped_column(Float, default=0.0)
    total_referrals: Mapped[int] = mapped_column(default=0)

    # User stats
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="user")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        parts = [self.first_name, self.last_name]
        return ' '.join(filter(None, parts)) or self.username or f"User {self.telegram_id}"

    # Обрати внимание: В асинхронной SQLAlchemy обращение к свойству user.subscriptions напрямую
    # вызовет ошибку MissingGreenlet, если связь не была загружена заранее через selectinload().
    # Рекомендуется проверять подписку отдельным асинхронным запросом в репозитории/сервисе.

class Subscription(Base):
    """Subscription model"""
    __tablename__ = 'subscriptions'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    vpn_config: Mapped[Optional[str]] = mapped_column(Text)
    config_name: Mapped[Optional[str]] = mapped_column(String(255))
    server_location: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription(user_id={self.user_id}, plan={self.plan_type}, active={self.is_active})>"

    @property
    def is_expired(self) -> bool:
        """Check if subscription is expired"""
        return datetime.now(timezone.utc) > self.end_date

    @property
    def days_remaining(self) -> int:
        """Get days remaining in subscription"""
        if self.is_expired:
            return 0
        return (self.end_date - datetime.now(timezone.utc)).days

class Payment(Base):
    """Payment model"""
    __tablename__ = 'payments'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)  # В копейках/центах
    currency: Mapped[str] = mapped_column(String(3), default='RUB')
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))
    payment_id: Mapped[Optional[str]] = mapped_column(String(255))
    payment_url: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment(user_id={self.user_id}, amount={self.amount}, status={self.status})>"

    @property
    def amount_rubles(self) -> float:
        """Get amount in rubles"""
        return self.amount / 100

    @property
    def is_expired(self) -> bool:
        """Check if payment is expired"""
        return self.expires_at is not None and datetime.now(timezone.utc) > self.expires_at

class VPNKey(Base):
    """VPN Key model for managing pre-generated keys"""
    __tablename__ = 'vpn_keys'

    id: Mapped[int] = mapped_column(primary_key=True)
    key_data: Mapped[str] = mapped_column(Text, nullable=False)
    server_location: Mapped[Optional[str]] = mapped_column(String(100))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<VPNKey(id={self.id}, is_used={self.is_used}, location={self.server_location})>"

class ReferralPayout(Base):
    """Referral payout model"""
    __tablename__ = 'referral_payouts'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))
    payment_details: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

class AdminLog(Base):
    """Admin action logs"""
    __tablename__ = 'admin_logs'

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    target_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'))
    details: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class BotStats(Base):
    """Bot statistics model"""
    __tablename__ = 'bot_stats'

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    total_users: Mapped[int] = mapped_column(default=0)
    active_subscriptions: Mapped[int] = mapped_column(default=0)
    daily_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    new_users: Mapped[int] = mapped_column(default=0)
    new_payments: Mapped[int] = mapped_column(default=0)

class DatabaseManager:
    """Async Database management class"""

    def __init__(self, database_url: str):
        # Превращаем db url в асинхронный, если юзер забыл указать asyncpg
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("sqlite://"):
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True  # Проверяет живое ли соединение перед запросом
        )
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_tables(self) -> None:
        """Create all database tables asynchronously"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def get_session(self) -> AsyncSession:
        """Get async database session"""
        return self.SessionLocal()

    async def close(self) -> None:
        """Close database connection"""
        await self.engine.dispose()
