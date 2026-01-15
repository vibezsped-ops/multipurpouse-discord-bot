import discord
from discord.ext import commands
from discord import app_commands
from database.database import (
    get_or_create_user, update_balance, update_user_streak,
    get_shop_items, get_user_inventory, buy_item, transfer_cash
)
from cogs.utils import (
    create_error_embed, create_success_embed, create_economy_embed,
    get_cooldown, set_cooldown, format_time_remaining
)
import random
from datetime import datetime, timedelta

# --- Constants & Message Lists (Unchanged) ---
WORK_COOLDOWN_SECONDS, BEG_COOLDOWN_SECONDS, CRIME_COOLDOWN_SECONDS, ROB_COOLDOWN_SECONDS = 3600, 300, 1800, 21600
DAILY_REWARD, WEEKLY_REWARD, MONTHLY_REWARD, STREAK_BONUS_PER_DAY = 1000, 7500, 30000, 100
WORK_MESSAGES = [("Programmer", (250, 750)), ("Burger Flipper", (100, 300))]
BEG_MESSAGES = [("A kind stranger", (20, 100)), ("The ground", (10, 50)), ("Nobody", (0, 0))]
CRIME_SUCCESS_MESSAGES = [("Bank robbery", (500, 2000)), ("Pickpocketing", (200, 800))]
CRIME_FAIL_MESSAGES = [("Store robbery", (100, 500)), ("Pickpocketing", (150, 600))]

class ShopBuyView(discord.ui.View):
    def __init__(self, items, user):
        super().__init__(timeout=180)
        self.user = user
        options = [discord.SelectOption(label=item['name'], value=str(item['item_id']), description=f"Price: {item['price']:,}") for item in items]
        self.select = discord.ui.Select(placeholder="Choose an item to buy...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(embed=create_error_embed("This is not for you!"), ephemeral=True)
            return

        item_id = int(self.select.values[0])
        item = [i for i in get_shop_items() if i['item_id'] == item_id][0]

        if buy_item(interaction.user.id, item['item_id'], item['price']):
            await interaction.response.edit_message(content=None, embed=create_success_embed("Purchase Successful", f"You bought one **{item['name']}** for {item['price']:,} cash.", self.user), view=None)
        else:
            await interaction.response.edit_message(content=None, embed=create_error_embed(f"Your purchase of **{item['name']}** failed. You may not have enough cash."), view=None)

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _claim_reward(self, interaction: discord.Interaction, reward_type: str, base_amount: int, cooldown_days: int):
        user_id = interaction.user.id; user_data = get_or_create_user(user_id)
        last_claim_str = user_data[f'last_{reward_type}']; streak = user_data[f'{reward_type}_streak']; now = datetime.utcnow()
        if last_claim_str:
            last_claim_time = datetime.fromisoformat(last_claim_str); time_since_claim = now - last_claim_time
            if time_since_claim < timedelta(days=cooldown_days):
                remaining = (last_claim_time + timedelta(days=cooldown_days)) - now
                await interaction.response.send_message(embed=create_error_embed(f"Claim again in **{format_time_remaining(remaining)}**."), ephemeral=True); return
            streak = streak + 1 if time_since_claim < timedelta(days=cooldown_days * 2) else 1
        else: streak = 1
        streak_bonus = (streak - 1) * 100 * cooldown_days; total_amount = base_amount + streak_bonus
        update_balance(user_id, cash_delta=total_amount); update_user_streak(user_id, reward_type, streak, now.isoformat())
        embed = create_economy_embed(f"{reward_type.capitalize()} Reward!", f"You received **{base_amount:,}** cash!\nYour **{streak}-day** streak gave you **{streak_bonus:,}** bonus cash.\nTotal: **{total_amount:,}** cash.", interaction.user)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="balance", description="Check your account balance.")
    async def balance(self, interaction: discord.Interaction):
        user_data = get_or_create_user(interaction.user.id)
        embed = create_economy_embed(f"{interaction.user.display_name}'s Balance", "", interaction.user)
        embed.add_field(name="💰 Cash", value=f"`{user_data['cash']:,}`", inline=True); embed.add_field(name="🏦 Bank", value=f"`{user_data['bank']:,} / {user_data['bank_capacity']:,}`", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="deposit", description="Deposit cash into your bank.")
    @app_commands.describe(amount="The amount to deposit, or 'all'.")
    async def deposit(self, interaction: discord.Interaction, amount: str):
        user_data = get_or_create_user(interaction.user.id)
        try: deposit_amount = user_data['cash'] if amount.lower() == 'all' else int(amount)
        except ValueError: await interaction.response.send_message(embed=create_error_embed("Invalid amount."), ephemeral=True); return
        if deposit_amount <= 0: await interaction.response.send_message(embed=create_error_embed("Deposit must be positive."), ephemeral=True); return
        space_in_bank = user_data['bank_capacity'] - user_data['bank']
        if deposit_amount > space_in_bank: await interaction.response.send_message(embed=create_error_embed(f"Not enough bank space. You can only deposit **{space_in_bank:,}** more."), ephemeral=True); return
        if not update_balance(interaction.user.id, cash_delta=-deposit_amount, bank_delta=deposit_amount):
            await interaction.response.send_message(embed=create_error_embed("Deposit failed. You may not have enough cash."), ephemeral=True)
        else: await interaction.response.send_message(embed=create_success_embed("Deposit Successful", f"You deposited **{deposit_amount:,}** cash.", interaction.user), ephemeral=True)

    @app_commands.command(name="withdraw", description="Withdraw cash from your bank.")
    @app_commands.describe(amount="The amount to withdraw, or 'all'.")
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        user_data = get_or_create_user(interaction.user.id)
        try: withdraw_amount = user_data['bank'] if amount.lower() == 'all' else int(amount)
        except ValueError: await interaction.response.send_message(embed=create_error_embed("Invalid amount."), ephemeral=True); return
        if withdraw_amount <= 0: await interaction.response.send_message(embed=create_error_embed("Withdrawal must be positive."), ephemeral=True); return
        if not update_balance(interaction.user.id, cash_delta=withdraw_amount, bank_delta=-withdraw_amount):
            await interaction.response.send_message(embed=create_error_embed("Withdrawal failed. You may not have enough in your bank."), ephemeral=True)
        else: await interaction.response.send_message(embed=create_success_embed("Withdrawal Successful", f"You withdrew **{withdraw_amount:,}** cash.", interaction.user), ephemeral=True)

    @app_commands.command(name="work", description="Work to earn some cash.")
    async def work(self, interaction: discord.Interaction):
        cooldown = get_cooldown(interaction.user.id, "work")
        if cooldown: await interaction.response.send_message(embed=create_error_embed(f"You can work again in **{format_time_remaining(cooldown)}**."), ephemeral=True); return
        job, amount_range = random.choice(WORK_MESSAGES); amount = random.randint(amount_range[0], amount_range[1])
        update_balance(interaction.user.id, cash_delta=amount); set_cooldown(interaction.user.id, "work", WORK_COOLDOWN_SECONDS)
        await interaction.response.send_message(embed=create_economy_embed("You Went to Work", f"You worked as a **{job}** and earned **{amount:,}** cash.", interaction.user))

    @app_commands.command(name="beg", description="Beg for some cash.")
    async def beg(self, interaction: discord.Interaction):
        cooldown = get_cooldown(interaction.user.id, "beg")
        if cooldown: await interaction.response.send_message(embed=create_error_embed(f"You can beg again in **{format_time_remaining(cooldown)}**."), ephemeral=True); return
        source, amount_range = random.choice(BEG_MESSAGES); amount = random.randint(amount_range[0], amount_range[1])
        set_cooldown(interaction.user.id, "beg", BEG_COOLDOWN_SECONDS)
        if amount > 0:
            update_balance(interaction.user.id, cash_delta=amount)
            await interaction.response.send_message(embed=create_economy_embed("You Begged for Money", f"**{source}** gave you **{amount:,}** cash.", interaction.user))
        else: await interaction.response.send_message(embed=create_economy_embed("You Begged for Money", f"**{source}** ignored you. You got no money.", interaction.user))

    @app_commands.command(name="crime", description="Commit a crime for a reward, but risk a fine.")
    async def crime(self, interaction: discord.Interaction):
        cooldown = get_cooldown(interaction.user.id, "crime")
        if cooldown: await interaction.response.send_message(embed=create_error_embed(f"You can commit a crime again in **{format_time_remaining(cooldown)}**."), ephemeral=True); return
        set_cooldown(interaction.user.id, "crime", CRIME_COOLDOWN_SECONDS)
        if random.random() < 0.6:
            crime_type, amount_range = random.choice(CRIME_SUCCESS_MESSAGES); amount = random.randint(amount_range[0], amount_range[1])
            update_balance(interaction.user.id, cash_delta=amount)
            await interaction.response.send_message(embed=create_success_embed("Crime Successful!", f"You succeeded in a **{crime_type}** and got away with **{amount:,}** cash.", interaction.user))
        else:
            crime_type, amount_range = random.choice(CRIME_FAIL_MESSAGES)
            user_data = get_or_create_user(interaction.user.id)
            fine = min(user_data['cash'], random.randint(amount_range[0], amount_range[1]))
            update_balance(interaction.user.id, cash_delta=-fine)
            await interaction.response.send_message(embed=create_error_embed(f"You failed a **{crime_type}** and were fined **{fine:,}** cash."))

    @app_commands.command(name="daily", description="Claim your daily reward.")
    async def daily(self, interaction: discord.Interaction): await self._claim_reward(interaction, "daily", DAILY_REWARD, 1)
    @app_commands.command(name="weekly", description="Claim your weekly reward.")
    async def weekly(self, interaction: discord.Interaction): await self._claim_reward(interaction, "weekly", WEEKLY_REWARD, 7)
    @app_commands.command(name="monthly", description="Claim your monthly reward.")
    async def monthly(self, interaction: discord.Interaction): await self._claim_reward(interaction, "monthly", MONTHLY_REWARD, 30)

    @app_commands.command(name="rob", description="Attempt to rob another user.")
    @app_commands.describe(user="The user to rob.")
    async def rob(self, interaction: discord.Interaction, user: discord.Member):
        if interaction.user.id == user.id: await interaction.response.send_message(embed=create_error_embed("You cannot rob yourself."), ephemeral=True); return
        cooldown = get_cooldown(interaction.user.id, "rob")
        if cooldown: await interaction.response.send_message(embed=create_error_embed(f"Lay low for **{format_time_remaining(cooldown)}**."), ephemeral=True); return
        set_cooldown(interaction.user.id, "rob", ROB_COOLDOWN_SECONDS)
        victim_data = get_or_create_user(user.id)
        if victim_data['cash'] < 500: await interaction.response.send_message(embed=create_error_embed(f"{user.display_name} is not worth robbing."), ephemeral=True); return
        if random.random() < 0.40:
            stolen_amount = int(victim_data['cash'] * random.uniform(0.15, 0.40))
            if update_balance(user.id, cash_delta=-stolen_amount):
                update_balance(interaction.user.id, cash_delta=stolen_amount)
                await interaction.response.send_message(embed=create_success_embed("Heist Successful!", f"You stole **{stolen_amount:,}** cash from {user.mention}.", interaction.user))
            else: await interaction.response.send_message(embed=create_error_embed("The robbery failed at the last second."), ephemeral=True)
        else:
            robber_data = get_or_create_user(interaction.user.id)
            fine = min(robber_data['cash'], int(robber_data['cash'] * random.uniform(0.20, 0.50)))
            if update_balance(interaction.user.id, cash_delta=-fine):
                await interaction.response.send_message(embed=create_error_embed(f"You were caught and fined **{fine:,}** cash."))
            else: await interaction.response.send_message(embed=create_error_embed("You were caught, but luckily had no cash to be fined."))

    @app_commands.command(name="pay", description="Pay another user some of your cash.")
    @app_commands.describe(user="The user to pay.", amount="The amount of cash to pay.")
    async def pay(self, interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 1]):
        if interaction.user.id == user.id: await interaction.response.send_message(embed=create_error_embed("You cannot pay yourself."), ephemeral=True); return
        if not transfer_cash(interaction.user.id, user.id, amount):
            await interaction.response.send_message(embed=create_error_embed("Transaction failed. You may not have enough cash."), ephemeral=True)
        else: await interaction.response.send_message(embed=create_success_embed("Payment Successful", f"You paid **{amount:,}** cash to {user.mention}.", interaction.user))

    @app_commands.command(name="shop", description="View the items available for purchase.")
    async def shop(self, interaction: discord.Interaction):
        items = get_shop_items()
        if not items: await interaction.response.send_message(embed=create_error_embed("The shop is empty."), ephemeral=True); return
        embed = create_economy_embed("Welcome to the Shop", "Use `/buy` to get something!", interaction.user)
        for item in items: embed.add_field(name=f"{item['name']} - {item['price']:,} cash", value=item['description'], inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy an item from the shop.")
    async def buy(self, interaction: discord.Interaction):
        items = get_shop_items()
        if not items: await interaction.response.send_message(embed=create_error_embed("The shop is empty."), ephemeral=True); return
        await interaction.response.send_message("Please select an item from the dropdown below.", view=ShopBuyView(items, interaction.user), ephemeral=True)

    @app_commands.command(name="inventory", description="View the items you own.")
    async def inventory(self, interaction: discord.Interaction):
        inventory = get_user_inventory(interaction.user.id)
        if not inventory:
            embed = create_economy_embed(f"{interaction.user.display_name}'s Inventory", "You have no items.", interaction.user)
            await interaction.response.send_message(embed=embed, ephemeral=True); return
        embed = create_economy_embed(f"{interaction.user.display_name}'s Inventory", "These are your items.", interaction.user)
        for item in inventory: embed.add_field(name=f"{item['name']} (x{item['quantity']})", value=item['description'], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
