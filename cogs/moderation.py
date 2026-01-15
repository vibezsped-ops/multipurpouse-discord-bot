import discord
from discord.ext import commands
from discord import app_commands
from cogs.utils import create_error_embed, create_success_embed
from typing import Optional
from datetime import timedelta

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kicks a user from the server.")
    @app_commands.describe(member="The member to kick.", reason="The reason for kicking the member.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        # ... (kick command logic)
        if member == interaction.user: await interaction.response.send_message(embed=create_error_embed("You cannot kick yourself."), ephemeral=True); return
        if member.top_role >= interaction.user.top_role: await interaction.response.send_message(embed=create_error_embed("You cannot kick this member."), ephemeral=True); return
        try: await member.kick(reason=reason or f"Kicked by {interaction.user.name}"); await interaction.response.send_message(embed=create_success_embed("Member Kicked", f"{member.mention} was kicked.", interaction.user))
        except Exception as e: await interaction.response.send_message(embed=create_error_embed(f"Failed to kick: {e}"), ephemeral=True)

    @app_commands.command(name="ban", description="Bans a user from the server.")
    @app_commands.describe(member="The member to ban.", reason="The reason for the ban.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        # ... (ban command logic)
        if member == interaction.user: await interaction.response.send_message(embed=create_error_embed("You cannot ban yourself."), ephemeral=True); return
        if member.top_role >= interaction.user.top_role: await interaction.response.send_message(embed=create_error_embed("You cannot ban this member."), ephemeral=True); return
        try: await member.ban(reason=reason or f"Banned by {interaction.user.name}"); await interaction.response.send_message(embed=create_success_embed("Member Banned", f"{member.mention} was banned.", interaction.user))
        except Exception as e: await interaction.response.send_message(embed=create_error_embed(f"Failed to ban: {e}"), ephemeral=True)

    @app_commands.command(name="timeout", description="Timeouts a user for a specified duration.")
    @app_commands.describe(member="The member to timeout.", minutes="Duration in minutes.", hours="Duration in hours.", days="Duration in days.", reason="Reason for the timeout.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 0] = 0, hours: app_commands.Range[int, 0] = 0, days: app_commands.Range[int, 0] = 0, reason: Optional[str] = None):
        # ... (timeout command logic)
        if member == interaction.user: await interaction.response.send_message(embed=create_error_embed("You cannot timeout yourself."), ephemeral=True); return
        if member.top_role >= interaction.user.top_role: await interaction.response.send_message(embed=create_error_embed("You cannot timeout this member."), ephemeral=True); return
        duration = timedelta(minutes=minutes, hours=hours, days=days)
        if duration.total_seconds() <= 0: await interaction.response.send_message(embed=create_error_embed("Please provide a valid duration."), ephemeral=True); return
        if duration.days > 27: await interaction.response.send_message(embed=create_error_embed("Timeout cannot exceed 27 days."), ephemeral=True); return
        try:
            await member.timeout(duration, reason=reason or f"Timed out by {interaction.user.name}")
            duration_str = []
            if days > 0: duration_str.append(f"{days} day(s)")
            if hours > 0: duration_str.append(f"{hours} hour(s)")
            if minutes > 0: duration_str.append(f"{minutes} minute(s)")
            await interaction.response.send_message(embed=create_success_embed("Member Timed Out", f"{member.mention} has been timed out for {' '.join(duration_str)}.", interaction.user))
        except Exception as e: await interaction.response.send_message(embed=create_error_embed(f"Failed to timeout: {e}"), ephemeral=True)

    @app_commands.command(name="purge", description="Deletes a specified number of messages from the channel.")
    @app_commands.describe(amount="The number of messages to delete (up to 100).")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            deleted = await interaction.channel.purge(limit=amount)
            embed = create_success_embed("Purge Complete", f"Successfully deleted **{len(deleted)}** message(s) from this channel.", interaction.user)
            await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send(embed=create_error_embed("I do not have permission to delete messages in this channel."))
        except Exception as e:
            await interaction.followup.send(embed=create_error_embed(f"An error occurred: {e}"))


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
