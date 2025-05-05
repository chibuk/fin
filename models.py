from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime

class BaseModel(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    institution_id: Optional[int] = Field(default=None, foreign_key="institution.id")

class User(BaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    email: str
    phone_number: str
    registration_date: datetime = Field(default_factory=datetime.utcnow)
    password_hash: str
    institutions: List["Institution"] = Relationship(back_populates="users")

class Institution(BaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    info: Optional[str]
    creator_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    users: List["User"] = Relationship(back_populates="institutions")
    accounts: List["Account"] = Relationship(back_populates="institution")

class Account(BaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    institution_id: int = Field(foreign_key="institution.id")
    balance: float = 0.0
    transactions: List["Transaction"] = Relationship(back_populates="account")
    balance_changes: List["BalanceChange"] = Relationship(back_populates="account")

class Category(BaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str  # 'income' или 'expense'
    transactions: List["Transaction"] = Relationship(back_populates="category")

class Transaction(BaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    category_id: int = Field(foreign_key="category.id")
    account_id: int = Field(foreign_key="account.id")
    is_transfer: bool = False
    target_account_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    balance_change: "BalanceChange" = Relationship(back_populates="transaction", sa_relationship_kwargs={"cascade": "delete"})

class BalanceChange(BaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id")
    transaction_id: int = Field(foreign_key="transaction.id")
    balance_after: float

    account: Account = Relationship(back_populates="balance_changes")
    transaction: Transaction = Relationship(back_populates="balance_change")
