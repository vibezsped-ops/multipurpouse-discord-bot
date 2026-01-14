import discord
from discord.ext import commands
import os
import sys
from database.database import init_db
import asyncio

# --- Configuration Loading ---
# Prioritize environment variables for production, but fall back to config.py for local development.
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

if DISCORD_TOKEN is None:
    # If the environment variable is not set, try to load from config.py
    if not os.path.exists('config.py'):
        print("Error: config.py not found and DISCORD_TOKEN environment variable is not set.")
        print("Please create config.py from config.py.example or set the environment variable.")
        sys.exit(1)

    try:
        import config
        DISCORD_TOKEN = config.DISCORD_TOKEN
        if DISCORD_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("Error: Bot token in config.py is still the placeholder.")
            print("Please open config.py and replace 'YOUR_BOT_TOKEN_HERE' with your bot's token.")
            sys.exit(1)
    except ImportError:
        # This case is redundant due to the os.path.exists check, but it's good practice.
        print("Error: Could not import config.py.")
        sys.exit(1)
# --- End of Configuration Loading ---

# Set up intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """A special method that is called after login and before connecting to the Gateway."""
        # Load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"Loaded cog: {filename[:-3]}")
                except Exception as e:
                    print(f"Failed to load cog {filename[:-3]}: {e}")

        # Sync application commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self):
        """Event that fires when the bot is ready."""
        print(f'Logged in as {self.user.name}')
        print('Bot is ready to accept commands.')

bot = MyBot()

def main():
    # Initialize the database
    init_db()

    # Run the bot
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
