import asyncpg
import random
import string
from contextlib import asynccontextmanager
from config import DATABASE_URL, DB_SCHEMA, DEFAULT_BONUS_AMOUNT, DEFAULT_BONUS_PROMO

POSITIVE_WORDS = [
    "SUNSHINE", "RAINBOW", "BLOSSOM", "HARMONY", "SPARKLE", "DREAM", "AURORA",
    "BREEZE", "CRYSTAL", "DELIGHT", "EMBER", "FORTUNE", "GENTLE", "HAVEN",
    "INSPIRE", "JOYFUL", "KINDNESS", "LIBERTY", "MIRACLE", "NOBLE", "OASIS",
    "PEACEFUL", "RADIANT", "SERENE", "TRIUMPH", "UNITY", "VALOR", "WONDER",
    "BLISS", "CHARM", "DAWN", "FAITH", "GRACE", "HONEY", "IVORY", "JEWEL",
    "LOTUS", "MELODY", "NECTAR", "PEARL", "SPIRIT", "STAR", "TENDER",
    "VELVET", "WISDOM", "BLOOM", "CORAL", "GLORY", "SILVER", "GOLDEN",
    "ANGEL", "BRIGHT", "CANDY", "DIVINE", "ETERNAL", "FEATHER", "GARDEN",
    "HAPPY", "ISLAND", "JASMINE", "KARMA", "LIGHT", "MAGIC", "NATURE",
    "OCEAN", "PARADISE", "QUEEN", "ROYAL", "SILK", "TREASURE", "UNIQUE",
    "VIVID", "WARMTH", "ZENITH", "AMBER", "BELOVED", "COSMIC", "DAZZLE",
    "ELEGANCE", "FLUTTER", "GLOW", "HORIZON", "INFINITY", "JUBILEE",
    "KINDRED", "LAVENDER", "MOONLIGHT", "NIRVANA", "ORCHID", "PASSION",
    "QUARTZ", "REVERIE", "SAPPHIRE", "TWILIGHT", "UTOPIA", "VIBRANT",
    "WHISPER", "XANADU", "YESTERDAY", "ZEPHYR", "BREEZY", "CHERISH",
    "DAHLIA", "ENCHANT", "FIREFLY", "GRATITUDE", "HALCYON", "IRIDESCENT",
    "JOURNEY", "KISMET", "LULLABY", "MAJESTIC", "NOSTALGIC", "OPULENT",
]

pool: asyncpg.Pool | None = None


@asynccontextmanager
async def _conn():
    """Acquire connection with correct search_path (Supabase pooler resets session state)."""
    async with pool.acquire() as conn:
        await conn.execute(f"SET search_path TO {DB_SCHEMA}")
        yield conn


async def init_db():
    global pool
    # First connection to create schema
    tmp = await asyncpg.connect(DATABASE_URL, ssl="require")
    await tmp.execute(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}")
    await tmp.close()

    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        statement_cache_size=0,
        ssl="require",
    )
    async with _conn() as conn:
        await _create_tables(conn)
        await _run_migrations(conn)
        await _seed_defaults(conn)


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None


async def _create_tables(conn):
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id              SERIAL PRIMARY KEY,
            telegram_id     BIGINT UNIQUE NOT NULL,
            first_name      TEXT,
            last_name       TEXT,
            username        TEXT,
            language_code   TEXT,
            phone           TEXT,
            created_at      TIMESTAMP DEFAULT NOW(),
            updated_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS promotions (
            id              SERIAL PRIMARY KEY,
            title           TEXT NOT NULL,
            description     TEXT NOT NULL,
            photo_path      TEXT,
            start_date      DATE,
            end_date        DATE,
            is_active       INTEGER DEFAULT 1,
            is_perpetual    INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS bonuses (
            id              SERIAL PRIMARY KEY,
            client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            amount          INTEGER NOT NULL DEFAULT 0,
            promo_code      TEXT NOT NULL,
            is_claimed      INTEGER DEFAULT 0,
            claimed_at      TIMESTAMP,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key             TEXT PRIMARY KEY,
            value           TEXT NOT NULL
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS mailings (
            id              SERIAL PRIMARY KEY,
            text            TEXT NOT NULL,
            photo_path      TEXT,
            button_text     TEXT,
            button_url      TEXT,
            status          TEXT DEFAULT 'draft',
            sent_total      INTEGER DEFAULT 0,
            sent_ok         INTEGER DEFAULT 0,
            sent_fail       INTEGER DEFAULT 0,
            sent_at         TIMESTAMP,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS bonus_redemptions (
            id              SERIAL PRIMARY KEY,
            bonus_id        INTEGER NOT NULL REFERENCES bonuses(id) ON DELETE CASCADE,
            amount          INTEGER NOT NULL,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback_messages (
            id              SERIAL PRIMARY KEY,
            client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            message_text    TEXT NOT NULL,
            admin_reply     TEXT,
            is_replied      INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT NOW(),
            replied_at      TIMESTAMP
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS giveaways (
            id              SERIAL PRIMARY KEY,
            title           TEXT NOT NULL,
            description     TEXT,
            winner_count    INTEGER NOT NULL DEFAULT 1,
            end_date        TIMESTAMP NOT NULL,
            deep_link_code  TEXT UNIQUE NOT NULL,
            status          TEXT DEFAULT 'active',
            created_at      TIMESTAMP DEFAULT NOW(),
            finished_at     TIMESTAMP
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS giveaway_participants (
            id              SERIAL PRIMARY KEY,
            giveaway_id     INTEGER NOT NULL REFERENCES giveaways(id) ON DELETE CASCADE,
            client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            created_at      TIMESTAMP DEFAULT NOW(),
            UNIQUE(giveaway_id, client_id)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS giveaway_winners (
            id              SERIAL PRIMARY KEY,
            giveaway_id     INTEGER NOT NULL REFERENCES giveaways(id) ON DELETE CASCADE,
            client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)


async def _run_migrations(conn):
    # Add is_perpetual column to promotions if not exists
    try:
        await conn.execute(
            "ALTER TABLE promotions ADD COLUMN is_perpetual INTEGER DEFAULT 0"
        )
    except Exception:
        pass  # Column already exists
    # Make start_date/end_date nullable for perpetual promotions
    try:
        await conn.execute("ALTER TABLE promotions ALTER COLUMN start_date DROP NOT NULL")
        await conn.execute("ALTER TABLE promotions ALTER COLUMN end_date DROP NOT NULL")
    except Exception:
        pass


async def _seed_defaults(conn):
    await conn.execute(
        "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING",
        "default_bonus_amount", str(DEFAULT_BONUS_AMOUNT),
    )
    await conn.execute(
        "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING",
        "default_bonus_promo", DEFAULT_BONUS_PROMO,
    )
    await conn.execute(
        "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING",
        "default_bonus_enabled", "1",
    )


# === Settings ===

async def get_setting(key: str) -> str | None:
    async with _conn() as conn:
        row = await conn.fetchrow("SELECT value FROM settings WHERE key = $1", key)
        return row["value"] if row else None


async def set_setting(key: str, value: str):
    async with _conn() as conn:
        await conn.execute(
            "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            key, value,
        )


# === Clients ===

async def ensure_client_registered(telegram_id: int, first_name: str = None,
                                    last_name: str = None, username: str = None,
                                    language_code: str = None) -> bool:
    """Register client. Returns True if this is a NEW client."""
    async with _conn() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM clients WHERE telegram_id = $1", telegram_id,
        )
        if existing:
            await conn.execute(
                """UPDATE clients SET first_name=$1, last_name=$2, username=$3, language_code=$4, updated_at=NOW()
                   WHERE telegram_id=$5""",
                first_name, last_name, username, language_code, telegram_id,
            )
            return False

        await conn.execute(
            "INSERT INTO clients (telegram_id, first_name, last_name, username, language_code) VALUES ($1, $2, $3, $4, $5)",
            telegram_id, first_name, last_name, username, language_code,
        )

    # Auto-assign default bonuses for new client
    enabled = await get_setting("default_bonus_enabled")
    if enabled == "1":
        amount = int(await get_setting("default_bonus_amount") or "0")
        if amount > 0:
            client = await get_client_by_telegram_id(telegram_id)
            if client:
                promo = await generate_unique_promo()
                await add_bonus(client["id"], amount, promo)

    return True


async def get_client_by_telegram_id(telegram_id: int) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM clients WHERE telegram_id = $1", telegram_id,
        )
        return dict(row) if row else None


async def get_all_clients() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT c.*,
                COALESCE((SELECT SUM(b.amount) FROM bonuses b WHERE b.client_id = c.id), 0) as bonus_total,
                COALESCE((SELECT COUNT(*) FROM feedback_messages f WHERE f.client_id = c.id), 0) as msg_count
            FROM clients c
            ORDER BY c.created_at DESC
        """)
        return [dict(r) for r in rows]


# === Promotions ===

async def get_active_promotions() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            """SELECT * FROM promotions
               WHERE is_active = 1
                 AND (is_perpetual = 1 OR (start_date <= CURRENT_DATE AND end_date >= CURRENT_DATE))
               ORDER BY created_at DESC"""
        )
        return [dict(r) for r in rows]


async def get_all_promotions() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM promotions ORDER BY created_at DESC")
        return [dict(r) for r in rows]


async def add_promotion(title: str, description: str, photo_path,
                        start_date, end_date, is_active: int = 1,
                        is_perpetual: int = 0) -> int:
    async with _conn() as conn:
        row = await conn.fetchrow(
            """INSERT INTO promotions (title, description, photo_path, start_date, end_date, is_active, is_perpetual)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
            title, description, photo_path, start_date, end_date, is_active, is_perpetual,
        )
        return row["id"]


async def update_promotion(promotion_id: int, title: str, description: str,
                           photo_path, start_date, end_date,
                           is_active: int = 1, is_perpetual: int = 0):
    async with _conn() as conn:
        await conn.execute(
            """UPDATE promotions
               SET title=$1, description=$2, photo_path=$3, start_date=$4,
                   end_date=$5, is_active=$6, is_perpetual=$7
               WHERE id=$8""",
            title, description, photo_path, start_date, end_date,
            is_active, is_perpetual, promotion_id,
        )


async def toggle_promotion(promotion_id: int):
    async with _conn() as conn:
        await conn.execute(
            "UPDATE promotions SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = $1",
            promotion_id,
        )


async def delete_promotion(promotion_id: int):
    async with _conn() as conn:
        await conn.execute("DELETE FROM promotions WHERE id = $1", promotion_id)


async def get_promotion(promotion_id: int) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow("SELECT * FROM promotions WHERE id = $1", promotion_id)
        return dict(row) if row else None


# === Bonuses ===

async def generate_unique_promo() -> str:
    """Generate a unique promo code from positive English words."""
    async with _conn() as conn:
        # Shuffle to avoid bias, try each word
        words = POSITIVE_WORDS.copy()
        random.shuffle(words)
        for word in words:
            existing = await conn.fetchrow(
                "SELECT id FROM bonuses WHERE promo_code = $1", word,
            )
            if not existing:
                return word
        # Fallback if all words used — add digits
        for _ in range(100):
            word = random.choice(POSITIVE_WORDS)
            code = f"{word}{random.randint(10, 99)}"
            existing = await conn.fetchrow(
                "SELECT id FROM bonuses WHERE promo_code = $1", code,
            )
            if not existing:
                return code
    return f"GIFT{random.randint(1000, 9999)}"


async def get_client_claimed_bonus_total(client_id: int) -> int:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(SUM(amount), 0) as total FROM bonuses WHERE client_id = $1 AND is_claimed = 1",
            client_id,
        )
        return row["total"]


async def update_client_phone(client_id: int, phone: str):
    async with _conn() as conn:
        await conn.execute(
            "UPDATE clients SET phone = $1 WHERE id = $2", phone, client_id,
        )


async def redeem_bonus_by_code(promo_code: str, amount: int, phone: str = "") -> dict:
    """Find bonus by promo code and reduce its amount. Returns result dict."""
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT id, amount, client_id FROM bonuses WHERE promo_code = $1",
            promo_code,
        )
        if not row:
            return {"found": False, "message": "Промокод не найден"}
        bonus_id = row["id"]
        client_id = row["client_id"]
        current = row["amount"]
        deduct = min(amount, current)
        new_amount = current - deduct
        await conn.execute(
            "UPDATE bonuses SET amount = $1 WHERE id = $2",
            new_amount, bonus_id,
        )
        # Update client phone if provided
        if phone and phone.strip():
            await conn.execute(
                "UPDATE clients SET phone = $1 WHERE id = $2",
                phone.strip(), client_id,
            )
        # Log redemption history
        await conn.execute(
            "INSERT INTO bonus_redemptions (bonus_id, amount) VALUES ($1, $2)",
            bonus_id, deduct,
        )
        # Track total redeemed
        await conn.execute(
            "INSERT INTO settings (key, value) VALUES ('total_redeemed', $1) ON CONFLICT (key) DO UPDATE SET value = (COALESCE(settings.value::int, 0) + $1::int)::text",
            str(deduct),
        )
        client = await conn.fetchrow("SELECT first_name, username FROM clients WHERE id = $1", client_id)
        client_name = (client["first_name"] or "") if client else ""
        if client and client["username"]:
            client_name += f" (@{client['username']})"
        return {
            "found": True,
            "deducted": deduct,
            "remaining": new_amount,
            "client_name": client_name.strip(),
            "message": f"Списано {deduct} бонусов. Остаток: {new_amount}. Клиент: {client_name.strip()}",
        }


async def get_client_promo_code(client_id: int) -> str | None:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT promo_code FROM bonuses WHERE client_id = $1 ORDER BY created_at DESC LIMIT 1",
            client_id,
        )
        return row["promo_code"] if row else None


async def get_client_redemptions(client_id: int) -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT r.amount, r.created_at
            FROM bonus_redemptions r
            JOIN bonuses b ON r.bonus_id = b.id
            WHERE b.client_id = $1
            ORDER BY r.created_at DESC
        """, client_id)
        return [dict(r) for r in rows]


async def get_redemption_history() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT r.amount, r.created_at,
                   b.promo_code,
                   c.first_name, c.last_name, c.username
            FROM bonus_redemptions r
            JOIN bonuses b ON r.bonus_id = b.id
            JOIN clients c ON b.client_id = c.id
            ORDER BY r.created_at DESC
        """)
        return [dict(r) for r in rows]


async def get_bonus_stats() -> dict:
    async with _conn() as conn:
        row = await conn.fetchrow("""
            SELECT
                COALESCE(SUM(amount), 0) as total_issued,
                COUNT(*) as total_records,
                COALESCE(SUM(CASE WHEN is_claimed = 1 THEN 1 ELSE 0 END), 0) as claimed_count,
                COUNT(DISTINCT client_id) as clients_with_bonuses,
                COUNT(DISTINCT CASE WHEN is_claimed = 1 THEN client_id END) as clients_claimed
            FROM bonuses
        """)
        stats = dict(row)
        redeemed = await conn.fetchrow("SELECT value FROM settings WHERE key = 'total_redeemed'")
        stats["total_redeemed"] = int(redeemed["value"]) if redeemed else 0
        return stats


async def get_client_bonuses(client_id: int) -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM bonuses WHERE client_id = $1 ORDER BY created_at DESC",
            client_id,
        )
        return [dict(r) for r in rows]


async def get_client_bonus_total(client_id: int) -> int:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(SUM(amount), 0) as total FROM bonuses WHERE client_id = $1",
            client_id,
        )
        return row["total"]


async def get_unclaimed_bonuses(client_id: int) -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM bonuses WHERE client_id = $1 AND is_claimed = 0 ORDER BY created_at DESC",
            client_id,
        )
        return [dict(r) for r in rows]


async def claim_bonuses(client_id: int) -> str | None:
    async with _conn() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT promo_code FROM bonuses WHERE client_id = $1 AND is_claimed = 0 ORDER BY created_at DESC LIMIT 1",
                client_id,
            )
            if not row:
                return None
            promo_code = row["promo_code"]
            await conn.execute(
                "UPDATE bonuses SET is_claimed = 1, claimed_at = NOW() WHERE client_id = $1 AND is_claimed = 0",
                client_id,
            )
            return promo_code


async def get_last_claimed_code(client_id: int) -> str | None:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT promo_code FROM bonuses WHERE client_id = $1 AND is_claimed = 1 ORDER BY claimed_at DESC LIMIT 1",
            client_id,
        )
        return row["promo_code"] if row else None


async def add_bonus(client_id: int, amount: int, promo_code: str):
    async with _conn() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM bonuses WHERE client_id = $1", client_id,
        )
        if existing:
            await conn.execute(
                "UPDATE bonuses SET amount = amount + $1 WHERE id = $2",
                amount, existing["id"],
            )
        else:
            await conn.execute(
                "INSERT INTO bonuses (client_id, amount, promo_code) VALUES ($1, $2, $3)",
                client_id, amount, promo_code,
            )


async def add_bonus_to_all(amount: int, promo_code: str):
    async with _conn() as conn:
        rows = await conn.fetch("SELECT id FROM clients")
        for r in rows:
            existing = await conn.fetchrow(
                "SELECT id FROM bonuses WHERE client_id = $1", r["id"],
            )
            if existing:
                await conn.execute(
                    "UPDATE bonuses SET amount = amount + $1 WHERE id = $2",
                    amount, existing["id"],
                )
            else:
                await conn.execute(
                    "INSERT INTO bonuses (client_id, amount, promo_code) VALUES ($1, $2, $3)",
                    r["id"], amount, promo_code,
                )


async def delete_bonus(bonus_id: int):
    async with _conn() as conn:
        await conn.execute("DELETE FROM bonuses WHERE id = $1", bonus_id)


async def update_bonus_code(bonus_id: int, new_code: str):
    async with _conn() as conn:
        await conn.execute(
            "UPDATE bonuses SET promo_code = $1 WHERE id = $2",
            new_code, bonus_id,
        )


async def get_all_bonuses_with_clients() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT b.*, c.first_name, c.last_name, c.username, c.telegram_id
            FROM bonuses b
            JOIN clients c ON b.client_id = c.id
            ORDER BY b.created_at DESC
        """)
        return [dict(r) for r in rows]


async def delete_client(client_id: int):
    async with _conn() as conn:
        await conn.execute("DELETE FROM clients WHERE id = $1", client_id)


# === Feedback ===

async def save_feedback(client_id: int, message_text: str) -> int:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "INSERT INTO feedback_messages (client_id, message_text) VALUES ($1, $2) RETURNING id",
            client_id, message_text,
        )
        return row["id"]


async def get_all_feedback() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT f.*, c.first_name, c.last_name, c.username, c.telegram_id
            FROM feedback_messages f
            JOIN clients c ON f.client_id = c.id
            ORDER BY f.created_at DESC
        """)
        return [dict(r) for r in rows]


async def get_feedback(feedback_id: int) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM feedback_messages WHERE id = $1", feedback_id,
        )
        return dict(row) if row else None


async def set_feedback_reply(feedback_id: int, reply_text: str):
    async with _conn() as conn:
        await conn.execute(
            "UPDATE feedback_messages SET admin_reply = $1, is_replied = 1, replied_at = NOW() WHERE id = $2",
            reply_text, feedback_id,
        )


async def delete_feedback(feedback_id: int):
    async with _conn() as conn:
        await conn.execute("DELETE FROM feedback_messages WHERE id = $1", feedback_id)


async def get_client(client_id: int) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow("SELECT * FROM clients WHERE id = $1", client_id)
        return dict(row) if row else None


# === Mailings ===

async def create_mailing(text: str, photo_path: str = None,
                         button_text: str = None, button_url: str = None) -> int:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "INSERT INTO mailings (text, photo_path, button_text, button_url) VALUES ($1, $2, $3, $4) RETURNING id",
            text, photo_path, button_text, button_url,
        )
        return row["id"]


async def get_all_mailings() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM mailings ORDER BY created_at DESC")
        return [dict(r) for r in rows]


async def get_mailing(mailing_id: int) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow("SELECT * FROM mailings WHERE id = $1", mailing_id)
        return dict(row) if row else None


async def update_mailing(mailing_id: int, text: str, photo_path: str = None,
                         button_text: str = None, button_url: str = None):
    async with _conn() as conn:
        await conn.execute(
            """UPDATE mailings SET text=$1, photo_path=$2, button_text=$3, button_url=$4
               WHERE id=$5 AND status='draft'""",
            text, photo_path, button_text, button_url, mailing_id,
        )


async def update_mailing_stats(mailing_id: int, sent_total: int, sent_ok: int, sent_fail: int):
    async with _conn() as conn:
        await conn.execute(
            """UPDATE mailings SET status='sent', sent_total=$1, sent_ok=$2, sent_fail=$3, sent_at=NOW()
               WHERE id=$4""",
            sent_total, sent_ok, sent_fail, mailing_id,
        )


async def delete_mailing(mailing_id: int):
    async with _conn() as conn:
        await conn.execute("DELETE FROM mailings WHERE id = $1", mailing_id)


async def get_all_client_telegram_ids() -> list[int]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT telegram_id FROM clients")
        return [r["telegram_id"] for r in rows]


# === Giveaways ===

async def create_giveaway(title: str, description: str, winner_count: int, end_date) -> int:
    async with _conn() as conn:
        # Generate unique deep link code
        for _ in range(100):
            code = "gw_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
            existing = await conn.fetchrow(
                "SELECT id FROM giveaways WHERE deep_link_code = $1", code,
            )
            if not existing:
                break
        row = await conn.fetchrow(
            """INSERT INTO giveaways (title, description, winner_count, end_date, deep_link_code)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            title, description, winner_count, end_date, code,
        )
        return row["id"]


async def get_giveaway(giveaway_id: int) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow("SELECT * FROM giveaways WHERE id = $1", giveaway_id)
        return dict(row) if row else None


async def get_giveaway_by_code(deep_link_code: str) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM giveaways WHERE deep_link_code = $1", deep_link_code,
        )
        return dict(row) if row else None


async def get_all_giveaways() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT g.*,
                COALESCE((SELECT COUNT(*) FROM giveaway_participants p WHERE p.giveaway_id = g.id), 0) as participant_count,
                COALESCE((SELECT COUNT(*) FROM giveaway_winners w WHERE w.giveaway_id = g.id), 0) as winner_count_actual
            FROM giveaways g
            ORDER BY g.created_at DESC
        """)
        return [dict(r) for r in rows]


async def add_giveaway_participant(giveaway_id: int, client_id: int) -> bool:
    """Add participant. Returns True if added, False if already exists."""
    async with _conn() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM giveaway_participants WHERE giveaway_id = $1 AND client_id = $2",
            giveaway_id, client_id,
        )
        if existing:
            return False
        await conn.execute(
            "INSERT INTO giveaway_participants (giveaway_id, client_id) VALUES ($1, $2)",
            giveaway_id, client_id,
        )
        return True


async def get_giveaway_participants(giveaway_id: int) -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT p.created_at, c.first_name, c.last_name, c.username, c.telegram_id
            FROM giveaway_participants p
            JOIN clients c ON p.client_id = c.id
            WHERE p.giveaway_id = $1
            ORDER BY p.created_at
        """, giveaway_id)
        return [dict(r) for r in rows]


async def finish_giveaway(giveaway_id: int) -> list[dict]:
    """Finish giveaway: pick random winners, return winner list."""
    async with _conn() as conn:
        gw = await conn.fetchrow("SELECT * FROM giveaways WHERE id = $1", giveaway_id)
        if not gw or gw["status"] != "active":
            return []
        # Get all participants
        participants = await conn.fetch(
            "SELECT client_id FROM giveaway_participants WHERE giveaway_id = $1",
            giveaway_id,
        )
        if not participants:
            await conn.execute(
                "UPDATE giveaways SET status = 'finished', finished_at = NOW() WHERE id = $1",
                giveaway_id,
            )
            return []
        # Pick random winners
        client_ids = [r["client_id"] for r in participants]
        winner_count = min(gw["winner_count"], len(client_ids))
        winner_ids = random.sample(client_ids, winner_count)
        # Insert winners
        for cid in winner_ids:
            await conn.execute(
                "INSERT INTO giveaway_winners (giveaway_id, client_id) VALUES ($1, $2)",
                giveaway_id, cid,
            )
        # Mark finished
        await conn.execute(
            "UPDATE giveaways SET status = 'finished', finished_at = NOW() WHERE id = $1",
            giveaway_id,
        )
        # Return winner info
        winners = await conn.fetch("""
            SELECT c.first_name, c.last_name, c.username, c.telegram_id
            FROM giveaway_winners w
            JOIN clients c ON w.client_id = c.id
            WHERE w.giveaway_id = $1
        """, giveaway_id)
        return [dict(r) for r in winners]


async def get_giveaway_winners(giveaway_id: int) -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT c.first_name, c.last_name, c.username, c.telegram_id, w.created_at
            FROM giveaway_winners w
            JOIN clients c ON w.client_id = c.id
            WHERE w.giveaway_id = $1
        """, giveaway_id)
        return [dict(r) for r in rows]


async def get_expired_active_giveaways() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM giveaways WHERE status = 'active' AND end_date <= NOW()"
        )
        return [dict(r) for r in rows]


async def delete_giveaway(giveaway_id: int):
    async with _conn() as conn:
        await conn.execute("DELETE FROM giveaways WHERE id = $1", giveaway_id)
