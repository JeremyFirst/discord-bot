import discord
from discord import app_commands
from discord.ext import commands

from config import TICKET_CATEGORY_ID, TICKET_ADMIN_ROLE_ID
from core.database import Database


# ================== TICKET TYPES ==================

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


# ================== SELECT ==================

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
            custom_id="ticket_type_select"
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


# ================== MODALS ==================

class UnbanModal(discord.ui.Modal, title="Заявление о разбане"):
    steam = discord.ui.TextInput(label="Ваш SteamID:", required=True)
    ban_time = discord.ui.TextInput(label="Время и дата выдачи наказания:", required=True)
    description = discord.ui.TextInput(
        label="Описание ситуации:",
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
    violator = discord.ui.TextInput(label="SteamID / Ник нарушителя:", required=True)
    time = discord.ui.TextInput(label="Время и дата нарушения:", required=True)
    proofs = discord.ui.TextInput(label="Доказательства:", required=False)
    description = discord.ui.TextInput(
        label="Описание ситуации:",
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
    user_steam = discord.ui.TextInput(label="Ваш SteamID:", required=True)
    admin = discord.ui.TextInput(label="SteamID/Ник администратора:", required=True)
    time = discord.ui.TextInput(label="Время и дата нарушения:", required=True)
    proofs = discord.ui.TextInput(label="Доказательства нарушения:", required=False)
    description = discord.ui.TextInput(
        label="Описание ситуации:",
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


# ================== HELPERS ==================

async def get_ticket(channel_id: int):
    return await Database.fetchrow(
        "SELECT * FROM tickets WHERE channel_id = %s",
        (channel_id,)
    )

async def send_ticket_log(
    guild: discord.Guild,
    title: str,
    description: str,
    color: discord.Color
):
    from config import TICKET_LOG_CHANNEL_ID

    if not TICKET_LOG_CHANNEL_ID:
        return

    log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
    if not log_channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    await log_channel.send(embed=embed)

import os
from datetime import timezone


async def generate_transcript(channel: discord.TextChannel):
    os.makedirs("transcripts", exist_ok=True)

    filename = f"{channel.name}.html"
    filepath = f"transcripts/{filename}"

    messages_html = []
    users = set()

    async for message in channel.history(limit=None, oldest_first=True):
        users.add(message.author)

        timestamp = message.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        author = f"{message.author} ({message.author.id})"

        content = (
            message.content
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        messages_html.append(f"""
        <div class="message">
            <div class="meta">
                <span class="author">{author}</span>
                <span class="time">{timestamp}</span>
            </div>
            <div class="content">{content}</div>
        </div>
        """)

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Transcript {channel.name}</title>
        <style>
            body {{
                background-color: #2b2d31;
                color: #dcddde;
                font-family: Arial, sans-serif;
                padding: 20px;
            }}
            .message {{
                margin-bottom: 12px;
                padding: 10px;
                background: #1e1f22;
                border-radius: 6px;
            }}
            .meta {{
                font-size: 12px;
                color: #b5bac1;
                margin-bottom: 6px;
            }}
            .author {{
                font-weight: bold;
            }}
            .content {{
                white-space: pre-wrap;
            }}
        </style>
    </head>
    <body>
        <h2>Transcript for #{channel.name}</h2>
        {''.join(messages_html)}
    </body>
    </html>
    """

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filename, users


# ================== BUTTONS ==================

class TicketCloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Close",
            style=discord.ButtonStyle.danger,
            custom_id="ticket_close"
        )

    async def callback(self, interaction: discord.Interaction):
        ticket = await get_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket not found.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        admin_role = guild.get_role(TICKET_ADMIN_ROLE_ID)

        is_admin = admin_role in interaction.user.roles if admin_role else False
        is_owner = interaction.user.id == ticket["user_id"]

        # 👤 PLAYER
        if is_owner and not is_admin:
            await interaction.response.send_message(
                "Вы уверены, что хотите закрыть тикет?\n"
                "Are you sure you want to close this ticket?",
                view=CloseConfirmView(),
                ephemeral=True
            )
            return

        # 🛡 ADMIN
        if is_admin:
            await send_ticket_log(
            guild=interaction.guild,
            title="🔒 Ticket Closed",
            description=(
                f"🎫 **{interaction.channel.name}**\n"
                f"🛡 Закрыт администратором: {interaction.user.mention}\n"
                f"📍 Канал: {interaction.channel.mention}"
                ),
                color=discord.Color.red()
            )

            await Database.execute(
                "UPDATE tickets SET status = 'closed' WHERE channel_id = %s",
                (interaction.channel.id,)
            )

            embed = discord.Embed(
                title="🔒 Ticket Closed",
                description=f"Closed by {interaction.user.mention}",
                color=discord.Color.red()
            )

            await interaction.channel.send(
                embed=embed,
                view=TicketAdminClosedView()
            )

            await interaction.response.defer()


class TicketClaimButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Claim",
            style=discord.ButtonStyle.success,
            custom_id="ticket_claim"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        admin_role = guild.get_role(TICKET_ADMIN_ROLE_ID)

        if not admin_role or admin_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ You are not allowed to claim this ticket.",
                ephemeral=True
            )
            return

        embed = interaction.message.embeds[0]

        # Обновляем поле "В работе у"
        for index, field in enumerate(embed.fields):
            if field.name == "👮 В работе у":
                embed.set_field_at(
                    index,
                    name="👮 В работе у",
                    value=interaction.user.mention,
                    inline=False
                )
                break


        await interaction.message.edit(
            embed=embed,
            view=TicketUserView(is_admin=False)
        )

        await send_ticket_log(
                guild=interaction.guild,
                title="🟢 Ticket Claimed",
                description=(
                    f"🎫 **{interaction.channel.name}**\n"
                    f"👮 В работе у: {interaction.user.mention}\n"
                    f"📍 Канал: {interaction.channel.mention}"
                ),
                color=discord.Color.blue()
            )

        await interaction.response.send_message(
            "✅ Ticket claimed.",
            ephemeral=True
        )

# ================== PERSISTENT VIEW ==================

class PersistentTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(TicketCloseButton())
        self.add_item(TicketClaimButton())


# ================== VIEWS ==================

class TicketUserView(discord.ui.View):
    def __init__(self, *, is_admin: bool):
        super().__init__(timeout=None)

        self.add_item(TicketCloseButton())

        if is_admin:
            self.add_item(TicketClaimButton())


class CloseConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="Confirm Close",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_confirm_close"
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await send_ticket_log(
            guild=interaction.guild,
            title="🔒 Ticket Closed",
            description=(
                f"🎫 **{interaction.channel.name}**\n"
                f"👤 Закрыт пользователем: {interaction.user.mention}"
            ),
            color=discord.Color.red()
        )

        await Database.execute(
            "UPDATE tickets SET status = 'closed' WHERE channel_id = %s",
            (interaction.channel.id,)
        )

        await interaction.channel.delete(reason="Ticket closed by owner")

class TicketAdminClosedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Transcript",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_transcript"
    )
    async def transcript_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        from config import TRANSCRIPT_PUBLIC_URL
        import os

        await interaction.response.defer(ephemeral=True)

        filename, users = await generate_transcript(interaction.channel)
        url = f"{TRANSCRIPT_PUBLIC_URL}/transcripts/{filename}"

        user_list = "\n".join(
            f"{i+1}. {user.mention}" for i, user in enumerate(users)
        )

        ticket = await get_ticket(interaction.channel.id)

        embed = discord.Embed(
            title="📄 Ticket Transcript",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Ticket Owner",
            value=f"<@{ticket['user_id']}>",
            inline=True
        )

        embed.add_field(
            name="Ticket Name",
            value=interaction.channel.name,
            inline=True
        )

        embed.add_field(
            name="Panel Name",
            value=TICKET_TYPES[ticket["ticket_type"]]["label"],
            inline=False
        )

        embed.add_field(
            name="Users in transcript",
            value=user_list or "—",
            inline=False
        )

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Direct Link",
                style=discord.ButtonStyle.link,
                url=url
            )
        )

        log_channel = interaction.guild.get_channel(
            int(os.getenv("TICKET_LOG_CHANNEL_ID"))
        )

        if log_channel:
            await log_channel.send(embed=embed, view=view)

        await send_ticket_log(
            guild=interaction.guild,
            title="📄 Transcript Generated",
            description=f"🎫 **{interaction.channel.name}**",
            color=discord.Color.blurple()
        )

# ================== CREATE TICKET ==================

async def create_ticket(interaction: discord.Interaction, ticket_type: str, fields: dict):
    guild = interaction.guild
    user = interaction.user

    category = guild.get_channel(TICKET_CATEGORY_ID)
    admin_role = guild.get_role(TICKET_ADMIN_ROLE_ID)

    row = await Database.fetchrow(
        "SELECT MAX(ticket_number) AS max_number FROM tickets"
    )
    ticket_number = (row["max_number"] or 0) + 1

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

    await Database.execute(
        """
        INSERT INTO tickets (ticket_number, ticket_type, ticket_letter, user_id, channel_id)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            ticket_number,
            ticket_type,
            letter,
            user.id,
            channel.id
        )
    )

    embed = discord.Embed(
    title=f"🎫 Тикет #{ticket_number:04d}{letter}",
    description="Информация по обращению:",
    color=discord.Color.blurple()
)

    # Аватар пользователя
    embed.set_thumbnail(url=user.display_avatar.url)

    # Автор
    embed.add_field(
        name="👤 Автор тикета",
        value=user.mention,
        inline=False
    )

    # Кто занимается тикетом (пока пусто)
    embed.add_field(
        name="👮 В работе у",
        value="—",
        inline=False
    )

    # Данные из формы
    for k, v in fields.items():
        embed.add_field(
            name=k,
            value=v,
            inline=False
        )

    embed.set_footer(
        text="Пожалуйста, ожидайте ответа администрации"
    )


    is_admin = admin_role in user.roles if admin_role else False

    await channel.send(
    embed=embed,
    view=PersistentTicketView()
    )

    await interaction.response.send_message(
        f"✅ Тикет создан: {channel.mention}",
        ephemeral=True
    )

    await send_ticket_log(
    guild=guild,
    title="🆕 Ticket Created",
    description=(
        f"🎫 **{channel.name}**\n"
        f"👤 Автор: {user.mention}\n"
        f"📂 Тип: {TICKET_TYPES[ticket_type]['label']}\n"
        f"📍 Канал: {channel.mention}"
    ),
    color=discord.Color.green()
)


# ================== COG ==================

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

        await interaction.channel.send(
            embed=embed,
            view=TicketCreateView()
        )

        await interaction.response.send_message(
            "✅ Панель тикетов создана.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
