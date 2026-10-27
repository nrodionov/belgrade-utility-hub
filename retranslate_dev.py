import asyncio
import os
import logging
import asyncpg
from main import translate_both, DATABASE_URL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    events = await conn.fetch("SELECT id, title_sr, description_sr FROM events ORDER BY id")
    logging.info(f"Found {len(events)} events to re-translate in development database.")

    for event in events:
        eid = event['id']
        title_sr = event['title_sr']
        desc_sr = event['description_sr']

        logging.info(f"Re-translating event {eid}: {title_sr[:40]}...")

        try:
            t_ru, t_en = await translate_both(title_sr)
            d_ru, d_en = await translate_both(desc_sr)

            await conn.execute("""
                UPDATE events SET
                    title_ru = $1,
                    title_en = $2,
                    description_ru = $3,
                    description_en = $4
                WHERE id = $5
            """, t_ru, t_en, d_ru, d_en, eid)
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.5)
        except Exception as e:
            logging.error(f"Error re-translating event {eid}: {e}")

    await conn.close()
    logging.info("Development re-translation complete!")

if __name__ == "__main__":
    asyncio.run(main())
