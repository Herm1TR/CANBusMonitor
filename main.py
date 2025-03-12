from GUI import *


if __name__ == "__main__":
    root = tk.Tk()
    app = CANBusMonitor(root)


    def on_closing():
        if app.m_reading:
            app.stop_reading()
        root.destroy()


    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
