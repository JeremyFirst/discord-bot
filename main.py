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
        print(f"🤖 Logged in as {bot.user}")

    async def setup_hook():
        await Database.connect()

        await bot.load_extension("cogs.tickets")

        from cogs.tickets import TicketCreateView
        bot.add_view(TicketCreateView())

        await bot.tree.sync()

    bot.setup_hook = setup_hook

    try:
        await bot.start(DISCORD_TOKEN)
    finally:
        await Database.close()


if __name__ == "__main__":
    asyncio.run(main())
