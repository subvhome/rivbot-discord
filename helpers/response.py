import discord
from core.logging_setup import logger
from io import StringIO

async def send_response(ctx, content):
    content_str = str(content)
    logger.info(f"Sending response to {ctx.author}: {content_str[:50]}...")
    if len(content_str) <= 2000:
        await ctx.send(content_str)
    else:
        file_content = StringIO(content_str)
        file = discord.File(file_content, filename="output.txt")
        await ctx.send("Output too long, here’s a file:", file=file)
        file_content.close()
    logger.info(f"Response sent to {ctx.author}")
