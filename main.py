import discord
from discord import app_commands
import aiohttp
import json
import time

with open("config.json", "r") as f:
    config = json.load(f)

TOKEN = config["Token"]
BYPASS_URL = config["Bypass-Url"]
BYPASS_RESULT = config["Bypass-Result"]
COLOR_SUCCESS = discord.Color(int(config["COLOR_SUCCESS"], 16))
COLOR_ERROR = discord.Color(int(config["COLOR_ERROR"], 16))
SUPPORT_URL = config["Support"]

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


class LoadingView(discord.ui.LayoutView):
    def __init__(self, url: str):
        super().__init__()

        container = discord.ui.Container()

        container.add_item(discord.ui.TextDisplay(
            "## <a:loading:1473521981428334663> Processing Request"
        ))

        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            f"**Link:** {url}"
        ))

        container.add_item(discord.ui.TextDisplay(
            "Please wait..."
        ))

        self.add_item(container)


class BypassSuccessView(discord.ui.LayoutView):
    def __init__(self, result: str, duration: str, user: str, invite_url: str):
        super().__init__()

        container = discord.ui.Container(accent_colour=COLOR_SUCCESS)

        container.add_item(discord.ui.TextDisplay(
            "**Bypass Success** <a:check:1473521968278933524>"
        ))

        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            f"**Mobile Version**\n`{result}`"
        ))

        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            f"**PC Version**\n```{result}```"
        ))

        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(
            f"-# Processed in {duration}s • Requested by {user}"
        ))

        container.add_item(discord.ui.ActionRow(
            discord.ui.Button(
                label="Invite",
                style=discord.ButtonStyle.link,
                url=invite_url,
                emoji="🔗"
            ),
            discord.ui.Button(
                label="Support",
                style=discord.ButtonStyle.link,
                url=SUPPORT_URL,
                emoji="💬"
            )
        ))

        self.add_item(container)


class ErrorView(discord.ui.LayoutView):
    def __init__(self, invite_url: str):
        super().__init__()

        container = discord.ui.Container(accent_colour=COLOR_ERROR)

        container.add_item(discord.ui.TextDisplay(
            "❌ Couldn't bypass the link. API might be offline or the link is unsupported. Please try again later."
        ))

        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.ActionRow(
            discord.ui.Button(
                label="Invite",
                style=discord.ButtonStyle.link,
                url=invite_url,
                emoji="🔗"
            ),
            discord.ui.Button(
                label="Support",
                style=discord.ButtonStyle.link,
                url=SUPPORT_URL,
                emoji="💬"
            )
        ))

        self.add_item(container)


class DMErrorView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__()

        container = discord.ui.Container(accent_colour=COLOR_ERROR)

        container.add_item(discord.ui.TextDisplay(
            "## ❌ Server Only\nCommands can only be used in a server.\n`/bypass <url>`"
        ))

        self.add_item(container)


class CooldownView(discord.ui.LayoutView):
    def __init__(self, user_id: int, retry_after: float, username: str):
        super().__init__()

        container = discord.ui.Container(accent_colour=COLOR_ERROR)

        container.add_item(discord.ui.TextDisplay(
            f"### ⏱ Cooldown\n"
            f"<@{user_id}> Whoa, slow down there! "
            f"You can run the command again in **{retry_after:.2f}** seconds.\n"
            f"-# Requested by {username}"
        ))

        self.add_item(container)


@tree.command(name="bypass", description="Bypass a URL")
@app_commands.describe(url="The URL you want to bypass")
@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
async def bypass(interaction: discord.Interaction, url: str):
    if interaction.guild is None:
        await interaction.response.send_message(view=DMErrorView(), ephemeral=True)
        return

    await interaction.response.send_message(view=LoadingView(url=url))

    start_time = time.time()
    user = interaction.user.name
    invite_url = (
        f"https://discord.com/oauth2/authorize"
        f"?client_id={interaction.application_id}"
        f"&permissions=8&scope=bot+applications.commands"
    )

    try:
        api_url = BYPASS_URL.replace("{url}", url)
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                data = await resp.json(content_type=None)
                result = data.get(BYPASS_RESULT)

        end_time = time.time()
        duration = f"{end_time - start_time:.3f}"

        if not result:
            raise ValueError("API did not return a valid result.")

        await interaction.edit_original_response(
            view=BypassSuccessView(result=result, duration=duration, user=user, invite_url=invite_url)
        )

    except Exception:
        await interaction.edit_original_response(
            view=ErrorView(invite_url=invite_url)
        )


@bypass.error
async def bypass_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        view = CooldownView(
            user_id=interaction.user.id,
            retry_after=error.retry_after,
            username=interaction.user.name
        )
        await interaction.response.send_message(view=view, ephemeral=True)


@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user} | Slash commands synced.")


client.run(TOKEN)
