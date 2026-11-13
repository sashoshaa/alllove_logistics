from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="client")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    contact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StorageLocation(Base):
    __tablename__ = "storage_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String)  # warehouse | showroom
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CatalogItem(Base):
    __tablename__ = "catalog_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    size: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Supply(Base):
    __tablename__ = "supplies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    number: Mapped[str] = mapped_column(String, unique=True, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("storage_locations.id"))
    planned_date: Mapped[date] = mapped_column(Date)
    actual_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, default="created", index=True)
    responsible_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    supplier: Mapped["Supplier"] = relationship(foreign_keys=[supplier_id])
    location: Mapped["StorageLocation"] = relationship(foreign_keys=[location_id])
    responsible: Mapped["User"] = relationship(foreign_keys=[responsible_id])
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    items: Mapped[List["SupplyItem"]] = relationship(
        back_populates="supply", cascade="all, delete-orphan"
    )
    documents: Mapped[List["SupplyDocument"]] = relationship(
        back_populates="supply", cascade="all, delete-orphan"
    )


class SupplyItem(Base):
    __tablename__ = "supply_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id"))
    catalog_item_id: Mapped[int] = mapped_column(ForeignKey("catalog_items.id"))
    planned_qty: Mapped[int] = mapped_column(Integer)
    actual_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    supply: Mapped["Supply"] = relationship(back_populates="items")
    catalog_item: Mapped["CatalogItem"] = relationship()


class SupplyDocument(Base):
    __tablename__ = "supply_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id"))
    filename: Mapped[str] = mapped_column(String)
    original_name: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    supply: Mapped["Supply"] = relationship(back_populates="documents")
    uploaded_by: Mapped["User"] = relationship()


class SupplyCheck(Base):
    __tablename__ = "supply_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id"))
    validator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    result: Mapped[str] = mapped_column(String)  # match | discrepancy
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Discrepancy(Base):
    __tablename__ = "discrepancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("supply_items.id"))
    check_id: Mapped[int] = mapped_column(ForeignKey("supply_checks.id"))
    planned_qty: Mapped[int] = mapped_column(Integer)
    actual_qty: Mapped[int] = mapped_column(Integer)
    difference: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ChangeProposal(Base):
    __tablename__ = "change_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    base_version: Mapped[int] = mapped_column(Integer)
    decided_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    author: Mapped["User"] = relationship(foreign_keys=[author_id])
    decided_by: Mapped["User"] = relationship(foreign_keys=[decided_by_id])


class SupplyComment(Base):
    __tablename__ = "supply_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    author: Mapped["User"] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    supply_id: Mapped[Optional[int]] = mapped_column(ForeignKey("supplies.id"), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String, index=True)
    object_type: Mapped[str] = mapped_column(String, index=True)
    object_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    actor: Mapped["User"] = relationship()


class SupplyHistory(Base):
    __tablename__ = "supply_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(String)
    field: Mapped[str] = mapped_column(String)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    actor: Mapped["User"] = relationship()
