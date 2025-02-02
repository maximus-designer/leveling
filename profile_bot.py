import discord
from discord.ext import commands
import sqlite3
from PIL import Image, ImageDraw, ImageFont
import io

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Database setup
conn = sqlite3.connect('profiles.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, 
    xp INTEGER DEFAULT 0, 
    level INTEGER DEFAULT 1, 
    messages INTEGER DEFAULT 0,
    bio TEXT DEFAULT ''
)''')
conn.commit()

# XP system on messages
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id

    cursor.execute("SELECT xp, level, messages FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return

    xp, level, messages = user
    xp += 10  # XP per message
    messages += 1
    new_level = level

    if xp >= level * 100:  # Level up condition
        new_level += 1
        await message.channel.send(f"🎉 {message.author.mention} leveled up to {new_level}!")

    cursor.execute("UPDATE users SET xp=?, level=?, messages=? WHERE user_id=?", (xp, new_level, messages, user_id))
    conn.commit()

    await bot.process_commands(message)

# Profile command
@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    cursor.execute("SELECT xp, level, messages, bio FROM users WHERE user_id=?", (member.id,))
    user = cursor.fetchone()

    if not user:
        await ctx.send("No profile found. Start chatting to create one!")
        return

    xp, level, messages, bio = user

    # Create an image-based profile card
    img = Image.new("RGB", (400, 200), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    draw.text((20, 20), f"Profile: {member.name}", fill="white", font=font)
    draw.text((20, 50), f"XP: {xp}", fill="white", font=font)
    draw.text((20, 80), f"Level: {level}", fill="white", font=font)
    draw.text((20, 110), f"Messages: {messages}", fill="white", font=font)
    draw.text((20, 140), f"Bio: {bio[:30]}", fill="white", font=font)

    with io.BytesIO() as image_binary:
        img.save(image_binary, "PNG")
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename="profile.png"))

# Set bio command
@bot.command()
async def setbio(ctx, *, bio: str):
    user_id = ctx.author.id
    cursor.execute("UPDATE users SET bio=? WHERE user_id=?", (bio[:200], user_id))  # Limit bio length
    conn.commit()
    await ctx.send("Bio updated successfully!")

# Badges system
badges = {
    "Chatterbox": lambda messages: messages >= 1000,
    "Night Owl": lambda xp: xp >= 5000,
    "Event Master": lambda level: level >= 10
}

@bot.command()
async def badges(ctx, member: discord.Member = None):
    member = member or ctx.author
    cursor.execute("SELECT xp, level, messages FROM users WHERE user_id=?", (member.id,))
    user = cursor.fetchone()

    if not user:
        await ctx.send("No profile found.")
        return

    xp, level, messages = user
    earned_badges = [badge for badge, condition in badges.items() if condition(messages if "messages" in condition.__code__.co_varnames else (xp if "xp" in condition.__code__.co_varnames else level))]

    embed = discord.Embed(title=f"{member.name}'s Badges", color=discord.Color.gold())
    embed.add_field(name="Earned Badges", value=", ".join(earned_badges) if earned_badges else "No badges yet.", inline=False)
    
    await ctx.send(embed=embed)

# Leaderboard command
@bot.command()
async def leaderboard(ctx):
    cursor.execute("SELECT user_id, xp FROM users ORDER BY xp DESC LIMIT 5")
    top_users = cursor.fetchall()
    embed = discord.Embed(title="Leaderboard", color=discord.Color.green())

    for rank, (user_id, xp) in enumerate(top_users, 1):
        user = ctx.guild.get_member(user_id)
        embed.add_field(name=f"{rank}. {user.name if user else 'Unknown'}", value=f"XP: {xp}", inline=False)

    await ctx.send(embed=embed)

# Run the bot
bot.run("YOUR_BOT_TOKEN")
