import logging
import math
import statistics
import threading
import time
import tkinter as tk
from collections import deque
from tkinter import ttk

import serial


# ---------------- HARDWARE CONFIGURATION ----------------
# Update this value for the computer running the GUI.
SERIAL_PORT = "COM5"
BAUD_RATE = 115200
TRG_INCLINE = 30.0  # Display/documentation reference; Arduino decides alarm status.

# GUI configuration
WINDOW_WIDTH = 680
WINDOW_HEIGHT = 520
REFRESH_INTERVAL_MS = 100

# Data handling
MEDIAN_WINDOW = 5
DATA_TIMEOUT_SECONDS = 5  # Startup grace / idle indication only; not a link-failure test.
RECONNECT_DELAY_SECONDS = 3
SERIAL_READ_TIMEOUT_SECONDS = 1


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)


class BedMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Hospital Bed Safety Node Tracker")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg="#F4F6F9")

        self.current_angle = 0.0
        self.current_status = "CONNECTING"
        self.current_uuid = "N/A"

        self.running = True
        self.stop_event = threading.Event()
        self.data_lock = threading.Lock()
        self.angle_samples = deque(maxlen=MEDIAN_WINDOW)

        # Times are measured with time.monotonic(), which is suitable for
        # elapsed-time checks and is unaffected by system-clock adjustments.
        self.connection_time = None
        self.last_valid_data_time = None
        self.serial_error = None

        self.setup_styles()
        self.create_widgets()

        self.serial_thread = threading.Thread(
            target=self.maintain_serial_pipeline,
            name="SerialReader",
            daemon=True,
        )
        self.serial_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh_ui_loop()

    # ---------------- UI STYLING ----------------
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure(
            "TLabel",
            background="#F4F6F9",
            font=("Helvetica", 11),
        )

        self.style.configure(
            "Header.TLabel",
            font=("Helvetica", 16, "bold"),
            foreground="#1E293B",
        )

    # ---------------- UI COMPONENTS ----------------
    def create_widgets(self):
        self.title_label = ttk.Label(
            self.root,
            text="AUTOMATED SAFETY MONITORING SYSTEM",
            style="Header.TLabel",
        )
        self.title_label.pack(pady=15)

        self.canvas = tk.Canvas(
            self.root,
            width=500,
            height=220,
            bg="#FFFFFF",
            highlightthickness=1,
            highlightbackground="#CBD5E1",
        )
        self.canvas.pack(pady=10)

        self.metrics_frame = tk.Frame(self.root, bg="#F4F6F9")
        self.metrics_frame.pack(pady=15, fill=tk.X, padx=30)

        self.uuid_lbl = ttk.Label(
            self.metrics_frame,
            text="DEVICE ID: WAITING...",
            font=("Helvetica", 11, "bold"),
        )
        self.uuid_lbl.pack(side=tk.LEFT, expand=True)

        self.angle_lbl = ttk.Label(
            self.metrics_frame,
            text="BED TILT ANGLE: --°",
            font=("Helvetica", 14, "bold"),
        )
        self.angle_lbl.pack(side=tk.LEFT, expand=True)

        self.status_box = tk.Label(
            self.root,
            text="SYSTEM STATUS: CONNECTING",
            font=("Helvetica", 12, "bold"),
            bg="#E2E8F0",
            fg="#475569",
            width=45,
            height=2,
            bd=1,
            relief=tk.SOLID,
        )
        self.status_box.pack(pady=15)

    # ---------------- BED DRAWING ----------------
    def draw_tilted_bed(self, angle_deg):
        self.canvas.delete("all")

        self.canvas.create_line(
            50, 190, 450, 190,
            fill="#64748B",
            width=4,
            dash=(4, 2),
        )

        self.canvas.create_text(
            250, 205,
            text="Floor Plane Reference",
            fill="#94A3B8",
            font=("Helvetica", 9),
        )

        pivot_x = 220
        pivot_y = 150
        length_head = 140
        length_body = 160

        angle_rad = math.radians(-angle_deg)

        head_end_x = pivot_x + length_head * math.cos(angle_rad)
        head_end_y = pivot_y + length_head * math.sin(angle_rad)

        body_end_x = pivot_x - length_body
        body_end_y = pivot_y

        self.canvas.create_line(
            pivot_x, pivot_y,
            body_end_x, body_end_y,
            fill="#334155",
            width=6,
        )

        self.canvas.create_line(
            pivot_x, pivot_y,
            head_end_x, head_end_y,
            fill="#2563EB",
            width=8,
        )

        self.canvas.create_oval(
            pivot_x - 6, pivot_y - 6,
            pivot_x + 6, pivot_y + 6,
            fill="#0F172A",
            outline="#FFFFFF",
        )

        self.canvas.create_oval(
            head_end_x - 5, head_end_y - 5,
            head_end_x + 5, head_end_y + 5,
            fill="#EF4444",
        )

        self.canvas.create_text(
            head_end_x, head_end_y - 15,
            text="Headrest",
            fill="#1E40AF",
            font=("Helvetica", 10, "bold"),
        )

        self.canvas.create_text(
            body_end_x + 40, body_end_y + 15,
            text="Foot Frame",
            fill="#475569",
            font=("Helvetica", 9),
        )

    # ---------------- SERIAL MESSAGE PARSING ----------------
    @staticmethod
    def parse_serial_message(raw_line):
        """
        Parse the firmware format:
        [START]:DEVICE-ID:12.34:STATUS_SAFE:[END]

        Returns (device_uuid, angle, status), or None for invalid messages.
        """
        if not (
            raw_line.startswith("[START]:")
            and raw_line.endswith(":[END]")
        ):
            return None

        tokens = raw_line.split(":")
        if len(tokens) != 5:
            return None

        try:
            device_uuid = tokens[1].strip()
            angle = float(tokens[2].strip())
            status = tokens[3].strip()
        except (ValueError, IndexError):
            return None

        if not device_uuid or not math.isfinite(angle):
            return None

        if not 0.0 <= angle <= 90.0:
            return None

        if status not in ("STATUS_SAFE", "ALARM_FALL_RISK"):
            return None

        return device_uuid, angle, status

    # ---------------- SERIAL DATA READER ----------------
    def set_connection_state(self, status, error=None):
        with self.data_lock:
            self.current_status = status
            self.serial_error = error

            if status != "CONNECTING":
                self.connection_time = None

            if status == "DISCONNECTED":
                self.last_valid_data_time = None
                self.angle_samples.clear()
                self.current_angle = 0.0
                self.current_uuid = "N/A"

    def maintain_serial_pipeline(self):
        """
        Keep trying to connect. If the USB serial connection is lost,
        close the old connection and retry after a short delay.
        """
        while not self.stop_event.is_set():
            try:
                logging.info("Connecting to Arduino on %s...", SERIAL_PORT)

                with serial.Serial(
                    SERIAL_PORT,
                    BAUD_RATE,
                    timeout=SERIAL_READ_TIMEOUT_SECONDS,
                ) as arduino:
                    # Some Arduino boards reset when the serial port opens.
                    time.sleep(1)

                    if self.stop_event.is_set():
                        break

                    arduino.reset_input_buffer()

                    with self.data_lock:
                        self.connection_time = time.monotonic()
                        self.last_valid_data_time = None
                        self.current_status = "CONNECTING"
                        self.serial_error = None
                        self.angle_samples.clear()
                        self.current_angle = 0.0
                        self.current_uuid = "N/A"

                    logging.info("Serial connection established.")

                    while not self.stop_event.is_set():
                        raw_line = arduino.readline().decode(
                            "utf-8",
                            errors="ignore",
                        ).strip()

                        if not raw_line:
                            continue

                        parsed = self.parse_serial_message(raw_line)
                        if parsed is None:
                            # Firmware also prints diagnostic messages.
                            # Ignore those and process only framed data lines.
                            continue

                        device_uuid, angle, status = parsed

                        with self.data_lock:
                            self.angle_samples.append(angle)
                            filtered_angle = statistics.median(
                                self.angle_samples
                            )

                            self.current_uuid = device_uuid
                            self.current_angle = filtered_angle

                            # The Arduino firmware remains authoritative
                            # for the SAFE / FALL-RISK decision.
                            self.current_status = status
                            self.last_valid_data_time = time.monotonic()
                            self.serial_error = None

                    # Leaving the read loop means the application is closing.
                    break

            except (serial.SerialException, OSError) as exc:
                if self.stop_event.is_set():
                    break

                logging.warning("Serial connection failed: %s", exc)
                self.set_connection_state("DISCONNECTED", str(exc))

            except Exception:
                if self.stop_event.is_set():
                    break

                logging.exception("Unexpected error in serial reader.")
                self.set_connection_state("ERROR", "Unexpected serial-reader error")

            if not self.stop_event.is_set():
                # Event.wait() allows shutdown to interrupt the retry delay.
                self.stop_event.wait(RECONNECT_DELAY_SECONDS)

        logging.info("Serial reader thread stopped.")

    # ---------------- GUI REFRESH ----------------
    def refresh_ui_loop(self):
        if not self.running:
            return

        with self.data_lock:
            angle = self.current_angle
            status = self.current_status
            device_uuid = self.current_uuid
            connection_time = self.connection_time
            last_data_time = self.last_valid_data_time

        # With Wake-on-Motion, silence is normal while the bed is stationary.
        # Use the timeout only to distinguish startup (no first event yet) from
        # an idle sensor after at least one valid event. Do not call it a fault.
        reference_time = (
            last_data_time if last_data_time is not None else connection_time
        )
        timed_out = (
            reference_time is not None
            and time.monotonic() - reference_time > DATA_TIMEOUT_SECONDS
        )
        if timed_out:
            status = (
                "WAITING_FOR_MOTION"
                if last_data_time is None
                else "IDLE"
            )

        self.uuid_lbl.config(text=f"DEVICE ID: {device_uuid}")

        if status in ("CONNECTING", "DISCONNECTED", "ERROR", "WAITING_FOR_MOTION"):
            self.angle_lbl.config(text="BED TILT ANGLE: --°")

            if status == "DISCONNECTED":
                message = "HARDWARE LINK OFFLINE"
            elif status == "ERROR":
                message = "SERIAL READER ERROR"
            elif status == "WAITING_FOR_MOTION":
                message = "CONNECTED • WAITING FOR FIRST MOTION EVENT"
            else:
                message = "CONNECTING TO SENSOR"

            self.status_box.config(
                text=f"SYSTEM STATUS: {message}",
                bg="#E2E8F0" if status == "WAITING_FOR_MOTION" else "#FECACA",
                fg="#334155" if status == "WAITING_FOR_MOTION" else "#991B1B",
            )
            self.draw_tilted_bed(0.0)

        else:
            self.angle_lbl.config(text=f"BED TILT ANGLE: {angle:.2f}°")
            if status == "ALARM_FALL_RISK":
                message = "ALARM: FALL-RISK THRESHOLD EXCEEDED"
                bg, fg = "#FEE2E2", "#991B1B"
            elif status == "IDLE":
                message = "SENSOR IDLE • SHOWING LAST REPORTED STATUS"
                bg, fg = "#E2E8F0", "#334155"
            else:
                message = "SYSTEM STATUS: SAFE"
                bg, fg = "#DCFCE7", "#166534"

            self.status_box.config(text=message, bg=bg, fg=fg)
            self.draw_tilted_bed(angle)

        self.root.after(REFRESH_INTERVAL_MS, self.refresh_ui_loop)

    # ---------------- CLEAN SHUTDOWN ----------------
    def close(self):
        self.running = False
        self.stop_event.set()

        # readline() has a finite timeout, so the worker should exit promptly.
        if self.serial_thread.is_alive():
            self.serial_thread.join(timeout=1.5)

        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    app = BedMonitorGUI(window)
    window.mainloop()
