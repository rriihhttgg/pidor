import discord
from discord.ext import commands
import random
import asyncio
import re
import sqlite3

# =========================
# 🗄️ DATABASE
# =========================

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS coins (
    user_id TEXT PRIMARY KEY,
    amount INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS filters (
    word TEXT PRIMARY KEY,
    reply TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned_words (
    word TEXT PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    user_id TEXT,
    item TEXT,
    count INTEGER,
    PRIMARY KEY(user_id, item)
)
""")

conn.commit()


# 🔥 ID пользователей
MY_ID = 1151575407666139291  # я
MY_ID2 = 1175806997845778572  # релз
MY_ID3 = 1042052101230034995  # аеросогс
MY_ID4 = 647154147371515911   # еминем
MY_ID5 = 1134533670829555852 # велег
MY_ID6 = 1167748208517206047 # рагалек
MY_ID7 = 1486614989816074382 # мои втарои агг

shop_items = {
    "filter": 250,
    "banword": 1000,
    "delete": 200,
    "remove banword": 1500
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# 💰 COINS
# =========================

def get_coins(user_id):
    cursor.execute("SELECT amount FROM coins WHERE user_id=?", (str(user_id),))
    result = cursor.fetchone()
    return result[0] if result else 0

def add_coins(user_id, amount):
    uid = str(user_id)
    current = get_coins(uid)

    cursor.execute("""
    INSERT INTO coins(user_id, amount)
    VALUES(?, ?)
    ON CONFLICT(user_id) DO UPDATE SET amount=?
    """, (uid, current + amount, current + amount))

    conn.commit()

# =========================
# 🔎 FILTERS
# =========================

def add_filter(word, reply):
    cursor.execute("INSERT OR REPLACE INTO filters VALUES (?, ?)", (word, reply))
    conn.commit()

def get_filters():
    cursor.execute("SELECT word, reply FROM filters")
    return dict(cursor.fetchall())

# =========================
# 🚫 BANWORDS
# =========================

def add_banword(word):
    cursor.execute("INSERT OR IGNORE INTO banned_words VALUES (?)", (word,))
    conn.commit()

def remove_banword(word):
    cursor.execute("DELETE FROM banned_words WHERE word=?", (word,))
    conn.commit()

def get_banwords():
    cursor.execute("SELECT word FROM banned_words")
    return [row[0] for row in cursor.fetchall()]

# =========================
# 🎒 ITEMS
# =========================

def add_item(user_id, item):
    cursor.execute("""
    INSERT INTO items(user_id, item, count)
    VALUES(?, ?, 1)
    ON CONFLICT(user_id, item) DO UPDATE SET count = count + 1
    """, (str(user_id), item))
    conn.commit()

def get_item(user_id, item):
    cursor.execute("SELECT count FROM items WHERE user_id=? AND item=?", (str(user_id), item))
    result = cursor.fetchone()
    return result[0] if result else 0

def use_item(user_id, item):
    if get_item(user_id, item) <= 0:
        return False

    cursor.execute("""
    UPDATE items SET count = count - 1
    WHERE user_id=? AND item=?
    """, (str(user_id), item))
    conn.commit()
    return True

# =========================
# 🔍 HELP
# =========================

def contains_phrase(text, phrase):
    if " " in phrase:
        return phrase in text
    return re.search(rf'\b{re.escape(phrase)}\b', text) is not None

# =========================
# 📩 MESSAGE
# =========================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.lower()

    # filters
    for word, reply in get_filters().items():
        if word in text:
            await message.reply(reply)
            return

    # banned words
    for word in get_banwords():
        if contains_phrase(text, word):
            await message.delete()
            await message.channel.send(f"{message.author.mention}, сообщение удалено!", delete_after=5)
            return

    await bot.process_commands(message)

# =========================
# 💰 COMMANDS
# =========================

@bot.command()
async def bal(ctx):
    await ctx.send(f"{ctx.author.mention} 💰 {get_coins(ctx.author.id)}")

@bot.command()
async def give(ctx, amount: int):
    if ctx.author.id != MY_ID:
        return await ctx.send("❌ Нет доступа")

    if not ctx.message.reference:
        return await ctx.send("❌ Ответь на сообщение")

    msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    target = msg.author

    add_coins(target.id, amount)

    await ctx.send(f"💰 Выдано {amount} монет {target.mention}")

@bot.command()
async def shop(ctx):
    await ctx.send(
        "🛒 Магазин:\n"
        "filter — 250\n"
        "banword — 1000\n"
        "delete — 200\n"
        "remove banword — 1500"
    )

@bot.command()
async def buy(ctx, item: str, *args):
    item = item.lower()

    if item == "remove" and len(args) >= 1 and args[0] == "banword":
        item = "remove banword"
        args = args[1:]

    if item not in shop_items:
        return await ctx.send("❌ Нет такого предмета")

    price = shop_items[item]

    if get_coins(ctx.author.id) < price:
        return await ctx.send("❌ Недостаточно монет")

    # FILTER
    if item == "filter":
        if len(args) < 2:
            return await ctx.send("❌ !buy filter слово ответ")

        word = args[0].lower()
        reply = " ".join(args[1:])

        add_filter(word, reply)
        add_coins(ctx.author.id, -price)

        await ctx.send("✅ Фильтр добавлен")

    # BANWORD
    elif item == "banword":
        word = " ".join(args).lower()
        add_banword(word)
        add_coins(ctx.author.id, -price)

        await ctx.send("🚫 Добавлено")

    # DELETE
    elif item == "delete":
        add_item(ctx.author.id, "delete")
        add_coins(ctx.author.id, -price)

        await ctx.send("🗑️ Куплен delete")

    # REMOVE BANWORD
    elif item == "remove banword":
        word = " ".join(args).lower()
        remove_banword(word)
        add_coins(ctx.author.id, -price)

        await ctx.send("✅ Удалено")

@bot.command()
async def delete(ctx):
    if ctx.author.id != MY_ID:
        if not use_item(ctx.author.id, "delete"):
            return await ctx.send("❌ Нет delete")

    if not ctx.message.reference:
        return await ctx.send("❌ Ответь на сообщение")

    msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    await msg.delete()
    await ctx.message.delete()

# =========================
# 🚀 READY
# =========================

@bot.event
async def on_ready():
    print(f"Bot ready: {bot.user}")
