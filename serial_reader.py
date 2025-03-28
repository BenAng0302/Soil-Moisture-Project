import customtkinter as ctk
import serial
import threading
import pandas as pd
import datetime
import os
import time
import re
import sys
import random

# Progress bar function
total=30
delay=0.1
block = "█"
for i in range(total + 1):
    progress = int((i / total) * 30)  # Scale progress to fit in 50 characters
    bar = block * progress + " " * (30 - progress)
    sys.stdout.write(f"\r{bar} {i * 2}%")  # Display progress in percentage
    sys.stdout.flush()
    time.sleep(random.uniform(0.01, 0.1))  # Random delay
print("\nDone!")

# Configure Serial Port
SERIAL_PORT = "COM7"  # Change if needed
BAUD_RATE = 115200

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# Function to determine the next available filename (called only ONCE)
def get_next_filenames():
    run_number = 1
    while any(os.path.exists(f"run_{run_number}_{suffix}.xlsx") for suffix in ["a", "b"]):
        run_number += 1
    return f"run_{run_number}_a.xlsx", f"run_{run_number}_b.xlsx"

# Get filenames for this session
log_filename_a, log_filename_b = get_next_filenames()

target_ml = None
entry_time = None

# Function to extract numerical values from a string
def extract_numbers(data):
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", data)
    return [float(num) for num in numbers]

# Function to log data to runX_a.xlsx
def log_data(data):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    numbers = extract_numbers(data)
    
    if len(numbers) == 5:  # Now expecting only 5 values
        new_data = pd.DataFrame([[timestamp] + numbers],
                                columns=["Timestamp", "Total_ADC", "Min_ADC", "Vol_Log_Total2", "Vol_Log_Total1", "Vol_Log_Total1_Offset"])

        if os.path.exists(log_filename_a):
            existing_data = pd.read_excel(log_filename_a, engine="openpyxl")
            updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        else:
            updated_data = new_data

        updated_data.to_excel(log_filename_a, index=False, engine="openpyxl")
        text_area.insert("end", data + "\n")  # Print all serial data
        text_area.yview("end")

        # Check if the last 3 values match the target ml
        check_water_level(timestamp, numbers[-3], numbers[-2], numbers[-1], data)

# Function to log when target ml is reached
def check_water_level(detect_time, vol_log_min, vol_log_total, vol_norm_total, raw_data):
    global target_ml, entry_time
    if target_ml is not None and entry_time is not None:
        if (target_ml - 1 <= vol_log_min <= target_ml + 1 or
            target_ml - 1 <= vol_log_total <= target_ml + 1 or
            target_ml - 1 <= vol_norm_total <= target_ml + 1):
            new_data = pd.DataFrame([[entry_time, detect_time, raw_data]],
                                    columns=["Entry_Timestamp", "Detect_Timestamp", "Serial_Data"])
            if os.path.exists(log_filename_b):
                existing_data = pd.read_excel(log_filename_b, engine="openpyxl")
                updated_data = pd.concat([existing_data, new_data], ignore_index=True)
            else:
                updated_data = new_data
            updated_data.to_excel(log_filename_b, index=False, engine="openpyxl")

# Function to read serial data
def read_serial():
    while True:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                log_data(line)
        time.sleep(0.2)

# Function to start serial reading
def start_reading():
    start_button.configure(state="disabled")
    thread = threading.Thread(target=read_serial, daemon=True)
    thread.start()

# Function to set target ml value
def set_target_ml():
    global target_ml, entry_time
    try:
        target_ml = float(entry.get())
        entry_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_data = pd.DataFrame([[entry_time, None, target_ml]],
                                columns=["Entry_Timestamp", "Detect_Timestamp", "Target_Water_Level_mL"])
        if os.path.exists(log_filename_b):
            existing_data = pd.read_excel(log_filename_b, engine="openpyxl")
            updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        else:
            updated_data = new_data

        updated_data.to_excel(log_filename_b, index=False, engine="openpyxl")
        text_area.insert("end", f"Tracking water level at: {target_ml} mL\n")
    except ValueError:
        text_area.insert("end", "Invalid input! Enter a numeric value.\n")

# UI Setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()
root.title("STM32 Serial Monitor")
root.geometry("1800x1600")

text_area = ctk.CTkTextbox(root, wrap="word", width=1515, height=800)
text_area.grid(row=0, column=0, columnspan=5, rowspan=5, padx=10, pady=10)

start_button = ctk.CTkButton(root, text="Start Reading", command=start_reading)
start_button.grid(row=5, column=0, padx=10, pady=10)

entry = ctk.CTkEntry(root, placeholder_text="Enter water level (mL)")
entry.grid(row=5, column=4, padx=10, pady=10)

ml_button = ctk.CTkButton(root, text="Track Water Level", command=set_target_ml)
ml_button.grid(row=6, column=4, padx=10, pady=10)

root.mainloop()