import asyncio
import asyncmy

async def main():
    conn = await asyncmy.connect(
        host="mysql",
        user="karnataka_user",
        password="karnataka_user_pass_2026",
        database="karnataka_guide",
        port=3306
    )
    async with conn.cursor() as cur:
        await cur.execute("SELECT 1")
        res = await cur.fetchone()
        print("MySQL SELECT 1:", res[0])
    await conn.ensure_closed()

if __name__ == "__main__":
    asyncio.run(main())
