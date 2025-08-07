import discord
from discord.ext import commands
import argparse
import asyncio
import requests
from datetime import datetime

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def get_token_price(): #I'll have to fix this, it's dogshit
    try:
        r = requests.get('https://wowauction.us/classic/token')
        token_price = r.text.split('''<div class="sm:w-full md: w-1/2 text-amber-400 flex flex-row items-center">
      <b>Current:</b>&nbsp;''')[1].split('&nbsp;')[0].replace(",","")
        return int(token_price)
    except Exception as e:
        log(f"Error fetching token price: {e}")
        return None

def parse_args():
    parser = argparse.ArgumentParser(description="WoW Token Price Discord Bot")
    parser.add_argument("-t", "--token", required=True, help="Discord bot token")
    parser.add_argument("-c", "--channel", required=True, type=int, help="Channel ID to send updates to")
    return parser.parse_args()


class TokenBot(commands.Bot):
    def __init__(self, channel_id, **kwargs):
        super().__init__(**kwargs)
        self.channel_id = channel_id
        self.last_price = None

    async def setup_hook(self):
        self.tree.add_command(token_price_slash)
        await self.tree.sync()
        self.bg_task = asyncio.create_task(self.monitor_price())

    async def on_ready(self):
        log(f"✅ Logged in as {self.user} (ID: {self.user.id})")

    async def monitor_price(self):
        await self.wait_until_ready()
        channel = self.get_channel(self.channel_id)

        if channel is None:
            log(f"❌ Could not find channel with ID {self.channel_id}")
            return

        log("📡 Background task started for token price monitoring.")

        while not self.is_closed():
            await asyncio.sleep(300)  # 5 minutes
            current_price = get_token_price()
            log(f'Fetched current price: {current_price}')

            if current_price is None:
                log("⚠️ Failed to fetch token price.")
                continue

            if self.last_price:
                change = abs(current_price - self.last_price) / self.last_price
                if change >= 0.02:
                    direction = "increased" if current_price > self.last_price else "decreased"
                    message = (
                        f"📢 WoW Token price has {direction} by {change:.2%}!\n"
                        f"New price: {current_price}g"
                    )
                    await channel.send(message)
                    self.last_price = current_price
                    log(f'last_price changed to {current_price}')
            else:
                self.last_price = current_price


# 🎯 Slash Command (/token)
@discord.app_commands.command(name="token", description="Check the current WoW Token price")
async def token_price_slash(interaction: discord.Interaction):
    price = get_token_price()
    if price:
        await interaction.response.send_message(f"💰 Current WoW Token price: {price}g", ephemeral=False)
        log(f"{interaction.user} used /token")
    else:
        await interaction.response.send_message("❌ Failed to fetch WoW Token price.", ephemeral=True)


# 💬 Prefix Command (!token)
@commands.command(name="token", help="Check the current WoW Token price")
async def token_price_prefix(ctx):
    price = get_token_price()
    if price:
        await ctx.send(f"💰 Current WoW Token price: {price}g")
        log(f"{ctx.author} used !token")
    else:
        await ctx.send("❌ Failed to fetch WoW Token price.")


def main():
    args = parse_args()

    intents = discord.Intents.default()
    intents.message_content = True

    bot = TokenBot(channel_id=args.channel, command_prefix="!", intents=intents)

    # Register prefix command manually
    bot.add_command(token_price_prefix)

    bot.run(args.token)


if __name__ == "__main__":
    main()

