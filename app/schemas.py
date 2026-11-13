from datetime import date, datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.constants import ROLES, STATUSES, LOCATION_TYPES, MAX_COMMENT_LENGTH


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field(default="client")

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ROLES:
            raise ValueError("Роль должна быть admin, validator или client")
        return value


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=50)
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ROLES:
            raise ValueError("Роль должна быть admin, validator или client")
        return value

    @field_validator("password")
    @classmethod
    def empty_password(cls, value: Optional[str]) -> Optional[str]:
        if value == "":
            return None
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserShort(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    contact: Optional[str] = Field(default=None, max_length=200)
    address: Optional[str] = Field(default=None, max_length=300)
    is_active: bool = True


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    contact: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierOut(BaseModel):
    id: int
    name: str
    contact: Optional[str] = None
    address: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    address: Optional[str] = Field(default=None, max_length=300)
    type: str
    is_active: bool = True

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in LOCATION_TYPES:
            raise ValueError("Тип места: warehouse или showroom")
        return value


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    address: Optional[str] = None
    type: Optional[str] = None
    is_active: Optional[bool] = None


class LocationOut(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    type: str
    is_active: bool

    class Config:
        from_attributes = True


class CatalogItemCreate(BaseModel):
    sku: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    category: Optional[str] = Field(default=None, max_length=100)
    size: Optional[str] = Field(default=None, max_length=50)
    color: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = True


class CatalogItemUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=2, max_length=50)
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    category: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class CatalogItemOut(BaseModel):
    id: int
    sku: str
    name: str
    category: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class SupplyItemIn(BaseModel):
    catalog_item_id: int
    quantity: int = Field(..., gt=0)


class SupplyItemOut(BaseModel):
    id: int
    catalog_item_id: int
    planned_qty: int
    actual_qty: Optional[int] = None
    sku: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    difference: Optional[int] = None


class SupplyCreate(BaseModel):
    supplier_id: int
    location_id: int
    planned_date: date
    responsible_id: int
    items: List[SupplyItemIn] = Field(..., min_length=1)


class SupplyUpdate(BaseModel):
    supplier_id: Optional[int] = None
    location_id: Optional[int] = None
    planned_date: Optional[date] = None
    responsible_id: Optional[int] = None
    items: Optional[List[SupplyItemIn]] = None


class SupplyRepeat(BaseModel):
    planned_date: date
    responsible_id: int


class StatusChange(BaseModel):
    status: str
    comment: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in STATUSES:
            raise ValueError("Недопустимый статус поставки")
        return value


class CheckItemIn(BaseModel):
    item_id: int
    actual_qty: int = Field(..., ge=0)


class SupplyCheckIn(BaseModel):
    items: List[CheckItemIn] = Field(..., min_length=1)
    comment: Optional[str] = Field(default=None, max_length=MAX_COMMENT_LENGTH)
    return_for_clarification: bool = False


class DocumentOut(BaseModel):
    id: int
    supply_id: int
    original_name: str
    content_type: str
    size: int
    uploaded_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_COMMENT_LENGTH)


class CommentOut(BaseModel):
    id: int
    supply_id: int
    author_id: int
    author_name: Optional[str] = None
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProposalCreate(BaseModel):
    planned_date: Optional[date] = None
    supplier_id: Optional[int] = None
    location_id: Optional[int] = None
    comment: Optional[str] = Field(default=None, max_length=MAX_COMMENT_LENGTH)


class ProposalOut(BaseModel):
    id: int
    supply_id: int
    author_id: int
    author_name: Optional[str] = None
    payload: Dict[str, Any]
    status: str
    base_version: int
    decided_by_id: Optional[int] = None
    decided_at: Optional[datetime] = None
    comment: Optional[str] = None
    created_at: datetime


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    message: str
    supply_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryOut(BaseModel):
    id: int
    supply_id: int
    actor_id: int
    actor_name: Optional[str] = None
    source: str
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime


class AuditOut(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    action: str
    object_type: str
    object_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime


class DiscrepancyOut(BaseModel):
    id: int
    supply_id: int
    item_id: int
    planned_qty: int
    actual_qty: int
    difference: int
    kind: str
    comment: Optional[str] = None
    sku: Optional[str] = None
    name: Optional[str] = None


class SupplyOut(BaseModel):
    id: int
    number: str
    supplier_id: int
    supplier_name: Optional[str] = None
    location_id: int
    location_name: Optional[str] = None
    location_type: Optional[str] = None
    planned_date: date
    actual_date: Optional[date] = None
    status: str
    status_label: Optional[str] = None
    responsible_id: int
    responsible_name: Optional[str] = None
    created_by_id: int
    created_by_name: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False
    overdue_days: int = 0
    items: List[SupplyItemOut] = []
    documents: List[DocumentOut] = []

    class Config:
        from_attributes = True


class SupplySummary(BaseModel):
    in_transit: int
    on_check: int
    overdue: int
    completed: int
    total: int


class RegistryRow(BaseModel):
    number: str
    supplier: str
    destination: str
    planned_date: date
    status: str
    responsible: str
    is_overdue: bool
    items: str


class DiscrepancyReportRow(BaseModel):
    number: str
    sku: str
    name: str
    planned_qty: int
    actual_qty: int
    difference: int
    kind: str
    comment: Optional[str] = None
