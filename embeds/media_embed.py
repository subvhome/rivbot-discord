import discord

def create_media_embed(query, title, year, rating, vote_count, description, imdb_id, tmdb_id, poster, riven_state, recommended_titles=None):
    embed = discord.Embed(title=f"🔎 Results for '{query}'")

    # Create IMDb link if available, otherwise use plain title
    if imdb_id != 'N/A':
        title_display = f"[{title} ({year})](https://www.imdb.com/title/{imdb_id}/)"
    else:
        title_display = f"{title} ({year})"

    media_card = (
        f"**{title_display}**\n"
        f"⭐ Rating: {rating}/10 ({vote_count} votes)\n"
        f"📝 {description}\n"
        f"🔄 Riven: {riven_state}\n\n"
    )

    if recommended_titles:
        media_card += "Reaction at the bottom to select a title:\n"
        media_card += "**Recommended Titles:**\n"
        media_card += "\n".join(recommended_titles)

    embed.description = media_card.strip()
    embed.set_thumbnail(url=poster)
    embed.set_image(url=poster)
    return embed
