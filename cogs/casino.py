import discord
from discord.ext import commands
from discord import app_commands
from database.database import get_or_create_user, update_balance
from cogs.utils import create_error_embed, create_economy_embed
import random
import asyncio

# --- Slots Constants ---
SLOTS_REELS = {
    '🍒': 10, '🍋': 15, '🍊': 20, '🍇': 25, '🔔': 40, '💎': 60, '💰': 100,
}
SLOTS_PAYOUTS = {
    ('🍒', '🍒', '🍒'): 5, ('🍋', '🍋', '🍋'): 8, ('🍊', '🍊', '🍊'): 12,
    ('🍇', '🍇', '🍇'): 15, ('🔔', '🔔', '🔔'): 25, ('💎', '💎', '💎'): 50,
    ('💰', '💰', '💰'): 200, ('🍒', '🍒', None): 2,
}

class CasinoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="coinflip", description="Bet on a coin flip.")
    @app_commands.describe(bet="The amount to bet.", choice="Heads or Tails.")
    @app_commands.choices(choice=[app_commands.Choice(name="Heads", value="heads"), app_commands.Choice(name="Tails", value="tails")])
    async def coinflip(self, interaction: discord.Interaction, bet: app_commands.Range[int, 1], choice: app_commands.Choice[str]):
        outcome = random.choice(["heads", "tails"])
        win = outcome == choice.value
        delta = bet if win else -bet
        if not update_balance(interaction.user.id, cash_delta=delta):
            await interaction.response.send_message(embed=create_error_embed(f"You don't have enough cash for a **{bet:,}** bet."), ephemeral=True); return
        title = "🎉 You Won!" if win else "😢 You Lost"
        desc = f"The coin landed on **{outcome}**. You {'won' if win else 'lost'} **{bet:,}** cash!"
        user_data = get_or_create_user(interaction.user.id)
        embed = create_economy_embed(title, desc, interaction.user)
        embed.add_field(name="New Balance", value=f"`{user_data['cash']:,}`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dice", description="Bet on a dice roll (1-6).")
    @app_commands.describe(bet="The amount to bet.", number="The number to bet on.")
    async def dice(self, interaction: discord.Interaction, bet: app_commands.Range[int, 1], number: app_commands.Range[int, 1, 6]):
        roll = random.randint(1, 6)
        win = roll == number
        payout = bet * 5
        delta = payout - bet if win else -bet
        if not update_balance(interaction.user.id, cash_delta=delta):
            await interaction.response.send_message(embed=create_error_embed(f"You don't have enough cash for a **{bet:,}** bet."), ephemeral=True); return
        title = "🎉 You Won!" if win else "😢 You Lost"
        desc = f"The dice landed on **{roll}**. You {'won ' + f'{payout:,}' if win else 'lost ' + f'{bet:,}'} cash."
        user_data = get_or_create_user(interaction.user.id)
        embed = create_economy_embed(title, desc, interaction.user)
        embed.add_field(name="New Balance", value=f"`{user_data['cash']:,}`")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slots", description="Play the slot machine.")
    @app_commands.describe(bet="The amount to bet.")
    async def slots(self, interaction: discord.Interaction, bet: app_commands.Range[int, 1]):
        if not update_balance(interaction.user.id, cash_delta=-bet):
            await interaction.response.send_message(embed=create_error_embed(f"You don't have enough cash for a **{bet:,}** bet."), ephemeral=True); return

        spinning_embed = create_economy_embed("Slot Machine", "Spinning...", interaction.user)
        await interaction.response.send_message(embed=spinning_embed)
        await asyncio.sleep(1.5)

        reels = [random.choice(list(SLOTS_REELS.keys())) for _ in range(3)]
        payout_multiplier = 0
        win_type = "No Win"
        if reels[0] == reels[1] == reels[2]: payout_multiplier = SLOTS_PAYOUTS.get(tuple(reels), 0); win_type = "Three of a Kind!"
        elif reels.count('🍒') == 2: payout_multiplier = SLOTS_PAYOUTS.get(('🍒', '🍒', None), 0); win_type = "Two Cherries!"

        payout = bet * payout_multiplier
        if payout > 0: update_balance(interaction.user.id, cash_delta=payout)

        title = "🎉 Jackpot!" if win_type == "Three of a Kind!" and reels[0] == '💰' else "🎉 You Won!" if payout > 0 else "😢 You Lost"
        description = f"You bet **{bet:,}** and {'won' if payout > 0 else 'lost'}.\n"
        if payout > 0: description += f"**Payout:** `{payout:,}` cash.\n**Reason:** {win_type}"

        user_data = get_or_create_user(interaction.user.id)
        result_embed = create_economy_embed(title, description, interaction.user)
        result_embed.add_field(name="Reels", value=f"[ {reels[0]} | {reels[1]} | {reels[2]} ]")
        result_embed.add_field(name="New Balance", value=f"`{user_data['cash']:,}`")
        await interaction.edit_original_response(embed=result_embed)

async def setup(bot):
    await bot.add_cog(CasinoCog(bot))
