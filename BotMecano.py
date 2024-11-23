# -*- coding: utf-8 -*-
"""
Created on Fri Nov 22 17:21:04 2024

@author: boris
"""

import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import pytz
import nest_asyncio
from flask import Flask
from threading import Thread

nest_asyncio.apply()

app = Flask('')


@app.route('/')
def home():
    return "Le bot fonctionne !"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    thread = Thread(target=run)
    thread.start()


# Configurez votre bot
intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.guild_reactions = True
intents.message_content = True
intents.members = True  # Permet d'accéder à la liste des membres
intents.presences = True  # Permet d'accéder au statut de présence (facultatif)

bot = commands.Bot(command_prefix="!", intents=intents)

# Variables pour le minuteur et suivi des utilisateurs
reaction_message_id = 1266769325277319208  # L'ID du message à surveiller
tracked_users = {}  # Dictionnaire pour suivre les temps (user_id : start_time)
cooldowns = {
}  # Dictionnaire pour gérer les cooldowns (user_id : last_action_time)
role_name = "En Service"  # Nom du rôle à donner
log_channel_id = 1309974199124885504  # Remplacez par l'ID du salon où afficher les logs

# Fuseau horaire pour la France
french_timezone = pytz.timezone("Europe/Paris")


def format_time_in_french_timezone(dt):
    """Formate un datetime pour qu'il soit en heure française."""
    return dt.astimezone(french_timezone).strftime("%H:%M:%S")


def is_on_cooldown(user_id):
    """Vérifie si un utilisateur est en cooldown."""
    now = datetime.now()
    if user_id in cooldowns:
        last_action_time = cooldowns[user_id]
        if now - last_action_time < timedelta(
                seconds=10):  # Cooldown de 10 secondes
            return True
    cooldowns[user_id] = now  # Met à jour l'heure de la dernière action
    return False


@bot.event
async def on_ready():
    print(f"{bot.user} est prêt et connecté !")


@bot.command()
async def setup(ctx):
    """Commande pour configurer le message de réaction."""
    global reaction_message_id
    embed = discord.Embed(
        title="Prise de Service : ",
        description="Ajoutez une réaction pour démarrer votre service !\n"
        "Retirez la réaction pour arrêter votre service !",
        color=discord.Color.blue(),
    )
    message = await ctx.send(embed=embed)
    reaction_message_id = message.id
    await message.add_reaction("⏱️")  # Emoji utilisé pour la réaction
    await ctx.send(f"Message configuré avec l'ID {reaction_message_id}.")


@bot.event
async def on_raw_reaction_add(payload):
    """Démarre le minuteur et donne un rôle."""
    if payload.message_id == reaction_message_id and str(
            payload.emoji) == "⏱️":
        if is_on_cooldown(payload.user_id):
            print(f"Ajout ignoré pour {payload.user_id} (cooldown actif).")
            return

        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = discord.utils.get(guild.roles, name=role_name)

        if not role:
            # Crée le rôle si inexistant
            role = await guild.create_role(name=role_name,
                                           color=discord.Color.green())

        if role not in member.roles:
            await member.add_roles(role)
            tracked_users[payload.user_id] = datetime.now()
            print(f"Prise de Service pour : {member.name}.")


@bot.event
async def on_raw_reaction_remove(payload):
    """Arrête le minuteur et affiche le temps écoulé."""
    if payload.message_id == reaction_message_id and str(
            payload.emoji) == "⏱️":
        if is_on_cooldown(payload.user_id):
            print(
                f"Suppression ignorée pour {payload.user_id} (cooldown actif)."
            )
            return

        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = discord.utils.get(guild.roles, name=role_name)
        log_channel = bot.get_channel(log_channel_id)

        if payload.user_id in tracked_users:
            start_time = tracked_users.pop(payload.user_id)
            end_time = datetime.now()
            elapsed_time = end_time - start_time

            # Convertir les heures en heure française
            formatted_start_time = format_time_in_french_timezone(start_time)
            formatted_end_time = format_time_in_french_timezone(end_time)

            # Retirer le rôle
            if role in member.roles:
                await member.remove_roles(role)

            # Envoyer le message dans le salon prévu
            if log_channel:
                await log_channel.send(
                    f"{member.mention} a terminé son service.\n"
                    f"**Heure de début :** {formatted_start_time}\n"
                    f"**Heure de fin :** {formatted_end_time}\n"
                    f"**Temps écoulé :** {elapsed_time}.")
            print(
                f"Service terminé pour {member.name}. Temps écoulé : {elapsed_time}. "
                f"Début : {formatted_start_time}, Fin : {formatted_end_time}.")


# Démarrez le bot


async def main():
    async with bot:
        await bot.start(
            "A METTRE"
        )


keep_alive()
asyncio.run(main())

