import os
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import select, Session
from .models import *
from .db import init_db, get_session
from passlib.hash import bcrypt
import jwt
import asyncio


# from dotenv import load_dotenv
# load_dotenv()


app = FastAPI()

# Инициализация базы
@app.on_event("startup")
async def startup_event():
    await init_db()

SECRET_KEY = os.getenv('SECRET_KEY', 'testsecret')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Вспомогательные функции
def create_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm="HS256")

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id: int = payload.get("user_id")
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

# Регистрация
@app.post("/register/")
async def register(user: User):
    user.password_hash = bcrypt.hash("password")  # Замена на получение пароля
    async with get_session() as session:
        existing = await session.exec(select(User).where(User.email==user.email))
        if await existing.first():
            raise HTTPException(400, detail="Email exists")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return {"id": user.id, "message": "Registered"}

# Логин
@app.post("/token")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    async with get_session() as session:
        user = await session.exec(select(User).where(User.email==form.username))
        user_obj = await user.first()
        if not user_obj or not bcrypt.verify(form.password, user_obj.password_hash):
            raise HTTPException(400, detail="Bad credentials")
        token = create_token({"user_id": user_obj.id})
        return {"access_token": token, "token_type": "bearer"}

# Простая статика
@app.get("/", response_class=HTMLResponse)
def read_index():
    return FileResponse("static/index.html")

# --- Остальные роуты: CRUD, транзакции, удаление с перерасчетом ---

# Создание учреждения
@app.post("/institutions/")
def create_institution(name: str, info: Optional[str], current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    institution = Institution(name=name, info=info, creator_id=current_user.id)
    session.add(institution)
    session.commit()
    session.refresh(institution)
    return institution

# Получение списка учреждений пользователя
@app.get("/institutions/")
def get_user_institutions(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    institutions = session.exec(select(Institution).where(Institution.creator_id==current_user.id)).all()
    return institutions

# Переключение текущего учреждения (добавьте хранение в куки или иные механизмы)
# Здесь — простая версия
# current_institution_id = Cookie(None)

# Получить текущие учреждения, выбрать и сохранить в куки (пример)
# Реализация зависит от фронтенда

# CRUD для Accounts
@app.post("/accounts/")
def create_account(name: str, institution_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # Проверка, что пользователь в институте или создатель
    institution = session.get(Institution, institution_id)
    if not institution:
        raise HTTPException(404, detail="Учреждение не найдено")
    account = Account(name=name, institution_id=institution_id)
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

@app.get("/accounts/")
def list_accounts(institution_id: int, current_user=Depends(get_current_user), session: Session = Depends(get_session)):
    accounts = session.exec(select(Account).where(Account.institution_id==institution_id)).all()
    return accounts

# Операция транзакции
@app.post("/transactions/")
def create_transaction(
    account_id: int,
    amount: float,
    category_id: int,
    target_account_id: Optional[int] = None,
    is_transfer: bool = False,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session)
):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(404, "Счёт не найден")
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(404, "Категория не найдена")
    
    # Создаем транзакцию
    transaction = Transaction(
        amount=amount,
        category_id=category_id,
        account_id=account_id,
        is_transfer=is_transfer,
        target_account_id=target_account_id
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    # Обновляем баланс и создаем изменение баланса
    new_balance = account.balance + amount if category.type == 'income' else account.balance - amount
    account.balance = new_balance
    balance_change = BalanceChange(
        account_id=account_id,
        transaction_id=transaction.id,
        balance_after=new_balance
    )
    session.add(balance_change)

    # Если перевод
    if is_transfer and target_account_id:
        target_account = session.get(Account, target_account_id)
        if not target_account:
            raise HTTPException(404, "Целевой счет не найден")
        # Создавать транзакцию для целевого счета
        trans_target = Transaction(
            amount=amount,
            category_id=category_id,
            account_id=target_account_id,
            is_transfer=True,
            target_account_id=account_id
        )
        session.add(trans_target)
        session.commit()
        session.refresh(trans_target)
        # Обновление баланса целевого счета
        new_balance_target = target_account.balance + amount
        target_account.balance = new_balance_target
        balance_change_target = BalanceChange(
            account_id=target_account_id,
            transaction_id=trans_target.id,
            balance_after=new_balance_target
        )
        session.add(balance_change_target)
        session.commit()

    session.commit()
    return {"transaction_id": transaction.id, "new_balance": new_balance}

# Просмотр истории по счету
@app.get("/accounts/{account_id}/history")
def get_account_history(account_id: int, session: Session = Depends(get_session)):
    transactions = session.exec(select(Transaction).where(Transaction.account_id==account_id)).all()
    return transactions

# Получение текущего баланса счета
@app.get("/accounts/{account_id}/balance")
def get_balance(account_id: int, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(404, "Счет не найден")
    return {"balance": account.balance}

# Обработка удаления транзакции с перерасчётом
@app.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int):
    async with get_session() as session:
        transaction = await session.get(Transaction, transaction_id)
        if not transaction:
            raise HTTPException(404, "Транзакция не найдена")
        account_id = transaction.account_id
        await session.delete(transaction)
        # Удаляем связанные BalanceChange
        bc_list = await session.exec(select(BalanceChange).where(BalanceChange.transaction_id==transaction_id))
        async for bc in bc_list:
            await session.delete(bc)
        await session.commit()
        # Перерасчет
        await recalculate_balances(account_id, session)
        return {"detail": "Транзакция удалена"}

async def recalculate_balances(account_id: int, session):
    # Пересчет всех транзакций и балансов
    transactions = await session.exec(
        select(Transaction).where(Transaction.account_id==account_id).order_by(Transaction.created_at)
    )
    account = await session.get(Account, account_id)
    if not account:
        return
    # Удаляем все баланс изменения перед пересчетом
    await session.execute("DELETE FROM balancechange WHERE account_id=:id", {"id": account_id})
    balance = 0
    async for t in transactions:
        # Обновляем баланс
        category = await session.get(Category, t.category_id)
        if category and category.type == 'income':
            balance += t.amount
        else:
            balance -= t.amount
        bc = BalanceChange(account_id=account_id, transaction_id=t.id, balance_after=balance)
        session.add(bc)
    account.balance = balance
    await session.commit()

# Запуск сервера
# -- Запуск через Docker или напрямую командой:
# uvicorn main:app --reload
