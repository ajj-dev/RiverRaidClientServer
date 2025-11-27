# River Raid - Threaded VPS Edition

A modern recreation of the classic Atari 2600 game River Raid, built as a distributed systems project demonstrating multi-threaded architecture and client-server communication over SSH.

## Overview

This project implements a River Raid clone where:
- **Game server** runs on a VPS with multiple threads controlling game entities
- **Client** connects remotely via SSH to send player input and receive game state
- **Threads H, J, B** autonomously control enemy helicopters, jets, and boats
- **Thread A** processes player input from the remote client

## Features

- Classic River Raid gameplay with modern enhancements
- Multi-threaded game engine (Threads H, J, B, A)
- Secure SSH/SFTP communication with RSA key authentication
- Local and remote play modes
- Checkpoint system
- Fuel management
- Enemy AI
- Respawn system

## Project Structure
```
RiverRaid/
├── game_server.py          # Main game server (runs on VPS)
├── game_client_local.py    # Local testing client (no SSH)
├── game_client_remote.py   # Remote client (connects via SSH)
├── config_remote.json      # VPS connection configuration (not tracked)
├── .gitignore              # Excludes config_remote.json
└── README.md
```

## Requirements

### Server (VPS)
- Python 3.12+
- Linux environment (Ubuntu/Debian recommended)

### Client (Local Machine)
- Python 3.12+
- pygame 2.5+
- paramiko (for remote client)

## Installation

### 1. Server Setup (VPS)
```bash
# SSH into your VPS
ssh user@your-vps-ip

# Install Python dependencies
sudo apt update
sudo apt install python3 python3-pip

# Upload server file
scp game_server.py user@your-vps-ip:~/

# Run the server
python3 game_server.py
```

### 2. Client Setup (Local Machine)
```bash
# Clone repository
git clone <your-repo-url>
cd RiverRaid

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install pygame paramiko
```

## Usage

### Local Testing (No VPS Required)
```bash
# Terminal 1 - Start local server
python game_server.py

# Terminal 2 - Start local client
python game_client_local.py
```

### Remote Play (VPS Required)

#### 1. Create Configuration File

Create `config_remote.json` in the project root directory:
```json
{
  "vps_host": "123.45.67.89",
  "ssh_user": "ubuntu",
  "ssh_key": "C:/Users/YourName/.ssh/river_raid_key"
}
```

**Configuration Options:**
- `vps_host`: Your VPS IP address or hostname
- `ssh_user`: Username on the VPS (e.g., `ubuntu`, `root`, etc.)
- `ssh_key`: Full path to your SSH private key file

**Note:** `config_remote.json` is ignored by git to keep credentials private. Never commit this file to version control.

#### 2. Run Remote Client
```bash
# On VPS - Start server
python3 game_server.py

# On Local Machine - Connect remote client
python game_client_remote.py
```

The client will automatically read connection details from `config_remote.json`.

## SSH Setup

### Generate RSA Key Pair
```bash
# On local machine
ssh-keygen -t rsa -b 4096 -f ~/.ssh/river_raid_key

# Copy public key to VPS
ssh-copy-id -i ~/.ssh/river_raid_key.pub user@your-vps-ip

# Test connection
ssh -i ~/.ssh/river_raid_key user@your-vps-ip
```

### Example `config_remote.json`

**Windows:**
```json
{
  "vps_host": "203.0.113.42",
  "ssh_user": "ubuntu",
  "ssh_key": "C:/Users/PcNub/.ssh/river_raid_key"
}
```

**Linux/Mac:**
```json
{
  "vps_host": "203.0.113.42",
  "ssh_user": "ubuntu",
  "ssh_key": "/home/username/.ssh/river_raid_key"
}
```

**Using `~` shorthand (may require expansion):**
```json
{
  "vps_host": "203.0.113.42",
  "ssh_user": "ubuntu",
  "ssh_key": "~/.ssh/river_raid_key"
}
```

## Controls

| Key | Action |
|-----|--------|
| ← → | Move left/right |
| ↑ ↓ | Speed up/slow down |
| Space | Shoot |
| R | Restart (on game over) |

## Game Mechanics

### Enemies
- **Helicopters (H)** - Move horizontally when player approaches, worth 60 points
- **Jets (J)** - Fly across entire screen, worth 100 points
- **Boats (B)** - Slow horizontal movement, worth 30 points

### Fuel System
- Fuel constantly drains during gameplay
- Fly through fuel depots (F) to refuel
- Shooting fuel depots awards 80 points but destroys them
- Running out of fuel costs a life

### Checkpoints
- Destroy bridges by shooting them (500 points)
- Bridges act as checkpoints
- Respawn at last destroyed bridge after death

### Lives
- Start with 3 lives
- Lose a life by:
  - Hitting riverbanks
  - Colliding with enemies
  - Hitting bridges without destroying them
  - Running out of fuel

## Architecture

### Threading Model
```
┌─────────────────────────────────────────┐
│           Game Server (VPS)             │
├─────────────────────────────────────────┤
│  Thread H: Helicopter management        │
│  Thread J: Jet management               │
│  Thread B: Boat management              │
│  Thread A: Player input processing      │
│  Main Loop: Collision detection, logic  │
│  Replication: State synchronization     │
└─────────────────────────────────────────┘
                    ↕ SSH/SFTP
┌─────────────────────────────────────────┐
│         Client (Local Machine)          │
├─────────────────────────────────────────┤
│  Input capture                          │
│  State rendering (Pygame)               │
│  Network communication (Paramiko)       │
└─────────────────────────────────────────┘
```

### State Synchronization

- **60Hz game tick** on server
- **60Hz state replication** via JSON over SFTP
- **Client prediction** for responsive input
- **Last-good-state caching** for network hiccups

## Technical Details

### Shared Memory
Game state stored in `/tmp/game_state.json` on VPS:
```json
{
  "player": {"x": 400, "y": 520, "fuel": 85, "lives": 3, "score": 1200},
  "helicopters": [{"x": 350, "y": 200}],
  "tankers": [{"x": 450, "y": 300}],
  "jets": [{"x": 600, "y": 150}],
  "fuel_depots": [{"x": 400, "y": -200}],
  "bridges": [{"x": 400, "y": -800, "destroyed": false, "id": 2}],
  "river_walls": {"left": 237.5, "right": 562.5},
  "game_over": false
}
```

### Network Protocol
- **Input**: Client writes to `/tmp/player_input.json` via SFTP
- **State**: Client reads from `/tmp/game_state.json` via SFTP
- **Security**: RSA key authentication, no passwords transmitted
- **Configuration**: Connection details stored in `config_remote.json` (git-ignored)

## Troubleshooting

### Missing Configuration File
```
Error: config_remote.json not found
```
**Solution:** Create `config_remote.json` with your VPS details (see Usage section above).

### Invalid Configuration
```
Error: config_remote.json is missing one of: vps_host, ssh_user, ssh_key
```
**Solution:** Ensure all three fields are present in your `config_remote.json`:
```json
{
  "vps_host": "YOUR_VPS_IP",
  "ssh_user": "YOUR_USERNAME",
  "ssh_key": "PATH/TO/YOUR/KEY"
}
```

### Connection Issues
```bash
# Test SSH connection manually
ssh -v -i ~/.ssh/river_raid_key user@vps-ip

# Check VPS firewall
sudo ufw status
sudo ufw allow 22/tcp

# Verify SSH service
sudo systemctl status ssh
```

### Game Not Starting
```bash
# Check server is running
ps aux | grep game_server.py

# Check file permissions
ls -l /tmp/game_state.json /tmp/player_input.json

# View server logs
python3 game_server.py  # Check terminal output
```

### Low FPS
- Reduce enemy spawn rates in thread functions
- Increase `time.sleep()` values in threads
- Check network latency with ping

## Security Notes

- **Never commit `config_remote.json`** to version control (already in `.gitignore`)
- Store SSH private keys securely (use file permissions `chmod 600` on Linux/Mac)
- Use strong passphrases for SSH keys
- Consider using SSH key forwarding for additional security

## Assignment Compliance

This project fulfills the following requirements:

1. ✅ **VPS Deployment**: Game server runs on cloud VPS
2. ✅ **Remote Input**: Client controls game from separate machine
3. ✅ **SSH Security**: RSA key authentication for automated connection
4. ✅ **Shared Memory**: Game state in `/tmp/` on VPS
5. ✅ **Threading**: H, J, B threads auto-controlled; A thread player-controlled
6. ✅ **Documentation**: README + code comments
7. ✅ **Submission**: Source code + video demo + presentation

---
