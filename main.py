#!/usr/bin/python3
# -*- coding: latin-1 -*-
import os
import socket
import ros_api
import logging
from py_code.classes import LogLine
import threading
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters
from telegram.ext import Application as TelegramApplication

# Environment variables
TG_BOTTOKEN = ""
TG_CHATID = ""
MKT_API_ADDRESS = ""
MKT_API_PORT = 8729
MKT_API_USER = ""
MKT_API_PASS = ""
MKT_LOGS_PORT = 10514

# Project variables
TG_APP = None
shutdown_flag = threading.Event()  # Create a shutdown flag

def configure_logging():
    """
    Configure logging settings.
    """

    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s', 
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.DEBUG)
    logging.getLogger("httpx").setLevel(logging.WARNING)

def load_env_variables():
    """
    Load environment variables from .env file.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Load environment variables
    global TG_BOTTOKEN, TG_CHATID, MKT_API_ADDRESS, MKT_API_PORT, MKT_API_USER, MKT_API_PASS, MKT_LOGS_PORT
    TG_BOTTOKEN = os.getenv("TG_BOTTOKEN")
    TG_CHATID = os.getenv("TG_CHATID")
    MKT_API_ADDRESS = os.getenv("MKT_API_ADDRESS")
    MKT_API_PORT = int(os.getenv("MKT_API_PORT", 8729))
    MKT_API_USER = os.getenv("MKT_API_USER")
    MKT_API_PASS = os.getenv("MKT_API_PASS")
    MKT_LOGS_PORT = int(os.getenv("MKT_LOGS_PORT", 10514))

    # Validate environment variables
    if not TG_BOTTOKEN:
        raise ValueError("TG_BOTTOKEN is not set in the environment variables.")
    if not TG_CHATID:
        raise ValueError("TG_CHATID is not set in the environment variables.")
    if not MKT_API_ADDRESS:
        raise ValueError("MKT_API_ADDRESS is not set in the environment variables.")
    if not MKT_API_PORT:
        logging.warning("MKT_API_PORT is not set in the environment variables, defaulting to 8728.")
    if not MKT_API_USER:
        raise ValueError("MKT_API_USER is not set in the environment variables.")
    if not MKT_API_PASS:
        raise ValueError("MKT_API_PASS is not set in the environment variables.")
    if not MKT_LOGS_PORT:
        logging.warning("MKT_LOGS_PORT is not set in the environment variables, defaulting to 10514.")

async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    """
    if update.message.chat.id != int(TG_CHATID):
        logging.warning("Unauthorized access from user ID: %d", update.message.chat.id)
        return

    # Send a welcome message
    await update.message.reply_text("Welcome to the MikroTik Logs Bot! Use /help to see available commands.")

async def tg_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /help command.
    """
    if update.message.chat.id != int(TG_CHATID):
        logging.warning("Unauthorized access from user ID: %d", update.message.chat.id)
        return

    # Send help message
    help_text = (
        "Available commands:\n"
        "/start - Welcome message\n"
        "/help - Show this help message\n"
        "/status - Get the status of the MikroTik device\n"
    )
    await update.message.reply_text(help_text)

async def tg_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /status command.
    """

    global TG_APP, MKT_API_ADDRESS, MKT_API_PORT, MKT_API_USER, MKT_API_PASS

    if update.message.chat.id != int(TG_CHATID):
        logging.warning("Unauthorized access from user ID: %d", update.message.chat.id)
        return
    else:
        logging.info("User %d requested %s", update.message.chat.id, update.message.text)

    # Retrieve the status of the Mikrotik device
    try:
        logging.info("Connecting to MikroTik API...")
        router = ros_api.Api(MKT_API_ADDRESS, user=MKT_API_USER, password=MKT_API_PASS, port=MKT_API_PORT, use_ssl=True, timeout=1)
        response = router.talk('/system/health/print')
        if response:
            # Process the response and send it to the Telegram chat
            status_message = f"Status: {response}"
            await update.message.reply_text(status_message)
        else:
            await update.message.reply_text("No response from MikroTik API.")
    except Exception as e:
        logging.error(f"Error retrieving status: {e}")
        await update.message.reply_text(f"Error retrieving status: {e}")

def build_telegram_app():
    """
    Build the Telegram application.
    """

    global TG_APP
    logging.info("Building Telegram application...")
    TG_APP = ApplicationBuilder().token(TG_BOTTOKEN).build()
    
    # Add handlers for commands
    logging.info("Adding command handlers...")
    TG_APP.add_handler(CommandHandler("start", tg_start))
    TG_APP.add_handler(CommandHandler("help", tg_help))
    TG_APP.add_handler(CommandHandler("status", tg_status))

def decode_log_line(log_line: str) -> LogLine:
    """
    Decode a log line into a LogLine object.
    """
    try:
        return LogLine(log_line)
    except ValueError as e:
        logging.error(f"Failed to decode log line: {e}")
        return None

def start_logs_server():
    host = "0.0.0.0"      # Listen on all available interfaces
    port = MKT_LOGS_PORT  # Port to listen on

    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        try:
            server_socket.bind((host, port))
            logging.info(f"UDP logs server listening on port {port}...")

            while not shutdown_flag.is_set():
                # Receive data from client
                log_content, log_address = server_socket.recvfrom(1024)  # Buffer size is 1024 bytes
                try:
                    # Decode the log content
                    log_line = decode_log_line(log_content.decode('utf-8'))
                    logging.debug(f"Parsed log line: {log_line}")
                except UnicodeDecodeError as e:
                    logging.error(f"Failed to decode message from {log_address}: {e}")

            logging.info("Logs server stopped.")
        except Exception as e:
            logging.error(f"Error in logs server: {e}")
            exit(1)

def main() -> None:
    """
    Main function to run the application.
    """

    global TG_APP

    # Load environment variables
    load_env_variables()

    # Build the Telegram application
    build_telegram_app()

    # Start the logs server
    logs_thread = threading.Thread(target=start_logs_server, daemon=True)
    logs_thread.start()

    # Start the Telegram bot
    try:
        logging.info("Starting Telegram bot...")
        TG_APP.run_polling()
    except KeyboardInterrupt:
        logging.info("Stopping Telegram bot...")
        shutdown_flag.set()
        logs_thread.join()
        TG_APP.stop()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        logging.info("Exiting...")


if __name__ == "__main__":
    configure_logging()

    try:
        logging.info("Starting the application...")
        main()
    except KeyboardInterrupt:
        logging.info("Stopping application...")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        logging.info("Exiting...")