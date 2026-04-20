
# Discord chat bot
Simple Discord bot that acts as a user.

![coverage](https://img.shields.io/badge/coverage-0%25-red)
![build](https://img.shields.io/badge/build-failing-red)
![dev](https://img.shields.io/badge/dev-annoyed-red)


## Features

- 🤖 Adjust the bot's behavior, temperature, and max response length directly via Discord commands.
- 🧠 RAG implemented using ChromaDB.
- ⚙️ Highly Configurable. Configure everything through a central config file
- 🤡 Dumbass dev who commits first and tests... eventually.
- ❌ Generously fills your logs with errors whenever someone sends a picture or video.


## Requirements

- Docker
- Openrouter api key
- Discord application token
## Installation

tl;dr just compose the container. The example of compose file can be found below.
But if you have no idea what you're doing, just follow the guide.
I won't be covering creating Discord application and getting api key from openrouter in this guide.

Install Docker and enable its daemon.

```bash
# Docker installation process varies depending on your operating system.
  
# For Arch linux
sudo pacman -S docker docker-compose
  
# For any other operating system, google how to install Docker for your specific case. 
  
# Enable the Docker daemon if it's not already running.
sudo systemctl enable --now docker
```

Now choose a directory for the bot. Following the [Filesystem Hierarchy Standard](https://en.wikipedia.org/wiki/Filesystem_Hierarchy_Standard), you should create a directory under /srv, but considering you're reading this guide, you probably don't want to mess around with permissions. Directory in /home/$USER will be just fine.

```bash
mkdir ~/discord-chat-bot && cd ~/discord-chat-bot
touch compose.yml .env
```

Edit compose.yml with the editor of your preference(e.g. nano, nvim).
Make sure to change platform from linux/amd64 to linux/arm64 if you're running an arm64 cpu.

```yaml
services:
  discord-bot:
    image: tymurd1/discord-chat-bot
    platform: linux/amd64
    restart: unless-stopped
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - OPENROUTER_KEY=${OPENROUTER_KEY}
    volumes:
      - ./data:/app/data
    env_file: .env
networks: {}
```

Populate your .env file with your secrets. Replace <apikey> with your actual keys.

```Env
DISCORD_TOKEN=<apikey>
OPENROUTER_KEY=<apikey>
```

Now compose (turn on) the container in detached mode.

```bash
docker compose up -d
```

On initial run, it will create a data directory with bot_memory (RAG) and config.json, which you can edit. The config file will be populated with new fields on updates automatically.

## Maintenance

To disable the bot, you have to shut down the container.

```bash
docker compose down
```

To update the bot, you have to pull it again from dockerhub.

```bash
docker compose pull
```

If you want to use a different embedding model, you have to shut down the container, change the model in the config and delete the bot_memory directory, and only then start the container again.
