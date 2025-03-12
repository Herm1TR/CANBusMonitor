import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PCANBasic import *
import cantools
import uuid
import threading


class CANBusMonitor:
    def __init__(self, master):
        self.master = master
        master.title("CAN Bus Monitor")

        # CAN initialization
        self.m_objPCANBasic = PCANBasic()
        self.available_channels = self.get_available_channels()
        if not self.available_channels:
            messagebox.showerror("Error", "No PCAN channels available")
        else:
            self.PcanHandle = self.available_channels[0][1]  # Default to first available channel

        self.baudrates = [
            ("1 MBit/sec", PCAN_BAUD_1M),
            ("800 kBit/sec", PCAN_BAUD_800K),
            ("500 kBit/sec", PCAN_BAUD_500K),
            ("250 kBit/sec", PCAN_BAUD_250K),
            ("125 kBit/sec", PCAN_BAUD_125K),
            ("100 kBit/sec", PCAN_BAUD_100K),
            ("95.238 kBit/sec", PCAN_BAUD_95K),
            ("83.333 kBit/sec", PCAN_BAUD_83K),
            ("50 kBit/sec", PCAN_BAUD_50K),
            ("47.619 kBit/sec", PCAN_BAUD_47K),
            ("33.333 kBit/sec", PCAN_BAUD_33K),
            ("20 kBit/sec", PCAN_BAUD_20K),
            ("10 kBit/sec", PCAN_BAUD_10K),
            ("5 kBit/sec", PCAN_BAUD_5K)
        ]

        self.PcanHandle = PCAN_USBBUS1  # Default channel
        self.Bitrate = PCAN_BAUD_500K  # Default baudrate
        self.m_initialize = False
        self.m_reading = False
        self.TimerInterval = 10  # milliseconds

        # Replace DBC file path
        self.db = cantools.database.load_file("D:\Hydrogen_Valley_Power\Four_in_one\Four_in_one.dbc")

        # Handle the receiving and transmitting text widget display
        self.message_handlers = {}
        for msg in self.db.messages:
            self.message_handlers[msg.frame_id] = self._create_message_handler(msg)

        self.last_transmitted_values = {}

        # Tracking the last received time
        self.last_received_times = {}

        # Attribute to store threads
        self.receive_thread = None
        self.transmit_threads = {}

        # Attribute to store receive and transmit message_details_text
        self.message_details_texts = {}

        # Create main frames with specific weight ratios
        self.toolbar_frame = ttk.Frame(master)
        self.receive_frame = ttk.LabelFrame(master, text="Receive")
        self.message_config_frame = ttk.LabelFrame(master, text="Transmit")
        self.transmit_frame = ttk.LabelFrame(master, text="Transmitted Messages")

        master.grid_rowconfigure(0, weight=0)  # Toolbar frame (no vertical expansion)
        master.grid_rowconfigure(1, weight=4)  # Receive frame
        master.grid_rowconfigure(2, weight=1)  # Message config frame
        master.grid_rowconfigure(3, weight=1)  # Transmit frame
        master.grid_columnconfigure(0, weight=1)

        self.toolbar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.receive_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.message_config_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.transmit_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)

        self.create_toolbar()
        self.create_receive_frame()
        self.create_message_config_frame()
        self.create_transmit_details_frame()

        # Disable receive and transmit button in the start
        self.start_stop_receive_button.config(state=tk.DISABLED)
        self.global_transmit_button.config(state=tk.DISABLED)

# -------------------------------------------------- GUI setup ------------------------------------------------------- #
    def create_toolbar(self):
        # Configure columns for left and right groups
        self.toolbar_frame.grid_columnconfigure(6, weight=1)  # This will create space between left and right groups

        # Left group: Channel, Baudrate, Initialize
        ttk.Label(self.toolbar_frame, text="Channel:").grid(row=0, column=0, padx=(5, 2), sticky="w")
        self.channel_combobox = ttk.Combobox(self.toolbar_frame, values=[channel[0] for channel in self.available_channels], width=20)
        self.channel_combobox.grid(row=0, column=1, padx=2, sticky="w")
        self.channel_combobox.set("")
        self.channel_combobox.bind("<<ComboboxSelected>>", self.on_channel_change)

        self.refresh_button = ttk.Button(self.toolbar_frame, text="Refresh", command=self.refresh_channels)
        self.refresh_button.grid(row=0, column=2, padx=2, sticky="w")

        ttk.Label(self.toolbar_frame, text="Baudrate:").grid(row=0, column=3, padx=(5, 2), sticky="w")
        self.baudrate_combobox = ttk.Combobox(self.toolbar_frame, values=[rate[0] for rate in self.baudrates], width=15)
        self.baudrate_combobox.grid(row=0, column=4, padx=2, sticky="w")
        self.baudrate_combobox.set("500 kBit/sec")
        self.baudrate_combobox.bind("<<ComboboxSelected>>", self.on_baudrate_change)

        self.initialize_button = ttk.Button(self.toolbar_frame, text="Initialize", command=self.initialize_settings)
        self.initialize_button.grid(row=0, column=5, padx=(5, 2), sticky="w")
        if not self.available_channels:
            self.initialize_button.config(state=tk.DISABLED)

        # Add Reset button
        self.reset_button = ttk.Button(self.toolbar_frame, text="Reset", command=self.reset_all)
        self.reset_button.grid(row=0, column=6, padx=5, sticky="w")

        # Right group: Interval, Set Interval, Start/Stop Receiving
        ttk.Label(self.toolbar_frame, text="Interval (ms):").grid(row=0, column=6, padx=(5, 2), sticky="e")
        self.interval_entry = ttk.Entry(self.toolbar_frame, width=5)
        self.interval_entry.grid(row=0, column=7, padx=2, sticky="e")
        self.interval_entry.insert(0, str(self.TimerInterval))

        self.set_interval_button = ttk.Button(self.toolbar_frame, text="Set Interval", command=self.set_interval)
        self.set_interval_button.grid(row=0, column=8, padx=2, sticky="e")

        self.start_stop_receive_button = ttk.Button(self.toolbar_frame, text="Start Receiving", command=self.toggle_receive)
        self.start_stop_receive_button.grid(row=0, column=9, padx=(2, 5), sticky="e")

    def create_receive_frame(self):
        self.receive_frame.grid_columnconfigure(0, weight=1)
        self.receive_frame.grid_rowconfigure(0, weight=2)
        self.receive_frame.grid_rowconfigure(1, weight=1)

        # Treeview
        tree_frame = ttk.Frame(self.receive_frame)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.receive_tree = ttk.Treeview(tree_frame, columns=("Msg_Name", "CAN-ID (hex)", "Type", "Length", "Data", "Cycle Time (ms)", "Count"), show="headings")
        self.receive_tree.grid(row=0, column=0, sticky="nsew")

        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.receive_tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.receive_tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.receive_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        for col in self.receive_tree["columns"]:
            self.receive_tree.heading(col, text=col)
            self.receive_tree.column(col, width=100)

        # Message details
        self.message_details_frame = ttk.Frame(self.receive_frame)
        self.message_details_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.message_details_frame.grid_rowconfigure(0, weight=1)
        self.message_details_frame.grid_columnconfigure(0, weight=1)

        self.details_canvas = tk.Canvas(self.message_details_frame)
        self.details_canvas.grid(row=0, column=0, sticky="nsew")

        self.details_v_scrollbar = ttk.Scrollbar(self.message_details_frame, orient="vertical", command=self.details_canvas.yview)
        self.details_v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.details_h_scrollbar = ttk.Scrollbar(self.message_details_frame, orient="horizontal", command=self.details_canvas.xview)
        self.details_h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.details_scrollable_frame = ttk.Frame(self.details_canvas)
        self.details_canvas.create_window((0, 0), window=self.details_scrollable_frame, anchor="nw")

        self.details_scrollable_frame.bind("<Configure>", lambda e: self.details_canvas.configure(scrollregion=self.details_canvas.bbox("all")))
        self.details_canvas.configure(yscrollcommand=self.details_v_scrollbar.set, xscrollcommand=self.details_h_scrollbar.set)

        self.message_details_texts = {}

    def create_message_config_frame(self):
        self.message_config_frame.grid_columnconfigure(0, weight=1)
        self.message_config_frame.grid_rowconfigure(1, weight=1)

        # Controls frame
        controls_frame = ttk.Frame(self.message_config_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(2, 5))
        controls_frame.grid_columnconfigure(1, weight=1)

        ttk.Button(controls_frame, text="Add Message", command=self.add_message_config).grid(row=0, column=0, padx=(0, 5), sticky="w")

        self.global_transmit_button = ttk.Button(controls_frame, text="Start All Transmissions", command=self.toggle_all_transmissions)
        self.global_transmit_button.grid(row=0, column=1, padx=(5, 0), sticky="e")

        # Message configurations frame
        self.message_configs_frame = ttk.Frame(self.message_config_frame)
        self.message_configs_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.config_canvas = tk.Canvas(self.message_configs_frame)
        self.config_canvas.grid(row=0, column=0, sticky="nsew")

        self.config_v_scrollbar = ttk.Scrollbar(self.message_configs_frame, orient="vertical", command=self.config_canvas.yview)
        self.config_v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.config_h_scrollbar = ttk.Scrollbar(self.message_configs_frame, orient="horizontal", command=self.config_canvas.xview)
        self.config_h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.config_scrollable_frame = ttk.Frame(self.config_canvas)
        self.config_canvas.create_window((0, 0), window=self.config_scrollable_frame, anchor="nw")

        self.config_scrollable_frame.bind("<Configure>", lambda e: self.config_canvas.configure(scrollregion=self.config_canvas.bbox("all")))
        self.config_canvas.configure(yscrollcommand=self.config_v_scrollbar.set, xscrollcommand=self.config_h_scrollbar.set)

        self.message_configs_frame.grid_rowconfigure(0, weight=1)
        self.message_configs_frame.grid_columnconfigure(0, weight=1)

        self.message_configs = []

    def create_transmit_details_frame(self):
        self.transmit_frame.grid_columnconfigure(0, weight=1)
        self.transmit_frame.grid_rowconfigure(0, weight=1)

        self.transmit_canvas = tk.Canvas(self.transmit_frame)
        self.transmit_canvas.grid(row=0, column=0, sticky="nsew")

        self.transmit_v_scrollbar = ttk.Scrollbar(self.transmit_frame, orient="vertical", command=self.transmit_canvas.yview)
        self.transmit_v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.transmit_h_scrollbar = ttk.Scrollbar(self.transmit_frame, orient="horizontal", command=self.transmit_canvas.xview)
        self.transmit_h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.transmit_scrollable_frame = ttk.Frame(self.transmit_canvas)
        self.transmit_canvas.create_window((0, 0), window=self.transmit_scrollable_frame, anchor="nw")

        self.transmit_scrollable_frame.bind("<Configure>", lambda e: self.transmit_canvas.configure(scrollregion=self.transmit_canvas.bbox("all")))
        self.transmit_canvas.configure(yscrollcommand=self.transmit_v_scrollbar.set, xscrollcommand=self.transmit_h_scrollbar.set)

        self.transmit_details_texts = {}

    def get_available_channels(self):
        available_channels = []
        result = self.m_objPCANBasic.GetValue(PCAN_NONEBUS, PCAN_ATTACHED_CHANNELS)
        if result[0] == PCAN_ERROR_OK:
            # Include only connectable channels
            for channel in result[1]:
                new_channel = (self.FormatChannelName(channel.channel_handle), channel.channel_handle)
                available_channels.append(new_channel)
        return available_channels

    def on_channel_change(self, event):
        selected_channel = self.channel_combobox.get()
        for channel in self.available_channels:
            if channel[0] == selected_channel:
                self.PcanHandle = channel[1]
                break

        if self.m_reading:
            self.stop_reading()
            self.start_reading()

    def on_baudrate_change(self, event):
        selected_baudrate = self.baudrate_combobox.get()
        for rate in self.baudrates:
            if rate[0] == selected_baudrate:
                self.Bitrate = rate[1]
                break

        if self.m_reading:
            self.stop_reading()
            self.start_reading()

    def initialize_settings(self):
        if not self.m_initialize:
            try:
                if not self.available_channels:
                    raise ValueError("No PCAN channels are available.")

                new_interval = int(self.interval_entry.get())
                if new_interval <= 0:
                    raise ValueError("Interval must be greater than zero")
                self.TimerInterval = new_interval

                selected_baudrate = self.baudrate_combobox.get()
                for rate in self.baudrates:
                    if rate[0] == selected_baudrate:
                        self.Bitrate = rate[1]
                        break

                selected_channel = self.channel_combobox.get()
                for channel in self.available_channels:
                    if channel[0] == selected_channel:
                        self.PcanHandle = channel[1]
                        break

                # Initialize CAN with new settings
                if self.m_reading:
                    self.stop_reading()
                    self.stop_all_transmissions()
                    self.m_initialize = False

                stsResult = self.m_objPCANBasic.Initialize(self.PcanHandle, self.Bitrate)
                if stsResult != PCAN_ERROR_OK:
                    raise Exception(f"Error initializing CAN on {selected_channel} with baudrate {selected_baudrate}")

                messagebox.showinfo("Initialization Successful",
                                    f"Channel: {selected_channel}\n"
                                    f"Baudrate: {selected_baudrate}")

                self.m_initialize = True

                # Enable the Start receiving button
                self.start_stop_receive_button.config(state=tk.NORMAL)
                self.global_transmit_button.config(state=tk.NORMAL)

                self.initialize_button.config(text="Uninitialize")

            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:
            if self.m_reading:
                self.stop_reading()
            self.stop_all_transmissions()
            self.m_objPCANBasic.Uninitialize(self.PcanHandle)
            self.m_initialize = False
            self.initialize_button.config(text="Initialize")

            self.start_stop_receive_button.config(state=tk.DISABLED)
            self.global_transmit_button.config(state=tk.DISABLED)

    def set_interval(self):
        try:
            new_interval = int(self.interval_entry.get())
            if new_interval <= 0:
                raise ValueError("Interval must be greater than zero")
            self.TimerInterval = new_interval
            messagebox.showinfo("Interval Set", f"New interval: {self.TimerInterval}ms")

            if self.m_reading:
                self.stop_reading()
                self.start_reading()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def refresh_channels(self):
        # Stop any ongoing operations
        if self.m_reading:
            self.stop_reading()
        self.stop_all_transmissions()

        # Uninitialize current channel if initialized
        if self.m_initialize:
            self.m_objPCANBasic.Uninitialize(self.PcanHandle)
            self.m_initialize = False
            self.initialize_button.config(text="Initialize")

        # Refresh available channels
        self.available_channels = self.get_available_channels()

        # Update channel combobox
        self.channel_combobox['values'] = [channel[0] for channel in self.available_channels]

        if self.available_channels:
            self.channel_combobox.set(self.available_channels[0][0])
            self.PcanHandle = self.available_channels[0][1]
        else:
            self.channel_combobox.set('')
            messagebox.showwarning("No Channels", "No PCAN channels are currently available.")
            self.initialize_button.config(state=tk.DISABLED)

        # Update GUI states
        self.start_stop_receive_button.config(state=tk.DISABLED)
        self.global_transmit_button.config(state=tk.DISABLED)

    def reset_all(self):
        # Clear receive frame
        for item in self.receive_tree.get_children():
            self.receive_tree.delete(item)

        # Clear message detail frame
        for text_widget in self.message_details_texts.values():
            text_widget.config(state=tk.NORMAL)
            text_widget.delete('1.0', tk.END)
            text_widget.config(state=tk.DISABLED)

        # Clear transmit message configuration frame
        for config in self.message_configs:
            self.remove_message_config(config['id'])

        # Clear transmitted message frame
        for frame in self.transmit_scrollable_frame.winfo_children():
            frame.destroy()
        self.transmit_details_texts.clear()

        # Reset data structures
        self.last_received_times = {}
        self.last_transmitted_values = {}

        # Update the canvas scroll region
        self.transmit_scrollable_frame.update_idletasks()
        self.transmit_canvas.configure(scrollregion=self.transmit_canvas.bbox("all"))

        messagebox.showinfo("Reset", "All displays have been cleared.")
# -------------------------------------------------------------------------------------------------------------------- #

# ----------------------------------------------- Receiving Message -------------------------------------------------- #
    # -------------------------------------------- Receiving Function ------------------------------------------------ #
    def toggle_receive(self):
        if self.m_initialize:
            if not self.m_reading:
                self.start_reading()
            else:
                self.stop_reading()

    def start_reading(self):
        self.m_reading = True
        self.start_stop_receive_button.config(text="Stop receiving")
        self.receive_thread = threading.Thread(target=self.read_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def read_messages(self):
        while self.m_reading:
            stsResult = self.m_objPCANBasic.Read(self.PcanHandle)
            if stsResult[0] == PCAN_ERROR_OK:
                self.process_message(stsResult[1])
            time.sleep(self.TimerInterval / 1000)  # Convert milliseconds to seconds

    def stop_reading(self):
        self.m_reading = False
        self.start_stop_receive_button.config(text="Start receiving")
        if hasattr(self, 'receive_thread'):
            self.receive_thread.join(timeout=1)  # Wait for the thread to finish

    def _create_message_handler(self, msg):
        # Create a custom handler function for the message
        def handle_message(can_msg):
            parsed_msg = msg.decode(can_msg.DATA)
            return parsed_msg

        return handle_message

    def process_message(self, msg):
        try:
            handler = self.message_handlers.get(msg.ID)
            if handler:
                can_msg_name = self.db.get_message_by_frame_id(msg.ID).name
                can_data = bytes(msg.DATA)
                parsed_data = self.db.decode_message(msg.ID, can_data)

                self.master.after(0, self.update_receive_frame, msg, parsed_data, can_msg_name)
            else:
                print(f"Unhandled message with ID: {msg.ID}")
        except cantools.CanError as e:
            print(f"Error parsing message: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    # ---------------------------------------------------------------------------------------------------------------- #

    # ------------------------------------------------ GUI Update ---------------------------------------------------- #
    def update_receive_frame(self, msg, parsed_data, can_msg_name):
        # ------------------------------------------- Receive tree --------------------------------------------------- #
        current_time = time.time()

        # Calculate cycle time
        if msg.ID in self.last_received_times:
            cycle_time = int((current_time - self.last_received_times[msg.ID]) * 1000)  # Convert to milliseconds
        else:
            cycle_time = 0

        self.last_received_times[msg.ID] = current_time

        # Check if a row with this CAN ID already exists
        existing_item = None
        for item in self.receive_tree.get_children():
            if self.receive_tree.item(item)['values'][1] == hex(msg.ID):
                existing_item = item
                break

        new_values = [
            can_msg_name,
            hex(msg.ID),
            self.GetTypeString(msg.MSGTYPE),
            msg.LEN,
            " ".join([f"{b:02X}" for b in msg.DATA]),
            cycle_time,  # Use the calculated cycle time
            1,
        ]

        if existing_item:
            # Update existing row
            current_values = self.receive_tree.item(existing_item)['values']
            new_values[-1] = current_values[-1] + 1  # Increment count
            self.receive_tree.item(existing_item, values=new_values)
        else:
            # Insert new row
            self.receive_tree.insert("", "end", values=new_values)
        # ------------------------------------------------------------------------------------------------------------ #
        # --------------------------------------------- Text Widget -------------------------------------------------- #
        # Update or create message details Text widget
        if msg.ID not in self.message_details_texts:
            # Calculate the position for the new widget
            row = len(self.message_details_texts) // 5
            col = len(self.message_details_texts) % 5

            # Create a new Text widget for this message ID
            frame = ttk.LabelFrame(self.details_scrollable_frame, text=f"ID: {hex(msg.ID)} ({can_msg_name})")
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=12, width=30)
            text_widget.pack(fill="both", expand=True)

            self.message_details_texts[msg.ID] = text_widget

        # Update the specific Text widget for this message ID
        text_widget = self.message_details_texts[msg.ID]
        text_widget.config(state=tk.NORMAL)
        text_widget.delete('1.0', tk.END)

        message_str = f"Type: {self.GetTypeString(msg.MSGTYPE)}\n"
        message_str += f"Cycle Time: {cycle_time} ms\n"
        for signal_name, signal_value in parsed_data.items():
            message_str += f"{signal_name}: {signal_value}\n"

        text_widget.insert(tk.END, message_str)
        text_widget.config(state=tk.DISABLED)

        # Update the canvas scroll region
        self.details_scrollable_frame.update_idletasks()
        self.details_canvas.configure(scrollregion=self.details_canvas.bbox("all"))
        # ------------------------------------------------------------------------------------------------------------ #
    # ---------------------------------------------------------------------------------------------------------------- #
# -------------------------------------------------------------------------------------------------------------------- #

# --------------------------------------------- Transmitting Message ------------------------------------------------- #
    # ------------------------------------------ transmitting Function ----------------------------------------------- #
    def toggle_transmit(self, config_id):
        config = next((c for c in self.message_configs if c['id'] == config_id), None)
        if config:
            if not config['transmitting']:
                self.start_transmitting(config_id)
            else:
                self.stop_transmitting(config_id)

    def start_transmitting(self, config_id):
        config = next((c for c in self.message_configs if c['id'] == config_id), None)
        if not config:
            return

        try:
            msg_id = int(config['msg_id_entry'].get(), 16)
            message = self.db.get_message_by_frame_id(msg_id)

            interval = int(config['interval_entry'].get())
            if interval <= 0:
                raise ValueError("Interval must be a positive integer")

            signal_values = {}
            for signal in message.signals:
                value = config['signals'][signal.name].get()
                signal_values[signal.name] = float(value)

            data = message.encode(signal_values)

            msg = TPCANMsg()
            msg.ID = msg_id
            msg.MSGTYPE = PCAN_MESSAGE_STANDARD
            msg.LEN = len(data)
            for i, byte in enumerate(data):
                msg.DATA[i] = byte

            # # Update the display with the initial transmission details
            # self.update_transmitted_message_display(msg_id, data, signal_values)

            config['transmitting'] = True
            config['thread'] = threading.Thread(target=self.transmit_message_thread,
                                                args=(config_id, msg, interval, signal_values))
            config['thread'].daemon = True
            config['thread'].start()
            self.transmit_threads[config_id] = config['thread']

            config['transmit_button']['text'] = "Stop Transmitting"

        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except KeyError:
            messagebox.showerror("Error", "Message ID not found in DBC file")

    def transmit_message_thread(self, config_id, msg, interval, signal_values):
        config = next((c for c in self.message_configs if c['id'] == config_id), None)
        if not config:
            return

        while config['transmitting']:
            start_time = time.time()

            result = self.m_objPCANBasic.Write(self.PcanHandle, msg)
            if result != PCAN_ERROR_OK:
                print(f"Failed to transmit message {config_id}: {self.m_objPCANBasic.GetErrorText(result, 0x09)}")
                messagebox.showerror("Error", f"Failed to transmit message {config_id}: {self.m_objPCANBasic.GetErrorText(result, 0x09)}")
                config['transmit_button']['text'] = "Start Transmitting"
                break

            # Update the display with the transmitted message details
            self.master.after(0, self.update_transmitted_message_display, msg.ID, bytes(msg.DATA), signal_values)

            # Sleep for the remaining time to maintain the interval
            elapsed_time = time.time() - start_time
            sleep_time = max(0, interval / 1000 - elapsed_time)
            time.sleep(sleep_time)

    def stop_transmitting(self, config_id):
        config = next((c for c in self.message_configs if c['id'] == config_id), None)
        if config:
            config['transmitting'] = False
            if config.get('thread'):
                config['thread'].join(timeout=1)  # Wait for the thread to finish
                config['thread'] = None
            if config_id in self.transmit_threads:
                del self.transmit_threads[config_id]
            config['transmit_button']['text'] = "Start Transmitting"

    def toggle_all_transmissions(self):
        if self.global_transmit_button['text'] == "Start All Transmissions":
            self.start_all_transmissions()
        else:
            self.stop_all_transmissions()

    def start_all_transmissions(self):
        for config in self.message_configs:
            if not config['transmitting']:
                self.start_transmitting(config['id'])
        self.global_transmit_button['text'] = "Stop All Transmissions"

    def stop_all_transmissions(self):
        for config in self.message_configs:
            if config['transmitting']:
                self.stop_transmitting(config['id'])
        self.global_transmit_button['text'] = "Start All Transmissions"
    # ---------------------------------------------------------------------------------------------------------------- #

    # ------------------------------------------------ GUI Update ---------------------------------------------------- #
    def add_message_config(self):
        config_id = str(uuid.uuid4())
        column_index = len(self.message_configs) % 5  # Assume 5 messages per row
        row_index = len(self.message_configs) // 5

        config_frame = ttk.LabelFrame(self.config_scrollable_frame, text=f"Message {len(self.message_configs) + 1}")
        config_frame.grid(row=row_index, column=column_index, padx=5, pady=5, sticky="nsew")

        # Message ID input
        ttk.Label(config_frame, text="Message ID (hex):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        msg_id_entry = ttk.Entry(config_frame, width=10)
        msg_id_entry.grid(row=0, column=1, padx=5, pady=2)

        # Interval input
        ttk.Label(config_frame, text="Interval (ms):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        interval_entry = ttk.Entry(config_frame, width=10)
        interval_entry.grid(row=1, column=1, padx=5, pady=2)
        interval_entry.insert(0, "100")  # Default value

        # Signal frame
        signal_frame = ttk.Frame(config_frame)
        signal_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        # Control buttons
        load_button = ttk.Button(config_frame, text="Load Signals",
                                 command=lambda: self.load_message_signals(msg_id_entry, signal_frame))
        load_button.grid(row=3, column=0, padx=5, pady=2)

        transmit_button = ttk.Button(config_frame, text="Start Transmitting",
                                     command=lambda cid=config_id: self.toggle_transmit(cid))
        transmit_button.grid(row=3, column=1, padx=5, pady=2)

        remove_button = ttk.Button(config_frame, text="Remove",
                                   command=lambda cid=config_id: self.remove_message_config(cid))
        remove_button.grid(row=3, column=2, padx=15, pady=2)

        self.message_configs.append({
            'id': config_id,
            'frame': config_frame,
            'msg_id_entry': msg_id_entry,
            'interval_entry': interval_entry,
            'signal_frame': signal_frame,
            'transmit_button': transmit_button,
            'signals': {},
            'transmitting': False,
            'thread': None  # New attribute for the transmit thread
        })

        self.update_canvas_scroll()

    def remove_message_config(self, config_id):
        config = next((c for c in self.message_configs if c['id'] == config_id), None)
        if config:
            if config['transmitting']:
                self.stop_transmitting(config_id)
            config['frame'].destroy()
            self.message_configs = [c for c in self.message_configs if c['id'] != config_id]
            self.update_message_labels()
            self.reposition_message_configs()
            self.update_canvas_scroll()

    def reposition_message_configs(self):
        for i, config in enumerate(self.message_configs):
            row_index = i // 5
            column_index = i % 5
            config['frame'].grid(row=row_index, column=column_index)

    def update_canvas_scroll(self):
        self.config_scrollable_frame.update_idletasks()
        self.config_canvas.configure(scrollregion=self.config_canvas.bbox("all"))
        self.config_canvas.yview_moveto(0)  # Reset vertical scroll to top
        self.config_canvas.xview_moveto(0)  # Reset horizontal scroll to left

    def update_message_labels(self):
        for i, config in enumerate(self.message_configs):
            config['frame'].configure(text=f"Message {i + 1}")

    def load_message_signals(self, msg_id_entry, signal_frame):
        try:
            msg_id = int(msg_id_entry.get(), 16)
            message = self.db.get_message_by_frame_id(msg_id)

            # Clear existing signal inputs
            for widget in signal_frame.winfo_children():
                widget.destroy()

            # Create input fields for each signal
            signal_inputs = {}
            for i, signal in enumerate(message.signals):
                ttk.Label(signal_frame, text=signal.name).grid(row=i, column=0, sticky="w", padx=5, pady=2)
                signal_inputs[signal.name] = ttk.Entry(signal_frame, width=10)
                signal_inputs[signal.name].grid(row=i, column=1, padx=5, pady=2)

            # Find the corresponding message config and update its signals
            for config in self.message_configs:
                if config['msg_id_entry'] == msg_id_entry:
                    config['signals'] = signal_inputs
                    break

            self.update_canvas_scroll()

        except ValueError:
            messagebox.showerror("Error", "Invalid Message ID")
        except KeyError:
            messagebox.showerror("Error", "Message ID not found in DBC file")

    # -------------------------------------- Text Widget display function -------------------------------------------- #
    def update_transmitted_message_display(self, msg_id, encoded_data, signal_values):
        if msg_id not in self.transmit_details_texts:
            # Calculate the position for the new widget
            row = len(self.transmit_details_texts) // 5
            col = len(self.transmit_details_texts) % 5

            # Create a new Text widget for this message ID
            frame = ttk.LabelFrame(self.transmit_scrollable_frame, text=f"ID: 0x{msg_id:X}")
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=10, width=40)
            text_widget.pack(fill="both", expand=True)

            self.transmit_details_texts[msg_id] = text_widget

        # Update the specific Text widget for this message ID
        text_widget = self.transmit_details_texts[msg_id]
        text_widget.config(state=tk.NORMAL)
        text_widget.delete('1.0', tk.END)

        message_str = f"Encoded Data: {' '.join([f'{b:02X}' for b in encoded_data])}\n"
        message_str += "Signal Values:\n"
        for signal_name, value in signal_values.items():
            message_str += f"  {signal_name}: {value}\n"

        text_widget.insert(tk.END, message_str)
        text_widget.config(state=tk.DISABLED)

        # Check if the data has changed
        if msg_id not in self.last_transmitted_values or self.last_transmitted_values[msg_id] != signal_values:
            self.last_transmitted_values[msg_id] = signal_values.copy()
            text_widget.see(tk.END)  # Scroll to the bottom of this specific text widget

        # Update the canvas scroll region
        self.transmit_scrollable_frame.update_idletasks()
        self.transmit_canvas.configure(scrollregion=self.transmit_canvas.bbox("all"))

    # ---------------------------------------------------------------------------------------------------------------- #
    # ---------------------------------------------------------------------------------------------------------------- #
    def cleanup(self):
        # Stop receiving
        if self.m_reading:
            self.stop_reading()

        # Stop all transmissions
        self.stop_all_transmissions()

        # Uninitialize PCAN
        if self.m_initialize:
            self.m_objPCANBasic.Uninitialize(self.PcanHandle)

        # Wait for receive thread to finish
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1)

        # Wait for all transmit threads to finish
        for thread in self.transmit_threads.values():
            if thread and thread.is_alive():
                thread.join(timeout=1)

# ------------------------------------------------ Help-Functions ---------------------------------------------------- #
    def GetDeviceName(self, handle):
        # Gets the name of a PCAN device
        switcher = {
            PCAN_NONEBUS.value: "PCAN_NONEBUS",
            PCAN_PEAKCAN.value: "PCAN_PEAKCAN",
            PCAN_DNG.value: "PCAN_DNG",
            PCAN_PCI.value: "PCAN_PCI",
            PCAN_USB.value: "PCAN_USB",
            PCAN_VIRTUAL.value: "PCAN_VIRTUAL",
            PCAN_LAN.value: "PCAN_LAN"
        }

        return switcher.get(handle, "UNKNOWN")

    def FormatChannelName(self, handle):
        # Gets the formated text for a PCAN-Basic channel handle
        if handle < 0x100:
            devDevice = TPCANDevice(handle >> 4)
            byChannel = handle & 0xF
        else:
            devDevice = TPCANDevice(handle >> 8)
            byChannel = handle & 0xFF

        return '%s: %s (%.2Xh)' % (self.GetDeviceName(devDevice.value), byChannel, handle)

    def GetTypeString(self, msgtype):
        # Gets the string representation of the type of CAN message
        if (msgtype & PCAN_MESSAGE_STATUS.value) == PCAN_MESSAGE_STATUS.value:
            return 'STATUS'
        if (msgtype & PCAN_MESSAGE_ERRFRAME.value) == PCAN_MESSAGE_ERRFRAME.value:
            return 'ERROR'
        if (msgtype & PCAN_MESSAGE_EXTENDED.value) == PCAN_MESSAGE_EXTENDED.value:
            strTemp = 'EXT'
        else:
            strTemp = 'STD'
        if (msgtype & PCAN_MESSAGE_RTR.value) == PCAN_MESSAGE_RTR.value:
            strTemp += '/RTR'
        else:
            if msgtype > PCAN_MESSAGE_EXTENDED.value:
                strTemp += ' ['
                if (msgtype & PCAN_MESSAGE_FD.value) == PCAN_MESSAGE_FD.value:
                    strTemp += ' FD'
                if (msgtype & PCAN_MESSAGE_BRS.value) == PCAN_MESSAGE_BRS.value:
                    strTemp += ' BRS'
                if (msgtype & PCAN_MESSAGE_ESI.value) == PCAN_MESSAGE_ESI.value:
                    strTemp += ' ESI'
                strTemp += ' ]'
        return strTemp
# -------------------------------------------------------------------------------------------------------------------- #


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1080x1000")  # Set an initial size for the window
    app = CANBusMonitor(root)

    def on_closing():
        app.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
