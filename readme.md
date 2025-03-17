# CAN Bus Monitor

## Overview
CAN Bus Monitor is a graphical tool for monitoring and interacting with CAN buses using PCAN interfaces. It allows users to:
- Initialize and connect to PCAN devices
- Monitor incoming CAN messages in real-time
- Decode messages according to a DBC file
- Transmit custom CAN messages with configurable signals
- View detailed information about received and transmitted messages

## Features
- **Channel Selection**: Choose from available PCAN interfaces
- **Baudrate Configuration**: Support for multiple baudrates from 5 kbit/s to 1 Mbit/s
- **Real-time Monitoring**: View incoming CAN messages with ID, type, data, and cycle time
- **Message Decoding**: Decode CAN messages according to a DBC definition file
- **Detailed Signal View**: See individual signal values in received messages
- **Custom Message Transmission**: Configure and send CAN messages with customizable signal values
- **Scheduled Transmission**: Set intervals for periodic message transmission
- **Reset Functionality**: Clear all displays and start fresh

## Requirements
- Python 3.6+
- Required Python packages:
  - tkinter
  - [python-can](https://python-can.readthedocs.io/)
  - [cantools](https://cantools.readthedocs.io/)
  - [PCANBasic](https://www.peak-system.com/Software-APIs.305.0.html?&L=1)

## Installation
1. Install the required Python packages:
   ```
   pip install python-can cantools
   ```

2. Install PCAN drivers and SDK from [PEAK-System](https://www.peak-system.com/Downloads.76.0.html?&L=1)

3. Place your DBC file in an accessible location and update the path in the code:
   ```python
   self.db = cantools.database.load_file("path/to/your/file.dbc")
   ```

## Usage
1. Launch the application:
   ```
   python main.py
   ```

2. Initialize the CAN connection:
   - Select a PCAN channel from the dropdown list
   - Choose the appropriate baudrate
   - Click "Initialize"

3. Start receiving messages:
   - Click "Start Receiving" to monitor CAN traffic
   - The upper pane shows a list of received messages
   - The lower pane displays detailed signal information

4. Transmit custom messages:
   - Click "Add Message" to create a new message configuration
   - Enter the message ID in hexadecimal format
   - Click "Load Signals" to load signal definitions from the DBC file
   - Enter signal values
   - Set the transmission interval
   - Click "Start Transmitting" to begin sending the message

5. Reset the application:
   - Click "Reset" to clear all displays
   - Initialize again to start fresh

## Error Handling
The application handles various errors including:
- Missing PCAN channels
- Initialization failures
- Invalid message IDs or values
- Transmission failures

If you encounter issues, check:
- PCAN device connection
- DBC file path correctness
- Baudrate setting

## Feedback and Contributions
For issues, suggestions, or contributions, please:
1. Ensure you have the latest version
2. Check your PCAN hardware and connections
3. Verify your DBC file is correctly formatted
4. Contact the developers with detailed error information

## License
This software is provided as-is for educational and development purposes.
