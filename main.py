import os
import json
import threading
import logging
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
CONFIG_FILE = "config.json"

# Load configuration from file or initialize default config
def load_config():
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"source_channel": None, "target_channel": None}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

config = load_config()

# Flask app for health check
app = Flask(__name__)

@app.route("/health")
def health_check():
    return "OK", 200

# Retrieve environment variables needed for Pyrogram
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

# Initialize Pyrogram client in bot mode
bot = Client("forward_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Command: /setsource <channel_identifier>
@bot.on_message(filters.command("setsource") & filters.private)
def set_source(client: Client, message: Message):
    if len(message.command) < 2:
        message.reply_text("Usage: /setsource <channel_username_or_id>")
        return
    source = message.command[1]
    config["source_channel"] = source
    save_config(config)
    message.reply_text(f"Source channel set to: {source}")

# Command: /setforward <channel_identifier>
@bot.on_message(filters.command("setforward") & filters.private)
def set_forward(client: Client, message: Message):
    if len(message.command) < 2:
        message.reply_text("Usage: /setforward <channel_username_or_id>")
        return
    target = message.command[1]
    config["target_channel"] = target
    save_config(config)
    message.reply_text(f"Forward channel set to: {target}")

# Command: /status - show current configuration
@bot.on_message(filters.command("status") & filters.private)
def status(client: Client, message: Message):
    src = config.get("source_channel") or "Not set"
    tgt = config.get("target_channel") or "Not set"
    message.reply_text(f"Current configuration:\nSource: {src}\nTarget: {tgt}")

# Function to perform bulk forwarding
def bulk_forward(client: Client, source, target, reply_to: Message):
    messages = []
    try:
        # Fetch all messages from source channel (get_history returns newest first)
        for msg in client.get_history(source):
            messages.append(msg)
    except Exception as e:
        reply_to.reply_text(f"Error fetching history from {source}: {e}")
        return

    # Reverse to forward from oldest to newest
    messages.sort(key=lambda m: m.message_id)
    total = len(messages)
    forwarded = 0

    reply_to.reply_text(f"Starting to forward {total} messages from {source} to {target}.")

    for msg in messages:
        try:
            client.forward_messages(
                chat_id=target,
                from_chat_id=source,
                message_ids=msg.message_id
            )
            forwarded += 1
        except Exception as e:
            logging.error(f"Error forwarding message {msg.message_id}: {e}")

    reply_to.reply_text(f"Forwarding complete. Successfully forwarded {forwarded}/{total} messages.")

# Command: /forward - trigger bulk forwarding
@bot.on_message(filters.command("forward") & filters.private)
def forward_command(client: Client, message: Message):
    source = config.get("source_channel")
    target = config.get("target_channel")
    if not source or not target:
        message.reply_text("Both source and target channels must be set. Use /setsource and /setforward commands.")
        return
    # Run the bulk forwarding in a separate thread so the bot remains responsive
    threading.Thread(target=bulk_forward, args=(client, source, target, message), daemon=True).start()

def start_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # Start Flask health-check server in a separate thread.
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    # Start the Pyrogram bot.
    logging.info("Bot is starting...")
    bot.run()
