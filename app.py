import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import random
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
XP_COOLDOWN = 30  # seconds
xp_cooldowns = {}

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

    await bot.tree.sync()  # GLOBAL sync
    print(f"🧸 Dollhouse Lurker online as {bot.user}")
    print("✅ Global slash commands synced")

@bot.event
async def on_member_join(member: discord.Member):
    guild_id = str(member.guild.id)
    guild_config = config.get(guild_id)
    if not guild_config:
        return

    # Autorole
    role_id = guild_config.get("autorole")
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)

    # Welcome channel
    channel_id = guild_config.get("welcome_channel")
    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)
    if not channel:
        return

    required_channels = " ".join(
        f"<#{cid}>" for cid in guild_config.get("required_channels", [])
    )

    custom_message = guild_config.get(
        "welcome_message",
        "Welcome {user} to **{server}**! Please check {channels}"
    )

    message_text = custom_message.format(
        user=member.mention,
        server=member.guild.name,
        channels=required_channels or "the server channels",
        membercount=member.guild.member_count
    )

    embed = discord.Embed(
        description=message_text,
        color=discord.Color.pink()
    )

    embed.set_author(
        name=f"{member.name} joined the dollhouse",
        icon_url=member.display_avatar.url
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Member #{member.guild.member_count}")

    await channel.send(embed=embed)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    levels.setdefault(guild_id, {})
    user_data = levels[guild_id].setdefault(user_id, {"xp": 0, "level": 1})

    xp_gain = random.randint(5, 10)
    user_data["xp"] += xp_gain

    next_level_xp = user_data["level"] * 100
    if user_data["xp"] >= next_level_xp:
        user_data["level"] += 1
        user_data["xp"] = 0
        await message.channel.send(
            f"🎀 {message.author.mention} reached **Level {user_data['level']}**!"
        )

    save_json(LEVELS_FILE, levels)
    await bot.process_commands(message)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    # Anti-spam cooldown
    now = message.created_at.timestamp()
    xp_cooldowns.setdefault(guild_id, {})
    last_time = xp_cooldowns[guild_id].get(user_id, 0)

    if now - last_time < XP_COOLDOWN:
        await bot.process_commands(message)
        return

    xp_cooldowns[guild_id][user_id] = now

    # Level data
    levels.setdefault(guild_id, {})
    user_data = levels[guild_id].setdefault(user_id, {"xp": 0, "level": 1})

    user_data["xp"] += random.randint(5, 10)
    next_level_xp = user_data["level"] * 100

    if user_data["xp"] >= next_level_xp:
        user_data["level"] += 1
        user_data["xp"] = 0

        # Level channel
        level_channel_id = config.get(guild_id, {}).get("level_channel")
        level_channel = (
            message.guild.get_channel(level_channel_id)
            if level_channel_id else message.channel
        )

        embed = discord.Embed(
            title="🎀 Level Up!",
            description=f"{message.author.mention} reached **Level {user_data['level']}**",
            color=discord.Color.pink()
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)

        await level_channel.send(embed=embed)

    save_json(LEVELS_FILE, levels)
    await bot.process_commands(message)

# --------------------
# Slash Commands
# --------------------
@app_commands.guild_only()
@bot.tree.command(name="setwelcome", description="Set the welcome channel")
@app_commands.checks.has_permissions(administrator=True)
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    config.setdefault(guild_id, {})
    config[guild_id]["welcome_channel"] = channel.id
    save_json(CONFIG_FILE, config)

    await interaction.response.send_message(
        f"✅ Welcome channel set to {channel.mention}", ephemeral=True
    )

@app_commands.guild_only()
@bot.tree.command(name="setautorole", description="Set autorole for new members")
@app_commands.checks.has_permissions(administrator=True)
async def setautorole(interaction: discord.Interaction, role: discord.Role):
    guild_id = str(interaction.guild.id)
    config.setdefault(guild_id, {})
    config[guild_id]["autorole"] = role.id
    save_json(CONFIG_FILE, config)

    await interaction.response.send_message(
        f"🎭 Autorole set to **{role.name}**", ephemeral=True
    )

@app_commands.guild_only()
@bot.tree.command(name="addrequired", description="Add a required channel to welcome embed")
@app_commands.checks.has_permissions(administrator=True)
async def addrequired(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    config.setdefault(guild_id, {})
    config[guild_id].setdefault("required_channels", [])

    if channel.id not in config[guild_id]["required_channels"]:
        config[guild_id]["required_channels"].append(channel.id)

    save_json(CONFIG_FILE, config)
    await interaction.response.send_message(
        f"📌 Added {channel.mention} to welcome message", ephemeral=True
    )

@app_commands.guild_only()
@bot.tree.command(name="setwelcomemessage", description="Set a custom welcome message")
@app_commands.checks.has_permissions(administrator=True)
async def setwelcomemessage(interaction: discord.Interaction, message: str):
    guild_id = str(interaction.guild.id)
    config.setdefault(guild_id, {})
    config[guild_id]["welcome_message"] = message
    save_json(CONFIG_FILE, config)

    await interaction.response.send_message(
        "🧸 Custom welcome message saved!", ephemeral=True
    )

@app_commands.guild_only()
@bot.tree.command(name="help", description="Show Dollhouse Lurker help menu")
async def help_command(
    interaction: discord.Interaction,
    command: str | None = None
):
    embed_color = discord.Color.pink()

    if command:
        command = command.lower()

        command_help = {
            "setwelcome": "Set the welcome channel.\n**Admin only**",
            "setautorole": "Set the autorole for new members.\n**Admin only**",
            "addrequired": "Add a channel to mention in the welcome embed.\n**Admin only**",
            "setwelcomemessage": "Set a custom welcome message using placeholders.\n**Admin only**",
            "level": "Check your current level and XP.",
            "help": "Show the help menu."
        }

        if command not in command_help:
            await interaction.response.send_message(
                "❌ That command does not exist.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🧸 Help — /{command}",
            description=command_help[command],
            color=embed_color
        )
        embed.set_footer(text="Dollhouse Lurker • Slash Commands Only")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Main help menu
    embed = discord.Embed(
        title="🧸 Dollhouse Lurker Help",
        description="A quiet watcher of the dollhouse.\nAll commands are **slash commands**.",
        color=embed_color
    )

    embed.add_field(
        name="🎀 Welcome System",
        value=(
            "`/setwelcome` – Set welcome channel\n"
            "`/setwelcomemessage` – Custom welcome text\n"
            "`/addrequired` – Mention required channels"
        ),
        inline=False
    )

    embed.add_field(
        name="🎭 Roles",
        value="`/setautorole` – Assign role on join",
        inline=False
    )

    embed.add_field(
        name="✨ Levels",
        value="`/level` – View your level & XP",
        inline=False
    )

    embed.add_field(
        name="🧸 Help",
        value="`/help [command]` – Get help for a command",
        inline=False
    )

    embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
    embed.set_footer(text="Dollhouse Lurker • Watching quietly")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@app_commands.guild_only()
@bot.tree.command(name="level", description="Check your level")
async def level(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)

    user_data = levels.get(guild_id, {}).get(user_id)
    if not user_data:
        await interaction.response.send_message(
            "You don't have a level yet!", ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"🧸 **Level:** {user_data['level']}\n✨ **XP:** {user_data['xp']}",
        ephemeral=True
    )

@app_commands.guild_only()
@bot.tree.command(name="leaderboard", description="View the server level leaderboard")
async def leaderboard(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    guild_levels = levels.get(guild_id)

    if not guild_levels:
        await interaction.response.send_message(
            "No one has leveled up yet 🧸",
            ephemeral=True
        )
        return

    # Sort users by level first, then XP
    sorted_users = sorted(
        guild_levels.items(),
        key=lambda x: (x[1]["level"], x[1]["xp"]),
        reverse=True
    )

    embed = discord.Embed(
        title="🏆 Dollhouse Leaderboard",
        description="Top lurkers in the dollhouse",
        color=discord.Color.pink()
    )

    rank = 1
    for user_id, data in sorted_users[:10]:
        member = interaction.guild.get_member(int(user_id))
        if not member:
            continue

        embed.add_field(
            name=f"{rank}. {member.display_name}",
            value=f"🧸 Level **{data['level']}** • ✨ XP **{data['xp']}**",
            inline=False
        )
        rank += 1

    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text="Dollhouse Lurker • Watching who grows")

    await interaction.response.send_message(embed=embed)

@app_commands.guild_only()
@bot.tree.command(name="setlevelchannel", description="Set the channel for level-up messages")
@app_commands.checks.has_permissions(administrator=True)
async def setlevelchannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    guild_id = str(interaction.guild.id)
    config.setdefault(guild_id, {})
    config[guild_id]["level_channel"] = channel.id
    save_json(CONFIG_FILE, config)

    await interaction.response.send_message(
        f"✨ Level-up messages will now be sent to {channel.mention}",
        ephemeral=True
    )

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True
        )

    elif isinstance(error, app_commands.NoPrivateMessage):
        await interaction.response.send_message(
            "❌ This command can only be used in servers.",
            ephemeral=True
        )

    else:
        await interaction.response.send_message(
            "⚠️ Something went wrong while running this command.",
            ephemeral=True
        )
        raise error

# --------------------
# Run
# --------------------
bot.run(TOKEN)
