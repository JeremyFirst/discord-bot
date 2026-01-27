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
        author_name = str(message.author)
        author_id = message.author.id
        avatar_url = message.author.display_avatar.url

        content_parts = []

        # обычный текст
        if message.content:
            safe_content = (
                message.content
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            content_parts.append(f"<div>{safe_content}</div>")

        # embeds (ОЧЕНЬ ВАЖНО)
        for embed in message.embeds:
            embed_block = ""

            if embed.title:
                embed_block += f"<div class='embed-title'>{embed.title}</div>"

            if embed.description:
                desc = (
                    embed.description
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                embed_block += f"<div class='embed-desc'>{desc}</div>"

            for field in embed.fields:
                embed_block += (
                    f"<div class='embed-field'>"
                    f"<b>{field.name}</b><br>{field.value}"
                    f"</div>"
                )

            if embed_block:
                content_parts.append(
                    f"<div class='embed'>{embed_block}</div>"
                )

        # если вообще ничего нет
        if not content_parts:
            content_parts.append("<i>(empty message)</i>")

        content = "".join(content_parts)

        messages_html.append(f"""
        <div class="message">
            <img class="avatar" src="{avatar_url}">
            <div class="body">
                <div class="meta">
                    <span class="author">{author_name}</span>
                    <span class="userid">({author_id})</span>
                    <span class="time">{timestamp}</span>
                </div>
                <div class="content">{content}</div>
            </div>
        </div>
        """)

    html = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>Transcript {channel.name}</title>
    <style>
        body {{
            background-color: #0f172a;
            color: #e5e7eb;
            font-family: Inter, Arial, sans-serif;
            padding: 30px;
        }}

        .container {{
            max-width: 1100px;
            margin: auto;
        }}

        .header {{
            display: flex;
            align-items: center;
            gap: 20px;
            padding: 20px;
            background: #020617;
            border-radius: 12px;
            margin-bottom: 30px;
        }}

        .header h1 {{
            margin: 0;
            font-size: 22px;
        }}

        .info {{
            background: #020617;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
        }}

        .info div {{
            font-size: 14px;
        }}

        .label {{
            color: #94a3b8;
            font-size: 12px;
        }}

        .message {{
            display: flex;
            gap: 12px;
            background: #020617;
            padding: 14px;
            border-radius: 10px;
        }}

        .avatar {{
            width: 42px;
            height: 42px;
            border-radius: 50%;
            object-fit: cover;
        }}

        .body {{
            flex: 1;
        }}

        .author {{
            font-weight: 600;
            color: #38bdf8;
        }}

        .userid {{
            color: #64748b;
            font-size: 11px;
            margin-left: 4px;
        }}

        .time {{
            color: #94a3b8;
            font-size: 11px;
            margin-left: 8px;
       }}

        .meta {{
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 6px;
        }}

        .author {{
            font-weight: 600;
            color: #38bdf8;
        }}

        .content {{
            white-space: pre-wrap;
            line-height: 1.4;
        }}

        .embed {{
            background: #020617;
            border-left: 4px solid #5865f2;
            padding: 10px;
            border-radius: 6px;
            margin-top: 6px;
        }}

        .embed-title {{
            font-weight: 600;
            margin-bottom: 4px;
        }}

        .embed-desc {{
            font-size: 14px;
            margin-bottom: 6px;
        }}

        .embed-field {{
            font-size: 13px;
            margin-top: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 Transcript — #{channel.name}</h1>
        </div>

        <div class="info">
            <div>
                <div class="label">Channel</div>
                <div>#{channel.name}</div>
            </div>
            <div>
                <div class="label">Total messages</div>
                <div>{len(messages_html)}</div>
            </div>
        </div>

        <div class="messages">
            {''.join(messages_html)}
        </div>
    </div>
</body>
</html>
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filename, users

# ================== DELETE TASK ==================

async def delete_ticket_channel(channel, guild, user):
    import asyncio

    await channel.send("🗑 **Ticket will be deleted in 5 seconds...**")
    await asyncio.sleep(5)

    await send_ticket_log(
        guild=guild,
        title="🗑 Ticket Deleted",
        description=(
            f"🎫 **{channel.name}**\n"
            f"🛡 Удалён администратором: {user.mention}"
        ),
        color=discord.Color.dark_red()
    )

    await Database.execute(
        "UPDATE tickets SET status = 'deleted' WHERE channel_id = %s",
        (channel.id,)
    )

    await channel.delete(
        reason=f"Ticket deleted by {user}"
    )

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
            await interaction.followup.send(
                "❌ Ticket not found.",
                ephemeral=True,
                delete_after=5
            )
            return

        guild = interaction.guild
        admin_role = guild.get_role(TICKET_ADMIN_ROLE_ID)

        is_admin = admin_role in interaction.user.roles if admin_role else False
        is_owner = interaction.user.id == ticket["user_id"]

        # 👤 USER
        if is_owner and not is_admin:
            await interaction.response.send_message(
                "❗ Вы уверены, что хотите закрыть тикет?\n"
                "Are you sure you want to close this ticket?",
                view=CloseConfirmView(),
                ephemeral=True
            )
            return

        # 🛡 ADMIN
        if is_admin:
            await interaction.response.defer()

            await Database.execute(
                "UPDATE tickets SET status = 'closed' WHERE channel_id = %s",
                (interaction.channel.id,)
            )

            await send_ticket_log(
                guild=guild,
                title="🔒 Ticket Closed (Admin)",
                description=(
                    f"🎫 **{interaction.channel.name}**\n"
                    f"🛡 Закрыт администратором: {interaction.user.mention}"
                ),
                color=discord.Color.red()
            )

            embed = discord.Embed(
                title="🔒 Ticket Closed",
                description="Тикет закрыт администратором.",
                color=discord.Color.red()
            )

            await interaction.channel.send(
                embed=embed,
                view=TicketAdminClosedView()
            )
            return

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

        await interaction.followup.send(
            "✅ Ticket claimed.",
            ephemeral=True,
            delete_after=5
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
        await interaction.response.defer(ephemeral=True)

        ticket = await get_ticket(interaction.channel.id)
        if not ticket:
            return

        await Database.execute(
            "UPDATE tickets SET status = 'closed' WHERE channel_id = %s",
            (interaction.channel.id,)
        )

        await send_ticket_log(
            guild=interaction.guild,
            title="🔒 Ticket Closed (User)",
            description=(
                f"🎫 **{interaction.channel.name}**\n"
                f"👤 Закрыт пользователем: {interaction.user.mention}"
            ),
            color=discord.Color.red()
        )

        await interaction.channel.delete(
            reason="Ticket closed by owner"
        )

class TicketAdminClosedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def lock(self, interaction: discord.Interaction):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(
        label="Transcript",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_admin_transcript"  
    )
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        from config import TRANSCRIPT_PUBLIC_URL
        filename, _ = await generate_transcript(interaction.channel)
        url = f"{TRANSCRIPT_PUBLIC_URL}/transcripts/{filename}"

        await Database.execute(
        "UPDATE tickets SET transcript_created = 1 WHERE channel_id = %s",
        (interaction.channel.id,)
    )

        embed = discord.Embed(
            title="📄 Ticket Transcript",
            description=f"🎫 **{interaction.channel.name}**",
            color=discord.Color.blurple()
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Transcript", style=discord.ButtonStyle.link, url=url))

        log = interaction.guild.get_channel(int(os.getenv("TICKET_LOG_CHANNEL_ID")))
        if log:
            await log.send(embed=embed, view=view)

    @discord.ui.button(
        label="Open",
        style=discord.ButtonStyle.success,
        custom_id="ticket_admin_open"          
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        ticket = await get_ticket(interaction.channel.id)
        if not ticket:
            return

        guild = interaction.guild
        user = guild.get_member(ticket["user_id"])
        admin_role = guild.get_role(TICKET_ADMIN_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        await interaction.channel.edit(overwrites=overwrites)

    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_admin_delete"        
    )
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        ticket = await get_ticket(interaction.channel.id)
        if not ticket:
            return

    # ❌ ТРАНСКРИПТА НЕТ
        if not ticket["transcript_created"]:
            await interaction.followup.send(
                "⚠️ **Transcript не был создан!**\n"
                "Вы уверены, что хотите удалить тикет без сохранения истории?",
                view=DeleteConfirmView(),
                ephemeral=True
            )
            return

    # ✅ ТРАНСКРИПТ ЕСТЬ — удаляем сразу
        interaction.client.loop.create_task(
            delete_ticket_channel(
                interaction.channel,
                interaction.guild,
                interaction.user
        )
    )

class DeleteConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(
        label="Confirm Delete",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_confirm_delete"
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.defer()

        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user

        # 🔥 удаление запускаем в фоне
        interaction.client.loop.create_task(
            delete_ticket_channel(channel, guild, user)
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

    await interaction.followup.send(
        f"✅ Тикет создан: {channel.mention}",
        ephemeral=True,
        delete_after=5
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

    @app_commands.command(
        name="ticket-panel",
        description="Создать панель тикетов"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):

        # 🔵 ОСНОВНАЯ ИНФОРМАЦИЯ
        embed_main = discord.Embed(
            title="🎫 Создание тикета",
            description=(
                "Выберите подходящую категорию для обращения \n\n"

                "🔹 **Заявление о разбане**\n"
                "Если ваш игровой аккаунт был заблокирован.\n\n"

                "🔹 **Жалоба на игрока**\n"
                "Если игрок нарушил правила проекта.\n\n"

                "🔹 **Жалоба на администратора**\n"
                "Только при серьёзных нарушениях со стороны администрации.\n\n"

                "🔹 **Техническая помощь**\n"
                "Баги, ошибки, проблемы с сервером или игрой."
            ),
            color=discord.Color.blurple()
        )

        embed_main.set_footer(
            text="Выбирайте категорию внимательно — неверный выбор замедлит рассмотрение"
        )

        # 🟠 ПРЕДУПРЕЖДЕНИЕ
        embed_warning = discord.Embed(
            title="⚠️ Важно перед созданием тикета",
            description=(
                "• Указывайте **достоверную и полную информацию**\n"
                "• Прикладывайте доказательства, если они имеются\n"
                "• Не создавайте несколько тикетов по одному вопросу\n\n"
                "⏳ Все обращения рассматриваются **в порядке очереди**"
            ),
            color=discord.Color.orange()
        )

        # 🔴 ОТВЕТСТВЕННОСТЬ
        embed_rules = discord.Embed(
            title="🚫 Ответственность",
            description=(
                "Следующие действия **строго запрещены**:\n\n"
                "• Ложная информация\n"
                "• Попытка ввести администрацию в заблуждение\n"
                "• Флуд / спам тикетами\n\n"
                "**Наказание может включать:**\n"
                "— Закрытие тикета без ответа\n"
                "— Временную или постоянную блокировку аккаунта"
            ),
            color=discord.Color.red()
        )

        # 📤 ОТПРАВКА
        await interaction.channel.send(embed=embed_main)
        await interaction.channel.send(embed=embed_warning)
        await interaction.channel.send(
            embed=embed_rules,
            view=TicketCreateView()  # ⚠️ кнопки ТОЛЬКО здесь
        )

        await interaction.response.send_message(
            "✅ Панель тикетов успешно создана.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Tickets(bot))

    # 🔥 ОБЯЗАТЕЛЬНО
    bot.add_view(PersistentTicketView())