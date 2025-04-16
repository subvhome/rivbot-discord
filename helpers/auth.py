async def check_authorization(interaction, initiator_id):
    if interaction.user.id != initiator_id:
        await interaction.response.send_message("Not your button!", ephemeral=True)
        return False
    return True
