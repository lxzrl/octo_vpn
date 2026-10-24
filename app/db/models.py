from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    # Telegram ID пользователя и есть первичный ключ.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(32))
    first_name: Mapped[str] = mapped_column(String(64), default="")
    # None, пока пользователь не выбрал язык при первом запуске.
    language: Mapped[str | None] = mapped_column(String(2))
    referrer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Пользователь заблокировал бота: не шлём ему рассылки и напоминания.
    is_blocked_bot: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
