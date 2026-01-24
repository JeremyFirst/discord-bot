import asyncio
import discord
from discord.ext import commands

from config import DISCORD_TOKEN
from core.database import Database


INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True


async def main():
    bot = commands.Bot(
        command_prefix="!",
        intents=INTENTS
    )

    @bot.event
    async def on_ready():
        print(f"🤖 Бот запущен как {bot.user}")

    async def setup_hook():
        await Database.connect()
        print("✅ MySQL connected")


        await bot.load_extension("cogs.tickets")

        from cogs.tickets import TicketCreateView, PersistentTicketView
        bot.add_view(TicketCreateView())
        bot.add_view(PersistentTicketView())

        await bot.tree.sync()
        print("✅ Slash-команды синхронизированы")


    bot.setup_hook = setup_hook

    try:
        await bot.start(DISCORD_TOKEN)
    finally:
        await Database.close()


if __name__ == "__main__":
    asyncio.run(main())
