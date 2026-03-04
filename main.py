import tkinter as tk
from tkinter import ttk, messagebox
import pyaudio
import threading
import numpy as np

# AudioStreamer handles the audio streaming and calculates the amplitude for visualization.
class AudioStreamer:
    def __init__(self, input_device, output_device, chunk=1024, rate=44100, channels=1, fmt=pyaudio.paInt16):
        self.input_device = input_device
        self.output_device = output_device
        self.chunk = chunk
        self.rate = rate
        self.channels = channels
        self.format = fmt
        self.p = pyaudio.PyAudio()
        self.stream_in = None
        self.stream_out = None
        self.running = False
        # This variable will store the latest amplitude (for visualization)
        self.latest_amplitude = 0

    def start(self):
        try:
            self.stream_in = self.p.open(format=self.format,
                                         channels=self.channels,
                                         rate=self.rate,
                                         input=True,
                                         frames_per_buffer=self.chunk,
                                         input_device_index=self.input_device)
            self.stream_out = self.p.open(format=self.format,
                                          channels=self.channels,
                                          rate=self.rate,
                                          output=True,
                                          frames_per_buffer=self.chunk,
                                          output_device_index=self.output_device)
        except Exception as e:
            messagebox.showerror("Error", f"Error opening streams: {e}")
            return

        self.running = True
        # Start audio streaming on a background thread so that the GUI stays responsive.
        threading.Thread(target=self.stream_audio, daemon=True).start()

    def stream_audio(self):
        while self.running:
            try:
                data = self.stream_in.read(self.chunk, exception_on_overflow=False)
                self.stream_out.write(data)
                # Convert byte data to numpy array to calculate the amplitude.
                audio_data = np.frombuffer(data, dtype=np.int16)
                # Compute the average absolute amplitude
                amplitude = np.abs(audio_data).mean()
                self.latest_amplitude = amplitude
            except Exception as e:
                print(f"Error during streaming: {e}")
                break

    def stop(self):
        self.running = False
        if self.stream_in is not None:
            self.stream_in.stop_stream()
            self.stream_in.close()
        if self.stream_out is not None:
            self.stream_out.stop_stream()
            self.stream_out.close()
        self.p.terminate()


# The main App class creates the Tkinter GUI.
class App:
    def __init__(self, root):
        self.root = root
        root.title("Audio Visualizer - Sweetie")
        self.audio_streamer = None

        # Create a PyAudio instance to list available devices.
        self.p = pyaudio.PyAudio()
        self.input_devices = []
        self.output_devices = []
        self.populate_devices()

        # Input device selection dropdown.
        tk.Label(root, text="Select Input Device:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.input_combo = ttk.Combobox(root, values=[f"[{d['index']}] {d['name']}" for d in self.input_devices],
                                        state="readonly", width=50)
        self.input_combo.grid(row=0, column=1, padx=10, pady=5)

        # Output device selection dropdown.
        tk.Label(root, text="Select Output Device:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.output_combo = ttk.Combobox(root, values=[f"[{d['index']}] {d['name']}" for d in self.output_devices],
                                         state="readonly", width=50)
        self.output_combo.grid(row=1, column=1, padx=10, pady=5)

        # Buttons to start and stop the streaming.
        self.start_button = tk.Button(root, text="Start Streaming", command=self.start_streaming)
        self.start_button.grid(row=2, column=0, padx=10, pady=10)
        self.stop_button = tk.Button(root, text="Stop Streaming", command=self.stop_streaming, state="disabled")
        self.stop_button.grid(row=2, column=1, padx=10, pady=10)

        # Canvas for the audio visualizer.
        self.canvas = tk.Canvas(root, width=400, height=100, bg="black")
        self.canvas.grid(row=3, column=0, columnspan=2, padx=10, pady=10)
        # This rectangle will show the audio level.
        self.visualizer_rect = self.canvas.create_rectangle(10, 10, 10, 90, fill="green")

        # Start the visualizer update loop.
        self.update_visualizer()

    def populate_devices(self):
        # Iterate over available devices and add devices that support input/output.
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            dev_info = {"index": i, "name": dev.get('name')}
            if dev.get("maxInputChannels", 0) > 0:
                self.input_devices.append(dev_info)
            if dev.get("maxOutputChannels", 0) > 0:
                self.output_devices.append(dev_info)
        self.p.terminate()

    def start_streaming(self):
        # Ensure both devices are selected.
        if not self.input_combo.get() or not self.output_combo.get():
            messagebox.showwarning("Warning", "Please select both input and output devices, sweetie!")
            return

        # Extract the device indices from the dropdown values.
        input_index = int(self.input_combo.get().split(']')[0][1:])
        output_index = int(self.output_combo.get().split(']')[0][1:])

        self.audio_streamer = AudioStreamer(input_index, output_index)
        self.audio_streamer.start()

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

    def stop_streaming(self):
        if self.audio_streamer:
            self.audio_streamer.stop()
            self.audio_streamer = None
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        messagebox.showinfo("Info", "Streaming stopped, sweetie!")

    def update_visualizer(self):
        # Update the visualizer based on the latest amplitude.
        if self.audio_streamer:
            amplitude = self.audio_streamer.latest_amplitude
        else:
            amplitude = 0

        # Map amplitude (0 to around 32767 for 16-bit audio) to a width on the canvas.
        max_amp = 32767
        # Scale the bar width (canvas width is 400, so we leave some padding)
        bar_width = (amplitude / max_amp) * 380  # 380 allows for padding on a 400-wide canvas
        self.canvas.coords(self.visualizer_rect, 10, 10, 10 + bar_width, 90)

        # Schedule the next visualizer update after 50 milliseconds.
        self.root.after(50, self.update_visualizer)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
