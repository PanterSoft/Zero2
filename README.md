# Zero2 Controller System

Automated setup and management for Headless Raspberry Pi Zero 2W.

## Features
- **SSH via Bluetooth**: Creates a Bluetooth Network (PAN) with IP 10.10.10.1.
- **USB OTG**: Enables Ethernet Gadget mode with IP 10.10.20.1.
- **Auto-Hotspot**: Switches to WiFi Hotspot (SSID: Zero2-Setup) if no known network is found.
- **OLED Display**: Shows IP, CPU, Memory usage on Adafruit 128x64 Bonnet.
- **Safe Shutdown**: Initiates shutdown on Low Battery signal (GPIO 25).

## Installation

### Method 1: DietPi Automation (Bootstrap)
1. Flash **DietPi** to your SD Card.
2. Open the SD card volume on your computer (labeled `boot`).
3. Copy ONLY the `Automation_Custom_Script.sh` file from this repository to the root of the `boot` drive.
4. Open `dietpi.txt` (also on the `boot` drive), find `AUTO_SETUP_CUSTOM_SCRIPT_EXEC`, and set it to 0:
   ```text
   AUTO_SETUP_CUSTOM_SCRIPT_EXEC=0
   ```
5. Eject SD card, insert into Pi, and power on.
6. The script will:
   - Configure the system.
   - **Download this repository** from GitHub.
   - Install all necessary components.

### Method 2: Manual Installation
1. Flash OS and boot the Pi.
2. Download and run the script:
   ```bash
   wget https://raw.githubusercontent.com/PanterSoft/Zero2/main/Automation_Custom_Script.sh
   chmod +x Automation_Custom_Script.sh
   sudo ./Automation_Custom_Script.sh
   ```

## Configuration
You can configure features by editing the variables at the top of `Automation_Custom_Script.sh` before using it.

## Usage

### Bluetooth SSH
1. Pair with the Pi from your computer.
2. Connect to the Network Access Point (NAP) provided by the Pi.
3. SSH to `root@10.10.10.1`.

### USB OTG
1. Plugin PC via USB Data port.
2. SSH to `root@10.10.20.1` or `dietpi@10.10.20.1`.

### WiFi
If fails to connect to known WiFi, it creates "Zero2-Setup" hotspot (password: zero2setup). Connect to it and configure standard WiFi via `dietpi-config` or `nmcli`.

