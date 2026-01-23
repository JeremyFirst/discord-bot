import discord
from discord import app_commands
from discord.ext import commands

from config import TICKET_CATEGORY_ID, TICKET_ADMIN_ROLE_ID


# ===== КОНФИГ ТИПОВ ТИКЕТОВ =====

TICKET_TYPES = {
    "appeal": {
        "label": "Апелляция",
        "letter": "A",
        "description": "Обжалование наказания"
    },
    "player_report": {
        "label": "Жалоба на игрока",
        "letter": "P",
        "description": "Сообщить о нарушении игрока"
    },
    "admin_report": {
        "label": "Жалоба на администратора",
        "letter": "M",
        "description": "Сообщить о нарушении администратора"
    },
    "tech": {
        "label": "Техническая помощь",
        "letter": "T",
        "description": "Проблемы с игрой или сервером"
    }
}


# ===== SELECT =====

class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=data["label"],
                value=key,
                description=data["description"]
            )
            for key, data in TICKET_TYPES.items()
        ]

        super().__init__(
            placeholder="Выберите причину тикета",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]

        if ticket_type == "player_report":
            await interaction.response.send_modal(PlayerReportModal())
        elif ticket_type == "appeal":
            await interaction.response.send_modal(AppealModal())
        elif ticket_type == "admin_report":
            await interaction.response.send_modal(AdminReportModal())
        elif ticket_type == "tech":
            await interaction.response.send_modal(TechModal())


class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())


# ===== MODALS =====

class PlayerReportModal(discord.ui.Modal, title="Жалоба на игрока"):
    steam = discord.ui.TextInput(
        label="SteamID или ник нарушителя",
        required=True,
        max_length=64
    )
    time = discord.ui.TextInput(
        label="Время происшествия",
        required=True,
        max_length=64
    )
    description = discord.ui.TextInput(
        label="Описание нарушения",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(
            interaction,
            "player_report",
            {
                "SteamID / Ник": self.steam.value,
                "Время": self.time.value,
                "Описание": self.description.value
            }
        )


class AppealModal(discord.ui.Modal, title="Апелляция"):
    reason = discord.ui.TextInput(
        label="Причина апелляции",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(
            interaction,
            "appeal",
            {"Причина": self.reason.value}
        )


class AdminReportModal(discord.ui.Modal, title="Жалоба на администратора"):
    admin = discord.ui.TextInput(
        label="Ник администратора",
        required=True,
        max_length=64
    )
    description = discord.ui.TextInput(
        label="Описание ситуации",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(
            interaction,
            "admin_report",
            {
                "Администратор": self.admin.value,
                "Описание": self.description.value
            }
        )


class TechModal(discord.ui.Modal, title="Техническая помощь"):
    issue = discord.ui.TextInput(
        label="Опишите проблему",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(
            interaction,
            "tech",
            {"Проблема": self.issue.value}
        )


# ===== СОЗДАНИЕ ТИКЕТА =====

async def create_ticket(
    interaction: discord.Interaction,
    ticket_type: str,
    fields: dict
):
    guild = interaction.guild
    user = interaction.user

    category = guild.get_channel(TICKET_CATEGORY_ID)
    admin_role = guild.get_role(TICKET_ADMIN_ROLE_ID)

    if not category:
        await interaction.response.send_message(
            "❌ Категория для тикетов не найдена. Сообщите администрации.",
            ephemeral=True
        )
        return

    # ⚠️ ВРЕМЕННАЯ НУМЕРАЦИЯ (позже заменим на MySQL)
    ticket_number = 1
    letter = TICKET_TYPES[ticket_type]["letter"]
    channel_name = f"ticket-{ticket_number:04d}{letter}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }

    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True
        )

    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites
    )

    embed = discord.Embed(
        title=f"🎫 Тикет #{ticket_number:04d}{letter}",
        color=discord.Color.blurple()
    )

    embed.add_field(name="Автор", value=user.mention, inline=False)

    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)

    await channel.send(embed=embed)

    await interaction.response.send_message(
        f"✅ Тикет создан: {channel.mention}",
        ephemeral=True
    )


# ===== COG =====

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ticket-panel",
        description="Создать панель тикетов"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 Тикет-система",
            description=(
                "Выберите причину обращения в меню ниже.\n\n"
                "⚠️ Пожалуйста, выбирайте категорию корректно — "
                "это ускорит обработку."
            ),
            color=discord.Color.blurple()
        )

        await interaction.channel.send(
            embed=embed,
            view=TicketCreateView()
        )

        await interaction.response.send_message(
            "✅ Панель тикетов создана.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
