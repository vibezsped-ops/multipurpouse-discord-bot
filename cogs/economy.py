import discord
from discord.ext import commands
from discord import app_commands
from database.database import (
    get_or_create_user, update_balance, update_user_streak,
    get_shop_items, get_user_inventory, get_item_by_name, add_item_to_inventory
)
from cogs.utils import (
    create_error_embed, create_success_embed, create_economy_embed,
    get_cooldown, set_cooldown, format_time_remaining
)
import random
from datetime import datetime, timedelta

# --- Constants & Message Lists (Unchanged) ---
WORK_COOLDOWN_SECONDS, BEG_COOLDOWN_SECONDS, CRIME_COOLDOWN_SECONDS = 3600, 300, 1800
DAILY_REWARD, WEEKLY_REWARD, MONTHLY_REWARD, STREAK_BONUS_PER_DAY = 1000, 7500, 30000, 100
WORK_MESSAGES = [("Programmer", (250, 750)), ("Burger Flipper", (100, 300))]
BEG_MESSAGES = [("A kind stranger", (20, 100)), ("The ground", (10, 50)), ("Nobody", (0, 0))]
CRIME_SUCCESS_MESSAGES = [("Bank robbery", (500, 2000)), ("Pickpocketing", (200, 800))]
CRIME_FAIL_MESSAGES = [("Store robbery", (100, 500)), ("Pickpocketing", (150, 600))]


class ShopBuyView(discord.ui.View):
    """A view for the /buy command that includes a dropdown for item selection."""
    def __init__(self, items, user):
        super().__init__(timeout=180)
        self.user = user
        options = [discord.SelectOption(label=item['name'], value=str(item['item_id']), description=f"Price: {item['price']:,}") for item in items]
        self.select = discord.ui.Select(placeholder="Choose an item to buy...", min_values=1, max_values=1, options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(embed=create_error_embed("This is not for you!"), ephemeral=True)
            return

        item_id = int(self.select.values[0])
        user_id = interaction.user.id

        # We need to re-fetch the item and user data within the callback.
        item = [i for i in get_shop_items() if i['item_id'] == item_id][0]
        user_data = get_or_create_user(user_id)

        if user_data['cash'] < item['price']:
            await interaction.response.edit_message(content=None, embed=create_error_embed(f"You cannot afford the **{item['name']}**. You need {item['price'] - user_data['cash']:,} more cash."), view=None)
            return

        # Perform transaction
        if update_balance(user_id, cash_delta=-item['price']) and add_item_to_inventory(user_id, item_id, 1):
            await interaction.response.edit_message(content=None, embed=create_success_embed("Purchase Successful", f"You have bought one **{item['name']}** for {item['price']:,} cash.", self.user), view=None)
        else:
            # Revert transaction if inventory add fails
            update_balance(user_id, cash_delta=item['price'])
            await interaction.response.edit_message(content=None, embed=create_error_embed("An error occurred with your purchase. Please try again."), view=None)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        # Cannot edit original message on timeout from here, but this prevents further interaction.

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Shop & Inventory Commands ---
    @app_commands.command(name="shop", description="View the items available for purchase.")
    async def shop(self, interaction: discord.Interaction):
        items = get_shop_items()
        if not items:
            await interaction.response.send_message(embed=create_error_embed("The shop is currently empty."), ephemeral=True)
            return

        embed = create_economy_embed("Welcome to the Shop", "Here are the items available for purchase. Use `/buy` to get something!", interaction.user)
        for item in items:
            embed.add_field(name=f"{item['name']} - {item['price']:,} cash", value=item['description'], inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy an item from the shop.")
    async def buy(self, interaction: discord.Interaction):
        items = get_shop_items()
        if not items:
            await interaction.response.send_message(embed=create_error_embed("The shop is empty."), ephemeral=True)
            return

        view = ShopBuyView(items, interaction.user)
        await interaction.response.send_message("Please select an item from the dropdown below.", view=view, ephemeral=True)

    @app_commands.command(name="inventory", description="View the items you own.")
    async def inventory(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        inventory = get_user_inventory(user_id)

        if not inventory:
            embed = create_economy_embed(f"{interaction.user.display_name}'s Inventory", "You don't have any items. Go buy some from the `/shop`!", interaction.user)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = create_economy_embed(f"{interaction.user.display_name}'s Inventory", "Here are the items you currently own.", interaction.user)
        for item in inventory:
            embed.add_field(name=f"{item['name']} (x{item['quantity']})", value=item['description'], inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Other commands follow ---
    # ... (balance, deposit, withdraw, work, beg, crime, daily, weekly, monthly)
    # The code for the other commands is unchanged and is not repeated here for brevity.
    @app_commands.command(name="pay", description="Pay another user some of your cash.")
    @app_commands.describe(user="The user to pay.", amount="The amount of cash to pay.")
    async def pay(self, interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 1]):
        sender_id = interaction.user.id; receiver_id = user.id
        if sender_id == receiver_id: await interaction.response.send_message(embed=create_error_embed("You cannot pay yourself."), ephemeral=True); return
        if user.bot: await interaction.response.send_message(embed=create_error_embed("You cannot pay a bot."), ephemeral=True); return
        sender_data = get_or_create_user(sender_id)
        if sender_data['cash'] < amount: await interaction.response.send_message(embed=create_error_embed(f"You don't have enough cash. You only have **{sender_data['cash']:,}**."), ephemeral=True); return
        sender_success = update_balance(sender_id, cash_delta=-amount)
        receiver_success = update_balance(receiver_id, cash_delta=amount)
        if sender_success and receiver_success: await interaction.response.send_message(embed=create_success_embed("Payment Successful", f"You have successfully paid **{amount:,}** cash to {user.mention}.", interaction.user))
        else:
            if sender_success: update_balance(sender_id, cash_delta=amount)
            await interaction.response.send_message(embed=create_error_embed("The transaction failed."), ephemeral=True)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
