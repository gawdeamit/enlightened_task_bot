import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io

load_dotenv()
bot_token = os.getenv('DISCORD_BOT_TOKEN')
if bot_token is None:
    raise ValueError("Bot token not found! Please check your .env file.")

intents = discord.Intents.default()
intents.message_content = True

class GoalBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.synced = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await self.tree.sync()
            self.synced = True
        print(f'Logged in as {self.user.name}')
        self.bg_task = self.loop.create_task(self.reminder_task())

    async def reminder_task(self):
        while not self.is_closed():
            now = datetime.now()
            for user_id, goals in user_goals.items():
                for goal in goals:
                    if not goal['completed'] and 'reminder' in goal and now >= goal['reminder']:
                        user = await self.fetch_user(int(user_id))
                        await user.send(f"⏰ Reminder: It's time to work on your goal: {goal['task']}")
                        goal['reminder'] = now + timedelta(hours=1)  # Set next reminder
            await asyncio.sleep(60)  # Check every minute

bot = GoalBot()

DATA_FILE = 'user_goals.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

user_goals = load_data()

@bot.tree.command(name="add_goal", description="Add a new goal with a duration in minutes.")
@app_commands.describe(duration="Duration of the task in minutes", task="Description of the task")
async def add_goal(interaction: discord.Interaction, duration: int, task: str):
    user_id = str(interaction.user.id)
    if user_id not in user_goals:
        user_goals[user_id] = []
    user_goals[user_id].append({
        'task': task,
        'duration': duration,
        'completed': False,
        'created_at': datetime.now().isoformat(),
        'reminder': (datetime.now() + timedelta(minutes=30)).isoformat()
    })
    save_data(user_goals)
    embed = discord.Embed(title="Goal Added", description=f"🎯 {task}", color=0x00ff00)
    embed.add_field(name="Duration", value=f"⏱️ {duration} minutes")
    embed.set_footer(text="You've got this! 💪")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="view_goals", description="View current goals.")
async def view_goals(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in user_goals or not user_goals[user_id]:
        await interaction.response.send_message("You haven't set any goals yet. Use /add_goal to get started!")
        return

    embed = discord.Embed(title="Your Goals", color=0x00ff00)
    for idx, goal in enumerate(user_goals[user_id], start=1):
        status = "✅" if goal['completed'] else "⏳"
        embed.add_field(
            name=f"Goal {idx}: {goal['task']}",
            value=f"{status} Duration: {goal['duration']} mins",
            inline=False
        )
    embed.set_footer(text="Keep pushing forward! 🚀")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="complete_goal", description="Mark a goal as completed by its number.")
@app_commands.describe(task_number="The number of the task to mark as completed.")
async def complete_goal(interaction: discord.Interaction, task_number: int):
    user_id = str(interaction.user.id)
    if user_id in user_goals and 0 < task_number <= len(user_goals[user_id]):
        goal = user_goals[user_id][task_number - 1]
        goal['completed'] = True
        goal['completed_at'] = datetime.now().isoformat()
        save_data(user_goals)
        embed = discord.Embed(title="Goal Completed!", description=f"🎉 {goal['task']}", color=0xffff00)
        embed.set_footer(text="Great job! Keep up the momentum! 🌟")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Invalid task number.")

@bot.tree.command(name="progress", description="View your goal progress with a visual chart.")
async def progress(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in user_goals or not user_goals[user_id]:
        await interaction.response.send_message("You haven't set any goals yet. Use /add_goal to get started!")
        return

    completed = sum(1 for goal in user_goals[user_id] if goal['completed'])
    total = len(user_goals[user_id])

    plt.figure(figsize=(8, 6))
    plt.pie([completed, total - completed], labels=['Completed', 'Remaining'], autopct='%1.1f%%', colors=['#00ff00', '#ff0000'])
    plt.title('Your Goal Progress')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    file = discord.File(buf, filename="progress.png")
    embed = discord.Embed(title="Goal Progress", color=0x00ff00)
    embed.set_image(url="attachment://progress.png")
    embed.add_field(name="Completed", value=f"{completed}/{total} goals")
    embed.set_footer(text="Every step counts! 👣")

    await interaction.response.send_message(embed=embed, file=file)

@bot.tree.command(name="streak", description="View your current streak of completing goals.")
async def streak(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in user_goals or not user_goals[user_id]:
        await interaction.response.send_message("You haven't set any goals yet. Use /add_goal to get started!")
        return

    completed_goals = sorted([goal for goal in user_goals[user_id] if goal['completed']],
                             key=lambda x: datetime.fromisoformat(x['completed_at']))

    if not completed_goals:
        await interaction.response.send_message("You haven't completed any goals yet. Keep pushing!")
        return

    streak = 1
    max_streak = 1
    last_date = datetime.fromisoformat(completed_goals[0]['completed_at']).date()

    for goal in completed_goals[1:]:
        current_date = datetime.fromisoformat(goal['completed_at']).date()
        if (current_date - last_date).days == 1:
            streak += 1
            max_streak = max(max_streak, streak)
        elif (current_date - last_date).days > 1:
            streak = 1
        last_date = current_date

    embed = discord.Embed(title="Goal Completion Streak", color=0xffff00)
    embed.add_field(name="Current Streak", value=f"🔥 {streak} day{'s' if streak != 1 else ''}")
    embed.add_field(name="Longest Streak", value=f"🏆 {max_streak} day{'s' if max_streak != 1 else ''}")
    embed.set_footer(text="Consistency is key! 🗝️")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clear_completed", description="Clear all completed goals.")
async def clear_completed(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in user_goals:
        await interaction.response.send_message("You don't have any goals set.")
        return

    initial_count = len(user_goals[user_id])
    user_goals[user_id] = [goal for goal in user_goals[user_id] if not goal['completed']]
    cleared_count = initial_count - len(user_goals[user_id])
    save_data(user_goals)

    embed = discord.Embed(title="Completed Goals Cleared", color=0x00ff00)
    embed.add_field(name="Cleared", value=f"🧹 {cleared_count} goal{'s' if cleared_count != 1 else ''}")
    embed.set_footer(text="Ready for new challenges! 🚀")
    await interaction.response.send_message(embed=embed)

bot.run(bot_token)
