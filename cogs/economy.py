import discord
from discord.ext import commands
from discord import app_commands
from database.database import get_or_create_user

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your account balance.")
    async def balance(self, interaction: discord.Interaction):
        """Displays the user's cash and bank balance."""
        user_id = interaction.user.id
        user_data = get_or_create_user(user_id)

        if user_data is None:
            # Send an error message if the database operation failed
            embed = discord.Embed(
                title="Error",
                description="Could not retrieve your balance. Please try again later.",
                color=discord.Color.dark_red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create a professional-looking embed for the response
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Balance",
            color=discord.Color.gold()  # Gold color for economy commands
        )
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)

        cash_value = f"{user_data['cash']:,}"
        bank_value = f"{user_data['bank']:,} / {user_data['bank_capacity']:,}"
        net_worth = f"{user_data['cash'] + user_data['bank']:,}"

        embed.add_field(name="💰 Cash", value=f"`{cash_value}`", inline=True)
        embed.add_field(name="🏦 Bank", value=f"`{bank_value}`", inline=True)
        embed.add_field(name="💼 Net Worth", value=f"`{net_worth}`", inline=False)

        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
