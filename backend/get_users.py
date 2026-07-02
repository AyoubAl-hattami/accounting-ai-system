import sys
import os

# Add backend directory to sys.path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.modules.accounting.models.user import User
from app.modules.accounting.models.company_user import CompanyUser

def main():
    engine = create_engine(settings.DATABASE_URL)
    with Session(engine) as session:
        statement = select(User, CompanyUser).join(CompanyUser, User.id == CompanyUser.user_id)
        results = session.execute(statement).all()
        for user, cu in results:
            print(f"User: {user.email}, Company: {cu.company_id}, Role: {cu.role}, Active: {cu.is_active}")

if __name__ == "__main__":
    main()
