import discord
from discord.ext import commands
import os
import sys
from database.database import init_db
import asyncio

# --- Configuration Loading ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if DISCORD_TOKEN is None:
    if not os.path.exists('config.py'):
        print("Error: config.py not found and DISCORD_TOKEN environment variable is not set.")
        sys.exit(1)
    try:
        import config
        DISCORD_TOKEN = config.DISCORD_TOKEN
        if DISCORD_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("Error: Bot token in config.py is still the placeholder.")
            sys.exit(1)
    except ImportError:
        print("Error: Could not import config.py.")
        sys.exit(1)

# --- Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Load cogs and sync commands."""
        print("Loading cogs...")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f" -> Loaded cog: {filename}")
                except Exception as e:
                    print(f" -> Failed to load cog {filename}: {e}")

        print("Syncing application commands...")
        try:
            synced = await self.tree.sync()
            print(f" -> Synced {len(synced)} command(s)")
        except Exception as e:
            print(f" -> Failed to sync commands: {e}")

    async def on_ready(self):
        print(f'Logged in as {self.user.name} ({self.user.id})')
        print('Bot is ready to accept commands.')

bot = MyBot()

def main():
    print("Initializing database...")
    init_db()
    print("Starting bot...")
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
