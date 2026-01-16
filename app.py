import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import random
import time
from dotenv import load_dotenv

# --------------------
# Setup
# --------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"
LEVELS_FILE = "levels.json"

XP_COOLDOWN = 30
xp_cooldowns = {}

# --------------------
# Bitchy Spam (DIVA)
# --------------------
BITCHY_SPAM_WORDS = ["EW", "NAUR", "BYE", "YIKES", "CRINGE"]
BITCHY_SPAM_COUNT = 5
BITCHY_DIVA_COOLDOWN = 20
diva_cooldowns = {}

# --------------------
# Auto Responses
# --------------------
AUTO_RESPONSES = {
    "hi": ["hi hi 🧸", "oh— hello~ 🎀"],
    "hello": ["hello darling 💗"],
    "hey": ["hey you 👀"],
}

EMOJI_TRIGGERS = {
    "🧸": ["don’t squeeze too tight…"],
    "🎀": ["pretty, isn’t it?"],
}

RARE_LINES = [
    "the dollhouse remembers you",
    "you feel familiar…",
]

# --------------------
# Sassy Responses
# --------------------
SASSY_TRIGGERS = {
    "bruh": ["don’t bruh me."],
    "ok": ["just ok? fascinating."],
    "what": ["read it again. slowly."],
    "bot": ["yes. and?"],
}

SASSY_RANDOM = [
    "that was… a decision.",
    "interesting choice of words.",
]

# --------------------
# Scam Words
# --------------------
SPAM_WORDS = ["free nitro", "steam gift", "click here", "free discord"]

# --------------------
# Helpers
# --------------------
def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f, indent=4)
        return default
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

config = load_json(CONFIG_FILE, {})
levels = load_json(LEVELS_FILE, {})

# --------------------
# Events
# --------------------
@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="whispers in the dollhouse 🧸"
        )
    )
    await bot.tree.sync()
    print(f"🧸 Dollhouse Lurker online as {bot.user}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    content = message.content.lower()
    now = time.time()
    guild_id = message.guild.id

    # --------------------
    # Diva → Bitchy Spam (word OR tag)
    # --------------------
    diva_triggered = False

    # Word trigger
    if "diva" in content:
        diva_triggered = True

    # User mention trigger
    for user in message.mentions:
        if "diva" in user.display_name.lower():
            diva_triggered = True
            break

    # Role mention trigger
    for role in message.role_mentions:
        if "diva" in role.name.lower():
            diva_triggered = True
            break

    if diva_triggered:
        last = diva_cooldowns.get(guild_id, 0)
        if now - last > BITCHY_DIVA_COOLDOWN:
            diva_cooldowns[guild_id] = now
            spam_word = random.choice(BITCHY_SPAM_WORDS)
            for _ in range(BITCHY_SPAM_COUNT):
                await message.channel.send(spam_word)
            return

    # --------------------
    # Scam Detection
    # --------------------
    for spam in SPAM_WORDS:
        if spam in content:
            await message.channel.send(
                f"⚠️ {message.author.mention} don’t post scammy stuff here."
            )
            return

    # --------------------
    # Cute Auto Responses
    # --------------------
    for word, replies in AUTO_RESPONSES.items():
        if word in content and random.random() < 0.15:
            await message.channel.send(random.choice(replies))
            break

    for emoji, replies in EMOJI_TRIGGERS.items():
        if emoji in message.content and random.random() < 0.25:
            await message.channel.send(random.choice(replies))
            break

    if random.random() < 0.01:
        await message.channel.send(random.choice(RARE_LINES))

    # --------------------
    # Sassy Responses
    # --------------------
    for trigger, replies in SASSY_TRIGGERS.items():
        if trigger in content and random.random() < 0.2:
            await message.channel.send(random.choice(replies))
            break

    if random.random() < 0.03:
        await message.channel.send(random.choice(SASSY_RANDOM))

    # --------------------
    # XP System
    # --------------------
    user_id = str(message.author.id)
    xp_cooldowns.setdefault(guild_id, {})
    last_time = xp_cooldowns[guild_id].get(user_id, 0)

    if now - last_time >= XP_COOLDOWN:
        xp_cooldowns[guild_id][user_id] = now
        levels.setdefault(str(guild_id), {})
        user_data = levels[str(guild_id)].setdefault(user_id, {"xp": 0, "level": 1})
        user_data["xp"] += random.randint(5, 10)

        if user_data["xp"] >= user_data["level"] * 100:
            user_data["level"] += 1
            user_data["xp"] = 0
            await message.channel.send(
                f"🎀 {message.author.mention} reached **Level {user_data['level']}**"
            )

        save_json(LEVELS_FILE, levels)

    await bot.process_commands(message)

# --------------------
# Run
# --------------------
bot.run(TOKEN)
