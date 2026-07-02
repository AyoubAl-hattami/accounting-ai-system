import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.modules.accounting.models.user import User
from app.modules.accounting.models.company_user import CompanyUser

def restore_admin():
    engine = create_engine(settings.DATABASE_URL)
    with Session(engine) as session:
        # Find the locked out user
        user = session.execute(select(User).where(User.email == "admin@example.com")).scalar_one_or_none()
        if user:
            # Find their company role (company 3)
            cu = session.execute(
                select(CompanyUser).where(CompanyUser.user_id == user.id, CompanyUser.company_id == 3)
            ).scalar_one_or_none()
            
            if cu:
                print(f"Current role for {user.email}: {cu.role}")
                cu.role = "admin"
                cu.is_active = True
                session.commit()
                print("Role successfully restored to admin.")
        else:
            print("User admin@example.com not found.")

if __name__ == "__main__":
    restore_admin()
