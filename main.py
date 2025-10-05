import websocket
import threading
import time
import re
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import ANSI
import sys

SERVER_URL = "wss://irc-ws.chat.twitch.tv:443"

BOT_NAME = ""
CHANNEL = ""
TOKEN = "oauth:"

session = PromptSession()

def colorize(segments):
    colors = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "normal": "\033[0m",
        "bold": "\033[1m",
        "underline": "\033[4m",
    }

    result = ""
    for color, text in segments:
        code = colors.get(color.lower(), "\033[0m")
        result += f"{code}{text}"
    result += "\033[0m"  # Reset at the end
    return result

message_regex = re.compile(r'^(?::(\S+)!)?(\S+)\s+(\S+)\s+#(\S+)\s+:(.*)$')

def on_message(ws, message):
    if message.startswith("PING :tmi.twitch.tv"):
        ws.send("PONG :tmi.twitch.tv")
        print_formatted_text(ANSI("\033[33mResponded to PING\033[0m"))  # Yellow text
        return

    match = message_regex.match(message)
    if match:
        prefix, user, command, channel, text = match.groups()
        user = user.split("@")[0]
        msg = colorize([
            ("red", "["),
            ("red", user),
            ("red", "@"),
            ("red", channel),
            ("red", "]"),
            ("red", "$ "),
            ("white", text.strip())
        ])
        print_formatted_text(ANSI(msg))
    else:
        print_formatted_text(ANSI(f"\033[31mRaw message: {message}\033[0m"))  # Red text

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    print("Connection opened. Listening for messages...")

    ws.send(f"PASS {TOKEN}")
    ws.send(f"NICK {BOT_NAME}")
    ws.send(f"JOIN {CHANNEL}")

    # Background thread for sending messages
    def send_loop():
        try:
            while True:
                with patch_stdout():
                    msg = session.prompt("> ")
                if msg.lower() == "quit":
                    ws.send(f"PART {CHANNEL}");
                    ws.close()
                    break
                ws.send(f"PRIVMSG {CHANNEL} :{msg}")
        except KeyboardInterrupt:
            ws.send(f"PART {CHANNEL}");
            ws.close()

    threading.Thread(target=send_loop, daemon=True).start()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} #<channel>")
        sys.exit(1)
    CHANNEL = sys.argv[1]

    ws = websocket.WebSocketApp(
        SERVER_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received, closing connection...")
        ws.send(f"PART {CHANNEL}")
        ws.close()
