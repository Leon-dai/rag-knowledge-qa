"""独立脚本：创建管理员账号 admin/123456"""
import sys
sys.path.insert(0, '..')

from app.auth.models import User
from app.auth.utils import hash_password
from app.database import async_session_factory
from sqlalchemy import select
import asyncio


async def seed_admin():
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        if admin:
            print("管理员账号已存在，跳过创建。")
            return

        admin = User(
            username="admin",
            password_hash=hash_password("123456"),
            email="admin@example.com",
            role="admin",
        )
        db.add(admin)
        await db.commit()
        print("✅ 管理员账号创建成功！")
        print("   用户名: admin")
        print("   密码: 123456")
        print("   角色: admin")


if __name__ == "__main__":
    asyncio.run(seed_admin())
