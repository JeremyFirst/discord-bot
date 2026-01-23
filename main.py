import asyncio
import discord
from discord.ext import commands

from config import DISCORD_TOKEN


INTENTS = discord.Intents.default()
INTENTS.members = True  # пригодится дальше


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=INTENTS
        )

    async def setup_hook(self):
        # Загружаем cogs
        await self.load_extension("cogs.tickets")

        # Синхронизация slash-команд
        await self.tree.sync()
        print("✅ Slash-команды синхронизированы")

    async def on_ready(self):
        print(f"🤖 Бот запущен как {self.user}")


async def main():
    bot = Bot()
    await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
