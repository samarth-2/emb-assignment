from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String, primary_key=True)  # e.g. 'ORD-1001'
    customer: Mapped[str] = mapped_column(String, nullable=False)
    product: Mapped[str] = mapped_column(String, nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # INR line total
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
