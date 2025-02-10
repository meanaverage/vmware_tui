# vmware_tui
Text based UI for VMWare Workstation Pro REST API (VMREST)

# VMware Manager TUI

A text user interface (TUI) for managing VMware Workstation virtual machines. Built with Python and curses.

## Features

- List and manage VMware Workstation VMs
- Real-time power state monitoring
- Start/Stop/Suspend VMs
- Customizable themes
- API call monitoring
- Live status updates

## Requirements

- Python 3.8+
- VMware Workstation Pro 17+ with REST API enabled
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
bash
git clone https://github.com/meanaverage/vmware-tui.git
cd vmware-manager

2. Create a virtual environment (optional but recommended):
bash
python -m venv .venv
source .venv/bin/activate

On Windows: .venv\Scripts\activate

4. Install dependencies:
bash
pip install -r requirements.txt

5. Configure credentials:
bash
cp .env.example .env

Edit `.env` with your VMware Workstation REST API credentials.

## Usage

Run the application:

python main.py

### Controls
- ↑/↓: Navigate
- Enter: Select
- c: Configuration menu
- q: Quit

## Configuration

The VMware Workstation REST API must be enabled and configured:

1. Enable the REST API in VMware Workstation
2. Set up your credentials in the `.env` file
3. Ensure the API is accessible at the configured URL

## License

[MIT License](LICENSE)
