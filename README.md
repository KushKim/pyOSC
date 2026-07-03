# OSC Master Tool

Cross-platform OSC (Open Sound Control) communication utility built with Python and PyQt6. 
A powerful tool for testing, monitoring, and sequencing OSC messages.

## ✨ Features

### 🌐 Core OSC Communication
* **OSC Send & Receive**: Send custom OSC messages and run a local server to receive them.
* **Real-time Logging**: Built-in log viewer to monitor incoming and outgoing OSC packets.

### 📝 Advanced Macro / Sequential Sending
* **Message Queue (List)**: Add multiple OSC messages to a list for batch processing.
* **Explicit Data Typing**: Send values precisely as `Auto` (smart detect), `int`, `float`, `str`, or `bool`.
* **Sequential Execution**: Send the entire list of messages sequentially with a single click.
* **Adjustable Delay**: Control the time gap (delay in seconds) between each message to prevent network flooding.
* **Selective Deletion**: Use checkboxes to delete specific messages from the queue.

### ⚙️ Smart Configuration
* **Auto-Save Settings**: Automatically saves your last used IP addresses, ports, OSC addresses, values, delay time, and data types via `config.json`.
* **State Restoration**: Restores all previous settings and UI states upon next launch.

### 🌍 Accessibility & UI
* **Bilingual Support**: Switch between English and Korean UI seamlessly.
* **Cross-Platform**: Fully supported and automatically built for Windows and macOS.

### 🚀 CI/CD & Deployment
* **Automated Builds**: GitHub Actions automatically builds Windows (`.exe`) and macOS (`.app`/`.zip`) binaries upon tagging a new release.
* **Smart Versioning**: Output files automatically include the release version tag (e.g., `OSC_Master_Tool_v1.2.0_Windows.exe`).

## Requirements

* Python 3.12+
* PyQt6
* python-osc

## License

MIT

Made by KushKim