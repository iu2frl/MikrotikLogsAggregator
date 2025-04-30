# Mikrotik to Telegram Interface using Python

This project provides an interface to forward MikroTik logs to a Telegram bot and interact with the MikroTik API.

## Features

- Receive MikroTik logs via UDP and process them.
- Interact with the MikroTik API to retrieve system health and status.
- Telegram bot integration to handle commands like `/start`, `/help`, and `/status`.

## Setting up the Environment

To run this project, you need to set up the following environment variables. You can use a `.env` file for this purpose.

```bash
TG_BOTTOKEN="xxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Telegram bot token
TG_CHATID="-00000000000"                   # Telegram chat ID
MKT_API_ADDRESS="1.2.3.4"                  # MikroTik API address
MKT_API_PORT=8729                          # MikroTik API port
MKT_API_USER="someuser"                    # MikroTik API username
MKT_API_PASS="somepass"                    # MikroTik API password
MKT_LOGS_PORT=10514                        # UDP port for MikroTik logs
```

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd MikrotikLogsAggregator
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project directory and add the environment variables as shown above.

## Running the Application

### Using Python

1. Start the application:

```bash
python3 main.py
```

2. The application will:
   - Start a UDP server to listen for MikroTik logs.
   - Start a Telegram bot to handle commands.

### Using Docker

You can both pull the pre-built images from `ghcr.io/iu2frl/mikrotiklogsaggregator:latest` or build your own image

#### Build the Docker Image

1. Build the Docker image locally:

```bash
docker build -t mikrotiklogsaggregator .
```

#### Run the Docker Container

1. Run the container using `docker run`:

```bash
docker run -d \
    --name mikrotik-telegram \
    --env-file .env \
    -p 10514:10514/udp \
    mikrotiklogsaggregator
```

or:

```bash
docker run -d \
    --name mikrotik-telegram \
    --env-file .env \
    -p 10514:10514/udp \
    ghcr.io/iu2frl/mikrotiklogsaggregator:latest
```

Where:

- `--env-file .env`: Passes the environment variables from the .env file.
- `-p 10514:10514/udp`: Maps the UDP port for MikroTik logs.

#### Using Docker Compose

1. Create a `docker-compose.yml` file with the following content:

```yaml
version: "3.8"

services:
    mikrotik-telegram:
    image: mikrotiklogsaggregator
    container_name: mikrotik-telegram
    env_file: .env
    ports:
        - "10514:10514/udp"
    restart: unless-stopped
```

or:

```yaml
version: "3.8"

services:
    mikrotik-telegram:
    image: ghcr.io/iu2frl/mikrotiklogsaggregator:latest
    container_name: mikrotik-telegram
    env_file: .env
    ports:
        - "10514:10514/udp"
    restart: unless-stopped
```

2. Start the container using Docker Compose:

```bash
docker-compose up -d
```

3. To stop the container:

```bash
docker-compose down
```

## Telegram Bot Commands

The Telegram bot supports the following commands:

- `/start`: Sends a welcome message.
- `/help`: Displays a list of available commands.
- `/status`: Retrieves the status of the MikroTik device.

## Configuring the Mikrotik device

Configure the Mikrotik device as follows:

```mikrotik
/system logging action
add cef-event-delimiter="" name=Docker remote=10.40.0.64 remote-log-format=cef remote-port=10514 syslog-time-format=iso8601 target=remote
/system logging
add action=Docker topics=info
add action=Docker topics=warning
add action=Docker topics=error
add action=Docker topics=critical
```

Make sure to replace the `remote` address with the address of the machine where the script (or the container) is running.

## Logging

The application uses Python's `logging` module to log events. Logs are displayed in the console with different levels (INFO, WARNING, ERROR, DEBUG).

## UDP Logs Server

The application starts a UDP server to listen for logs from MikroTik devices. Ensure that your MikroTik device is configured to send logs to the server's IP address and the specified port (`MKT_LOGS_PORT`).

## MikroTik API Integration

The application connects to the MikroTik API to retrieve system health and status. Ensure that the API service is enabled on your MikroTik device and that the credentials provided in the .env file are correct.

## Stopping the Application

To stop the application, press `Ctrl+C`. This will gracefully shut down the Telegram bot and the UDP logs server.

If running in Docker, use the following commands:

- For `docker run`:

```bash
docker stop mikrotik-telegram
docker rm mikrotik-telegram
```

- For Docker Compose:

```bash
docker-compose down
```

## Troubleshooting

- Ensure that the .env file is correctly configured with valid values.
- Check that the MikroTik device is configured to send logs to the correct IP and port.
- Verify that the Telegram bot token and chat ID are correct.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
