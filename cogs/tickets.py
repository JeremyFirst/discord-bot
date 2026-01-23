import discord
from discord import app_commands
from discord.ext import commands

from config import TICKET_CATEGORY_ID, TICKET_ADMIN_ROLE_ID


TICKET_TYPES = {
    "unban_request": {
        "label": "Заявление о разбане",
        "letter": "U",
        "description": "Если ваш игровой аккаунт был заблокирован"
    },
    "player_report": {
        "label": "Жалоба на игрока",
        "letter": "P",
        "description": "Нарушение правил со стороны игрока"
    },
    "admin_report": {
        "label": "Жалоба на администратора",
        "letter": "A",
        "description": "Нарушение правил со стороны администрации"
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
        super().__init__(
            placeholder="Выберите причину создания тикета",
            options=[
                discord.SelectOption(
                    label=data["label"],
                    value=key,
                    description=data["description"]
                )
                for key, data in TICKET_TYPES.items()
            ],
            custom_id="ticket_type_select"  # 🔥 ОБЯЗАТЕЛЬНО
        )

    async def callback(self, interaction: discord.Interaction):
        t = self.values[0]

        if t == "unban_request":
            await interaction.response.send_modal(UnbanModal())
        elif t == "player_report":
            await interaction.response.send_modal(PlayerReportModal())
        elif t == "admin_report":
            await interaction.response.send_modal(AdminReportModal())
        elif t == "tech":
            await interaction.response.send_modal(TechModal())


class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())


# ===== MODALS =====

class UnbanModal(discord.ui.Modal, title="Заявление о разбане"):
    steam = discord.ui.TextInput(label="Ваш SteamID", required=True)
    ban_time = discord.ui.TextInput(label="Время и дата выдачи наказания", required=True)
    description = discord.ui.TextInput(
        label="Описание ситуации",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, "unban_request", {
            "SteamID": self.steam.value,
            "Дата наказания": self.ban_time.value,
            "Описание": self.description.value
        })


class PlayerReportModal(discord.ui.Modal, title="Жалоба на игрока"):
    violator = discord.ui.TextInput(label="SteamID / Ник нарушителя", required=True)
    time = discord.ui.TextInput(label="Время и дата нарушения", required=True)
    proofs = discord.ui.TextInput(label="Доказательства", required=False)
    description = discord.ui.TextInput(
        label="Описание ситуации",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, "player_report", {
            "Нарушитель": self.violator.value,
            "Время": self.time.value,
            "Доказательства": self.proofs.value or "Не предоставлены",
            "Описание": self.description.value
        })


class AdminReportModal(discord.ui.Modal, title="Жалоба на администратора"):
    user_steam = discord.ui.TextInput(label="Ваш SteamID", required=True)
    admin = discord.ui.TextInput(label="SteamID / Ник администратора", required=True)
    time = discord.ui.TextInput(label="Время и дата нарушения", required=True)
    proofs = discord.ui.TextInput(label="Доказательства нарушения", required=False)
    description = discord.ui.TextInput(
        label="Описание ситуации",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, "admin_report", {
            "Ваш SteamID": self.user_steam.value,
            "Администратор": self.admin.value,
            "Время": self.time.value,
            "Доказательства": self.proofs.value or "Не предоставлены",
            "Описание": self.description.value
        })


class TechModal(discord.ui.Modal, title="Техническая помощь"):
    issue = discord.ui.TextInput(
        label="Опишите проблему",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, "tech", {
            "Проблема": self.issue.value
        })

class TicketCloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Close",
            style=discord.ButtonStyle.danger,
            custom_id="ticket_close"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Close pressed (logic will be added next step).",
            ephemeral=True
        )


class TicketClaimButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Claim",
            style=discord.ButtonStyle.success,
            custom_id="ticket_claim"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Claim pressed (logic will be added next step).",
            ephemeral=True
        )


class TicketUserView(discord.ui.View):
    def __init__(self, *, is_admin: bool):
        super().__init__(timeout=None)

        self.add_item(TicketCloseButton())

        if is_admin:
            self.add_item(TicketClaimButton())


# ===== CREATE TICKET =====

async def create_ticket(interaction: discord.Interaction, ticket_type: str, fields: dict):
    guild = interaction.guild
    user = interaction.user

    category = guild.get_channel(TICKET_CATEGORY_ID)
    admin_role = guild.get_role(TICKET_ADMIN_ROLE_ID)

    ticket_number = 1  # позже заменим на MySQL
    letter = TICKET_TYPES[ticket_type]["letter"]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True)
    }

    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True
        )

    channel = await guild.create_text_channel(
        name=f"ticket-{ticket_number:04d}{letter}",
        category=category,
        overwrites=overwrites
    )

    embed = discord.Embed(
        title=f"🎫 Тикет #{ticket_number:04d}{letter}",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Автор", value=user.mention, inline=False)

    for k, v in fields.items():
        embed.add_field(name=k, value=v, inline=False)

    admin_role = guild.get_role(TICKET_ADMIN_ROLE_ID)
    is_admin = admin_role in user.roles if admin_role else False

    await channel.send(
        embed=embed,
        view=TicketUserView(is_admin=is_admin)
    )
    await interaction.response.send_message(f"✅ Тикет создан: {channel.mention}", ephemeral=True)


# ===== COG =====

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket-panel", description="Создать панель тикетов")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 Создание тикета",
            description=(
                "**Выберите подходящую категорию:**\n\n"
                "🔹 **Заявление о разбане** — если ваш аккаунт был заблокирован.\n"
                "🔹 **Жалоба на игрока** — если игрок нарушил правила.\n"
                "🔹 **Жалоба на администратора** — если администратор нарушил правила.\n"
                "🔹 **Техническая помощь** — проблемы с сервером или игрой.\n\n"
                "⚠️ Пожалуйста, указывайте точную информацию и прикладывайте доказательства."
            ),
            color=discord.Color.blurple()
        )

        await interaction.channel.send(embed=embed, view=TicketCreateView())
        await interaction.response.send_message("✅ Панель тикетов создана.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
