from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StoredMessage(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    telegram_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    thread_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    thread_name: Mapped[str] = mapped_column(String(255), nullable=False)

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    has_photo: Mapped[bool] = mapped_column(Boolean, default=False)
    has_video: Mapped[bool] = mapped_column(Boolean, default=False)
    has_document: Mapped[bool] = mapped_column(Boolean, default=False)

    reply_to_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)