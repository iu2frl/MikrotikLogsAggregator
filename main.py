#!/usr/bin/python3
# -*- coding: latin-1 -*-
import os
import socket
import asyncio
import ros_api
import logging
from py_code.classes import LogLine
import threading
from dotenv import load_dotenv
from telegram import Update, Message
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
CFG_SEND_INFO = False
CFG_SEND_WARNING = True
CFG_SEND_ERROR = True
CFG_SEND_CRITICAL = True

# Project variables
TG_APP: TelegramApplication = None
shutdown_flag = threading.Event()  # Create a shutdown flag

### Logging configuration ###

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
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

### Load environment variables ###

def load_env_variables():
    """
    Load environment variables from .env file.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Load environment variables
    global TG_BOTTOKEN, TG_CHATID, MKT_API_ADDRESS
    global MKT_API_PORT, MKT_API_USER, MKT_API_PASS, MKT_LOGS_PORT
    global CFG_SEND_ERROR, CFG_SEND_WARNING, CFG_SEND_INFO, CFG_SEND_CRITICAL
    
    TG_BOTTOKEN = os.getenv("TG_BOTTOKEN")
    TG_CHATID = os.getenv("TG_CHATID")
    MKT_API_ADDRESS = os.getenv("MKT_API_ADDRESS")
    MKT_API_PORT = int(os.getenv("MKT_API_PORT", 8729))
    MKT_API_USER = os.getenv("MKT_API_USER")
    MKT_API_PASS = os.getenv("MKT_API_PASS")
    MKT_LOGS_PORT = int(os.getenv("MKT_LOGS_PORT", 10514))
    CFG_SEND_ERROR = os.getenv("CFG_SEND_ERROR", "True").lower() == "true"
    CFG_SEND_WARNING = os.getenv("CFG_SEND_WARNING", "True").lower() == "true"
    CFG_SEND_INFO = os.getenv("CFG_SEND_INFO", "False").lower() == "true"
    CFG_SEND_CRITICAL = os.getenv("CFG_SEND_CRITICAL", "True").lower() == "true"

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

### Parsers from MikroTik to Telegram ###

def status_to_text(status: list[dict]) -> str:
    """
    Convert status list of dictionaries to a pretty Markdown message.
    """
    try:
        if not isinstance(status, list):
            raise ValueError("Status is not a list.")

        # Build the Markdown message
        markdown_message = "MikroTik Device Status\n\n"
        for item in status:
            name = item.get("name", "Unknown").capitalize()
            value = str(item.get("value", "N/A"))
            unit = item.get("type", "")
            markdown_message += f"- {name}: {value} {unit}\n"

        return markdown_message
    except Exception as e:
        logging.error(f"Failed to parse status message: {e}")
        return "Error processing status information."
    
def dict_list_to_text(dict_list: list[dict]) -> str:
    """
    Convert a generic list of dictionaries to a pretty Markdown message.
    """
    try:
        if not isinstance(dict_list, list):
            raise ValueError("Input is not a list of dictionaries.")

        # Build the Markdown message
        markdown_message = "MikroTik Device Information\n\n"
        for item in dict_list:
            for key, value in item.items():
                markdown_message += f"- {key.replace('-', ' ').capitalize()}: {value}\n"
            markdown_message += "\n"  # Add a blank line between items

        return markdown_message.strip()
    except Exception as e:
        logging.error(f"Failed to parse dictionary list: {e}")
        return "Error processing dictionary list."

def interface_to_text(interface: list[dict]) -> str:
    """
    Convert interface list of dictionaries to a pretty Markdown message.
    """
    try:
        if not isinstance(interface, list):
            raise ValueError("Interface is not a list.")

        # Build the Markdown message
        markdown_message = "MikroTik Interfaces\n\n"
        for item in interface:
            name = item.get("name", "Unknown").capitalize()
            type_ = item.get("type", "N/A")
            status = item.get("running", "N/A")
            markdown_message += f"- Interface: {name}\n-- Type: {type_}\n-- Status: {status}\n\n"

        return markdown_message
    except Exception as e:
        logging.error(f"Failed to parse interface message: {e}")
        return "Error processing interface information."

def dhcplease_to_text(dhcp_leases: list[dict]) -> str:
    """
    Convert DHCP leases list of dictionaries to a pretty Markdown message.
    """
    try:
        if not isinstance(dhcp_leases, list):
            raise ValueError("DHCP leases is not a list.")

        # Build the Markdown message
        markdown_message = "MikroTik DHCP Leases\n\n"
        for lease in dhcp_leases:
            address = lease.get("address", "Unknown")
            mac_address = lease.get("mac-address", "N/A")
            host_name = lease.get("host-name", "N/A")
            status = lease.get("status", "N/A")
            markdown_message += f"- Address: {address}\n-- MAC: {mac_address}\n-- Hostname: {host_name}\n-- Status: {status}\n\n"

        return markdown_message
    except Exception as e:
        logging.error(f"Failed to parse DHCP leases message: {e}")
        return "Error processing DHCP leases information."

def logs_to_text(logs: list[dict]) -> str:
    """
    Convert logs list of dictionaries to a pretty Markdown message.
    """
    try:
        if not isinstance(logs, list):
            raise ValueError("Logs is not a list.")

        # Build the Markdown message
        markdown_message = "Last 10 MikroTik Logs:\n\n"
        last_logs = logs[-10:]  # Get the last 10 logs
        for log in last_logs:
            time = log.get("time", "Unknown")
            message = log.get("message", "N/A")
            topics = log.get("topics", "N/A")
            markdown_message += f"- Time: {time}\n-- Topics: {topics}\n-- Message: {message}\n\n"

        return markdown_message
    except Exception as e:
        logging.error(f"Failed to parse logs message: {e}")
        return "Error processing logs information."

### Telegram Handlers ###

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

async def tg_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /health command.
    """
    await telegram_to_mikrotik(update.message, "/system/health/print", status_to_text)

async def tg_resource(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /resource command.
    """
    await telegram_to_mikrotik(update.message, "/system/resource/print", dict_list_to_text)

async def tg_interface(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /interface command.
    """
    await telegram_to_mikrotik(update.message, "/interface/print brief", interface_to_text)

async def tg_dhcplease(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /dhcplease command.
    """
    await telegram_to_mikrotik(update.message, "/ip/dhcp-server/lease/print", dhcplease_to_text)

async def tg_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /logs command.
    """
    await telegram_to_mikrotik(update.message, "/log/print", logs_to_text)

async def telegram_to_mikrotik(message: Message, command: str, parse_function: callable) -> None:
    """
    Send a command to the MikroTik device and parse the response.
    """
    global TG_APP, MKT_API_ADDRESS, MKT_API_PORT, MKT_API_USER, MKT_API_PASS

    if message.chat.id != int(TG_CHATID):
        logging.warning("Unauthorized access from user ID: %d", message.chat.id)
        return
    else:
        logging.info("User %d requested %s", message.chat.id, message.text)

    # Retrieve the status of the Mikrotik device
    try:
        logging.info("Connecting to MikroTik API...")
        router = ros_api.Api(MKT_API_ADDRESS, user=MKT_API_USER, password=MKT_API_PASS, port=MKT_API_PORT, use_ssl=True, timeout=1)
        response = router.talk(command)
        logging.debug(f"Response from MikroTik API: {response}")
        if response:
            # Process the response and send it to the Telegram chat
            reply_message = parse_function(response)
            await message.reply_text(reply_message)
        else:
            await message.reply_text("No response from MikroTik API.")
    except Exception as e:
        logging.error(f"Error retrieving status: {e}")
        await message.reply_text(f"Error retrieving status: {e}")

### Telegram application builder ###

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
    TG_APP.add_handler(CommandHandler("health", tg_health))
    TG_APP.add_handler(CommandHandler("resource", tg_resource))
    TG_APP.add_handler(CommandHandler("interface", tg_interface))
    TG_APP.add_handler(CommandHandler("dhcplease", tg_dhcplease))
    TG_APP.add_handler(CommandHandler("logs", tg_logs))

### Logs processing ###

async def logs_to_telegram(log_line: LogLine) -> None:
    """
    Send a log line to the Telegram chat.
    """
    global TG_APP, TG_CHATID

    logging.debug(f"Testing log line to be sent to Telegram: {log_line}")

    if log_line and log_line.message:
        try:
            if "critical" in log_line.topics and CFG_SEND_CRITICAL:
                content = f"{log_line.dvchost} CRITICAL: \n\n{log_line.message}"
            elif "error" in log_line.topics and CFG_SEND_ERROR:
                content = f"{log_line.dvchost} ERROR: \n\n{log_line.message}"
            elif "warning" in log_line.topics and CFG_SEND_WARNING:
                content = f"{log_line.dvchost} WARNING: \n\n{log_line.message}"
            elif "info" in log_line.topics and CFG_SEND_INFO:
                content = f"{log_line.dvchost} INFO: \n\n{log_line.message}"
            else:
                logging.debug("Log line does not match any configured filters.")
                return

            # Send the log line to the Telegram chat
            logging.debug(f"Sending log line to chat ID {TG_CHATID}: {content}")
            await TG_APP.bot.send_message(chat_id=TG_CHATID, text=content)
        
        except Exception as e:
            logging.error(f"Failed to send log line to Telegram: {e}")

def decode_log_line(log_line: str) -> LogLine:
    """
    Decode a log line into a LogLine object.
    """
    try:
        return LogLine(log_line)
    except ValueError as e:
        logging.error(f"Failed to decode log line: {e}")
        return None

def start_logs_server(main_loop: asyncio.AbstractEventLoop) -> None:
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
                    if log_line and TG_APP:
                        try:
                            asyncio.run_coroutine_threadsafe(logs_to_telegram(log_line), main_loop)
                        except Exception as e:
                            logging.error(f"Failed to send log line to Telegram: {e}")
                    logging.debug(f"Parsed log line: {log_line}")
                except UnicodeDecodeError as e:
                    logging.error(f"Failed to decode message from {log_address}: {e}")

            logging.info("Logs server stopped.")
        except Exception as e:
            logging.error(f"Error in logs server: {e}")
            exit(1)

### Main function ###

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
    loop = asyncio.get_event_loop()
    logs_thread = threading.Thread(target=start_logs_server, args=(loop,), daemon=False)
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

### Entry point of the script ###

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