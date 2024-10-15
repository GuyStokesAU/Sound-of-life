# sound_of_life.py

import sys
import json
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QColorDialog, QComboBox, QFileDialog, QCheckBox, QLineEdit,
    QMessageBox, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen
from pyo import Server, Sine, Square, Saw, Tri, Sig, Fader, Mixer, Record, Path


class Grid(QWidget):
    """
    Represents the Game of Life grid.
    """

    def __init__(self, rows=10, cols=10, cell_size=20, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.grid = np.zeros((self.rows, self.cols), dtype=bool)
        self.setFixedSize(self.cols * self.cell_size, self.rows * self.cell_size)
        self.rules = {'birth': [3], 'survival': [2, 3]}
        self.show_gridlines = True
        self.rule_colors = {}  # To store colors for different rules

    def set_rules(self, birth, survival):
        """
        Sets the birth and survival rules.
        """
        self.rules['birth'] = birth
        self.rules['survival'] = survival
        self.update()

    def toggle_gridlines(self, show):
        """
        Toggles the visibility of gridlines.
        """
        self.show_gridlines = show
        self.update()

    def resize_grid(self, new_rows, new_cols):
        """
        Resizes the grid to new dimensions.
        """
        new_grid = np.zeros((new_rows, new_cols), dtype=bool)
        min_rows = min(self.rows, new_rows)
        min_cols = min(self.cols, new_cols)
        new_grid[:min_rows, :min_cols] = self.grid[:min_rows, :min_cols]
        self.rows, self.cols = new_rows, new_cols
        self.grid = new_grid
        self.setFixedSize(self.cols * self.cell_size, self.rows * self.cell_size)
        self.update()

    def paintEvent(self, event):
        """
        Handles the painting of the grid.
        """
        painter = QPainter(self)
        for row in range(self.rows):
            for col in range(self.cols):
                rect_x = col * self.cell_size
                rect_y = row * self.cell_size
                if self.grid[row, col]:
                    color = self.rule_colors.get('default', QColor(0, 255, 0))
                    painter.setBrush(QBrush(color))
                else:
                    color = self.rule_colors.get('dead', QColor(255, 255, 255))
                    painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.black) if self.show_gridlines else Qt.NoPen)
                painter.drawRect(rect_x, rect_y, self.cell_size, self.cell_size)

    def mousePressEvent(self, event):
        """
        Toggles the state of the clicked cell.
        """
        x = event.x() // self.cell_size
        y = event.y() // self.cell_size
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.grid[y, x] = not self.grid[y, x]
            self.update()

    def update_grid(self):
        """
        Updates the grid based on the current rules.
        """
        new_grid = np.copy(self.grid)
        for row in range(self.rows):
            for col in range(self.cols):
                # Count alive neighbors
                neighbors = self.count_alive_neighbors(row, col)
                if self.grid[row, col]:
                    if neighbors not in self.rules['survival']:
                        new_grid[row, col] = False
                else:
                    if neighbors in self.rules['birth']:
                        new_grid[row, col] = True
        self.grid = new_grid
        self.update()

    def count_alive_neighbors(self, row, col):
        """
        Counts the number of alive neighbors for a given cell.
        """
        count = 0
        for i in range(max(0, row - 1), min(self.rows, row + 2)):
            for j in range(max(0, col - 1), min(self.cols, col + 2)):
                if (i != row or j != col) and self.grid[i, j]:
                    count += 1
        return count

    def clear_grid(self):
        """
        Clears the grid, setting all cells to dead.
        """
        self.grid = np.zeros((self.rows, self.cols), dtype=bool)
        self.update()


class SoundManager:
    """
    Manages sound synthesis based on the grid state.
    """

    def __init__(self, grid: Grid):
        self.grid = grid
        self.server = Server().boot()
        self.server.start()
        self.frequency_range = (200, 1000)  # (min_freq, max_freq)
        self.amplitude = 0.5
        self.waveform = 'Sine'
        self.smooth_transitions = True
        self.oscillators = {}  # key: (row, col), value: oscillator object
        self.envelopes = {}
        self.initialize_sound_parameters()

    def initialize_sound_parameters(self):
        """
        Initializes sound parameters based on default settings.
        """
        self.server.setMidi()

    def set_frequency_range(self, min_freq, max_freq):
        self.frequency_range = (min_freq, max_freq)
        self.update_all_frequencies()

    def set_amplitude(self, amplitude):
        self.amplitude = amplitude
        for osc in self.oscillators.values():
            osc.setMul(self.amplitude)

    def set_waveform(self, waveform_type):
        self.waveform = waveform_type
        self.update_all_waveforms()

    def set_smooth_transitions(self, smooth):
        self.smooth_transitions = smooth

    def calculate_frequency(self, row, col):
        """
        Maps a cell's position to a frequency within the specified range.
        """
        freq = self.frequency_range[0] + (self.frequency_range[1] - self.frequency_range[0]) * (col / self.grid.cols)
        freq += (self.frequency_range[1] - self.frequency_range[0]) * (row / self.grid.rows) * 0.5
        return freq

    def get_waveform_class(self, waveform_type):
        """
        Returns the Pyo oscillator class based on the waveform type.
        """
        return {
            'Sine': Sine,
            'Square': Square,
            'Sawtooth': Saw,
            'Triangle': Tri
        }.get(waveform_type, Sine)

    def play_sound(self, row, col):
        """
        Starts playing a sound for the specified cell.
        """
        key = (row, col)
        if key in self.oscillators:
            return  # Sound already playing

        freq = self.calculate_frequency(row, col)
        waveform_class = self.get_waveform_class(self.waveform)
        osc = waveform_class(freq=freq, mul=0).out()
        if self.smooth_transitions:
            env = Fader(fadein=0.5, fadeout=0.5, dur=0, mul=self.amplitude).play()
            osc.mul = env
            self.envelopes[key] = env
        else:
            osc.setMul(self.amplitude)
        self.oscillators[key] = osc

    def stop_sound(self, row, col):
        """
        Stops the sound for the specified cell.
        """
        key = (row, col)
        if key in self.oscillators:
            if self.smooth_transitions and key in self.envelopes:
                self.envelopes[key].stop()
            self.oscillators[key].stop()
            del self.oscillators[key]
            if key in self.envelopes:
                del self.envelopes[key]

    def update_sounds(self, previous_grid, current_grid):
        """
        Updates the sounds based on grid changes.
        """
        for row in range(self.grid.rows):
            for col in range(self.grid.cols):
                was_alive = previous_grid[row, col]
                is_alive = current_grid[row, col]
                if not was_alive and is_alive:
                    self.play_sound(row, col)
                elif was_alive and not is_alive:
                    self.stop_sound(row, col)

    def update_all_frequencies(self):
        """
        Updates frequencies for all active oscillators.
        """
        for (row, col), osc in self.oscillators.items():
            freq = self.calculate_frequency(row, col)
            osc.freq = freq

    def update_all_waveforms(self):
        """
        Updates waveforms for all active oscillators.
        """
        # Note: Changing waveform type on-the-fly is complex in Pyo and may require restarting oscillators
        # For simplicity, this function stops all oscillators and restarts them with the new waveform
        active_keys = list(self.oscillators.keys())
        for key in active_keys:
            row, col = key
            self.stop_sound(row, col)
            self.play_sound(row, col)

    def shutdown(self):
        """
        Shuts down the sound server.
        """
        self.server.stop()


class MainWindow(QMainWindow):
    """
    Main application window.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Sound of Life")
        self.grid_widget = Grid(rows=20, cols=20, cell_size=20)
        self.sound_manager = SoundManager(self.grid_widget)
        self.previous_grid = np.copy(self.grid_widget.grid)
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.simulation_running = False

    def init_ui(self):
        """
        Initializes the user interface.
        """
        main_layout = QHBoxLayout()

        # Left side: Grid display
        main_layout.addWidget(self.grid_widget)

        # Right side: Control panels
        control_panel = QVBoxLayout()

        # Simulation Controls
        sim_controls = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_simulation)
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_simulation)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_simulation)
        self.next_button = QPushButton("Next Generation")
        self.next_button.clicked.connect(self.next_generation)
        sim_controls.addWidget(self.play_button)
        sim_controls.addWidget(self.pause_button)
        sim_controls.addWidget(self.stop_button)
        sim_controls.addWidget(self.next_button)
        control_panel.addLayout(sim_controls)

        # Simulation Speed Slider
        speed_layout = QHBoxLayout()
        speed_label = QLabel("Simulation Speed:")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self.change_speed)
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider)
        control_panel.addLayout(speed_layout)

        # Rule Selection
        rule_layout = QHBoxLayout()
        rule_label = QLabel("Rule Set:")
        self.rule_combo = QComboBox()
        self.rule_combo.addItems([
            "B3/S23 (Conway)",
            "B36/S23 (HighLife)",
            "B2/S (Seeds)",
            "B3678/S34678 (Day & Night)",
            "B1357/S1357 (Replicator)",
            "Custom Rules"
        ])
        self.rule_combo.currentIndexChanged.connect(self.change_rule)
        rule_layout.addWidget(rule_label)
        rule_layout.addWidget(self.rule_combo)
        control_panel.addLayout(rule_layout)

        # Custom Rule Editor
        self.custom_rule_input = QLineEdit()
        self.custom_rule_input.setPlaceholderText("Enter custom rules e.g., B4/S34")
        self.custom_rule_input.returnPressed.connect(self.apply_custom_rule)
        control_panel.addWidget(self.custom_rule_input)

        # Grid Size Slider
        grid_size_layout = QHBoxLayout()
        grid_size_label = QLabel("Grid Size:")
        self.grid_size_slider = QSlider(Qt.Horizontal)
        self.grid_size_slider.setMinimum(10)
        self.grid_size_slider.setMaximum(100)
        self.grid_size_slider.setValue(20)
        self.grid_size_slider.valueChanged.connect(self.change_grid_size)
        grid_size_layout.addWidget(grid_size_label)
        grid_size_layout.addWidget(self.grid_size_slider)
        control_panel.addLayout(grid_size_layout)

        # Cell Color Customization
        color_layout = QHBoxLayout()
        live_color_label = QLabel("Live Cell Color:")
        self.live_color_button = QPushButton()
        self.live_color_button.setStyleSheet("background-color: green")
        self.live_color_button.clicked.connect(self.change_live_color)
        dead_color_label = QLabel("Dead Cell Color:")
        self.dead_color_button = QPushButton()
        self.dead_color_button.setStyleSheet("background-color: white")
        self.dead_color_button.clicked.connect(self.change_dead_color)
        color_layout.addWidget(live_color_label)
        color_layout.addWidget(self.live_color_button)
        color_layout.addWidget(dead_color_label)
        color_layout.addWidget(self.dead_color_button)
        control_panel.addLayout(color_layout)

        # Gridlines Toggle
        gridline_layout = QHBoxLayout()
        self.gridline_checkbox = QCheckBox("Show Gridlines")
        self.gridline_checkbox.setChecked(True)
        self.gridline_checkbox.stateChanged.connect(self.toggle_gridlines)
        gridline_layout.addWidget(self.gridline_checkbox)
        control_panel.addLayout(gridline_layout)

        # Sound Customization
        sound_layout = QVBoxLayout()
        sound_label = QLabel("Sound Customization:")
        sound_layout.addWidget(sound_label)

        # Sound Mode
        sound_mode_layout = QHBoxLayout()
        sound_mode_label = QLabel("Sound Mode:")
        self.sound_mode_combo = QComboBox()
        self.sound_mode_combo.addItems([
            "Grid Mapping Mode",
            "Event-Based Sound Mode"
        ])
        self.sound_mode_combo.currentIndexChanged.connect(self.change_sound_mode)
        sound_mode_layout.addWidget(sound_mode_label)
        sound_mode_layout.addWidget(self.sound_mode_combo)
        sound_layout.addLayout(sound_mode_layout)

        # Frequency Range Slider
        freq_layout = QHBoxLayout()
        freq_label = QLabel("Frequency Range:")
        self.freq_slider = QSlider(Qt.Horizontal)
        self.freq_slider.setMinimum(100)
        self.freq_slider.setMaximum(2000)
        self.freq_slider.setValue(1000)
        self.freq_slider.valueChanged.connect(self.change_frequency_range)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_slider)
        sound_layout.addLayout(freq_layout)

        # Amplitude Slider
        amp_layout = QHBoxLayout()
        amp_label = QLabel("Amplitude:")
        self.amp_slider = QSlider(Qt.Horizontal)
        self.amp_slider.setMinimum(0)
        self.amp_slider.setMaximum(100)
        self.amp_slider.setValue(50)
        self.amp_slider.valueChanged.connect(self.change_amplitude)
        amp_layout.addWidget(amp_label)
        amp_layout.addWidget(self.amp_slider)
        sound_layout.addLayout(amp_layout)

        # Waveform Selection
        waveform_layout = QHBoxLayout()
        waveform_label = QLabel("Waveform Type:")
        self.waveform_combo = QComboBox()
        self.waveform_combo.addItems(["Sine", "Square", "Sawtooth", "Triangle"])
        self.waveform_combo.currentIndexChanged.connect(self.change_waveform)
        waveform_layout.addWidget(waveform_label)
        waveform_layout.addWidget(self.waveform_combo)
        sound_layout.addLayout(waveform_layout)

        # Smooth Transitions Toggle
        self.transition_checkbox = QCheckBox("Smooth Transitions")
        self.transition_checkbox.setChecked(True)
        self.transition_checkbox.stateChanged.connect(self.toggle_transitions)
        sound_layout.addWidget(self.transition_checkbox)

        control_panel.addLayout(sound_layout)

        # Preset Management
        preset_layout = QHBoxLayout()
        self.save_preset_button = QPushButton("Save Preset")
        self.save_preset_button.clicked.connect(self.save_preset)
        self.load_preset_button = QPushButton("Load Preset")
        self.load_preset_button.clicked.connect(self.load_preset)
        preset_layout.addWidget(self.save_preset_button)
        preset_layout.addWidget(self.load_preset_button)
        control_panel.addLayout(preset_layout)

        # Audio Exporting
        export_layout = QHBoxLayout()
        self.export_button = QPushButton("Export Audio")
        self.export_button.clicked.connect(self.export_audio)
        export_layout.addWidget(self.export_button)
        control_panel.addLayout(export_layout)

        # Add control panel to main layout
        main_layout.addLayout(control_panel)

        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def play_simulation(self):
        """
        Starts the simulation.
        """
        if not self.simulation_running:
            self.timer.start(500 // self.speed_slider.value())  # Interval based on speed
            self.simulation_running = True

    def pause_simulation(self):
        """
        Pauses the simulation.
        """
        if self.simulation_running:
            self.timer.stop()
            self.simulation_running = False

    def stop_simulation(self):
        """
        Stops the simulation and clears the grid.
        """
        self.pause_simulation()
        self.grid_widget.clear_grid()
        self.sound_manager.oscillators.clear()
        self.sound_manager.shutdown()
        self.sound_manager = SoundManager(self.grid_widget)
        self.previous_grid = np.copy(self.grid_widget.grid)

    def next_generation(self):
        """
        Advances the simulation by one generation.
        """
        self.grid_widget.update_grid()
        self.sound_manager.update_sounds(self.previous_grid, self.grid_widget.grid)
        self.previous_grid = np.copy(self.grid_widget.grid)

    def change_speed(self):
        """
        Changes the simulation speed based on the slider value.
        """
        if self.simulation_running:
            self.timer.setInterval(500 // self.speed_slider.value())

    def change_rule(self):
        """
        Changes the simulation rules based on the dropdown selection.
        """
        rule = self.rule_combo.currentText()
        if rule == "B3/S23 (Conway)":
            self.grid_widget.set_rules(birth=[3], survival=[2, 3])
        elif rule == "B36/S23 (HighLife)":
            self.grid_widget.set_rules(birth=[3, 6], survival=[2, 3])
        elif rule == "B2/S (Seeds)":
            self.grid_widget.set_rules(birth=[2], survival=[])
        elif rule == "B3678/S34678 (Day & Night)":
            self.grid_widget.set_rules(birth=[3, 6, 7, 8], survival=[3, 4, 6, 7, 8])
        elif rule == "B1357/S1357 (Replicator)":
            self.grid_widget.set_rules(birth=[1, 3, 5, 7], survival=[1, 3, 5, 7])
        elif rule == "Custom Rules":
            # Enable custom rule input
            self.custom_rule_input.setEnabled(True)
        else:
            self.grid_widget.set_rules(birth=[3], survival=[2, 3])

    def apply_custom_rule(self):
        """
        Applies custom rules input by the user.
        """
        rule_str = self.custom_rule_input.text()
        try:
            birth_str, survival_str = rule_str.split('/')
            birth = [int(n) for n in birth_str.replace('B', '').split(',')]
            survival = [int(n) for n in survival_str.replace('S', '').split(',')]
            self.grid_widget.set_rules(birth=birth, survival=survival)
            QMessageBox.information(self, "Success", f"Custom rules applied: B{','.join(map(str, birth))}/S{','.join(map(str, survival))}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Invalid rule format. Please use Bx/Sy format.\nError: {str(e)}")

    def change_grid_size(self):
        """
        Changes the grid size based on the slider value.
        """
        size = self.grid_size_slider.value()
        self.grid_widget.resize_grid(rows=size, cols=size)

    def change_live_color(self):
        """
        Changes the color of live cells.
        """
        color = QColorDialog.getColor()
        if color.isValid():
            self.grid_widget.rule_colors['default'] = color
            self.grid_widget.update()

    def change_dead_color(self):
        """
        Changes the color of dead cells.
        """
        color = QColorDialog.getColor()
        if color.isValid():
            self.grid_widget.rule_colors['dead'] = color
            self.grid_widget.update()

    def toggle_gridlines(self, state):
        """
        Toggles gridline visibility.
        """
        self.grid_widget.toggle_gridlines(state == Qt.Checked)

    def change_sound_mode(self):
        """
        Changes the sound generation mode.
        """
        mode = self.sound_mode_combo.currentText()
        # Future implementation for different sound modes
        QMessageBox.information(self, "Info", f"Sound Mode changed to: {mode}")

    def change_frequency_range(self):
        """
        Changes the frequency range based on the slider value.
        """
        freq = self.freq_slider.value()
        self.sound_manager.set_frequency_range(200, freq)

    def change_amplitude(self):
        """
        Changes the amplitude based on the slider value.
        """
        amp = self.amp_slider.value() / 100.0
        self.sound_manager.set_amplitude(amp)

    def change_waveform(self):
        """
        Changes the waveform type based on the dropdown selection.
        """
        waveform = self.waveform_combo.currentText()
        self.sound_manager.set_waveform(waveform)

    def toggle_transitions(self, state):
        """
        Toggles smooth transitions for sounds.
        """
        smooth = state == Qt.Checked
        self.sound_manager.set_smooth_transitions(smooth)

    def save_preset(self):
        """
        Saves the current configuration as a preset.
        """
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Preset", "", "JSON Files (*.json)", options=options)
        if file_path:
            preset = {
                'rules': self.grid_widget.rules,
                'grid_size': {'rows': self.grid_widget.rows, 'cols': self.grid_widget.cols},
                'live_color': self.grid_widget.rule_colors.get('default', '#00FF00').name(),
                'dead_color': self.grid_widget.rule_colors.get('dead', '#FFFFFF').name(),
                'sound_mode': self.sound_mode_combo.currentText(),
                'frequency_range': self.sound_manager.frequency_range,
                'amplitude': self.sound_manager.amplitude,
                'waveform': self.waveform_combo.currentText(),
                'smooth_transitions': self.transition_checkbox.isChecked()
            }
            try:
                with open(file_path, 'w') as f:
                    json.dump(preset, f, indent=4)
                QMessageBox.information(self, "Success", "Preset saved successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save preset.\nError: {str(e)}")

    def load_preset(self):
        """
        Loads a preset from a file.
        """
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "JSON Files (*.json)", options=options)
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    preset = json.load(f)
                # Apply rules
                rules = preset.get('rules', {'birth': [3], 'survival': [2, 3]})
                self.grid_widget.set_rules(birth=rules['birth'], survival=rules['survival'])
                # Apply grid size
                grid_size = preset.get('grid_size', {'rows': 20, 'cols': 20})
                self.grid_size_slider.setValue(grid_size['rows'])
                self.grid_widget.resize_grid(rows=grid_size['rows'], cols=grid_size['cols'])
                # Apply colors
                live_color = QColor(preset.get('live_color', '#00FF00'))
                dead_color = QColor(preset.get('dead_color', '#FFFFFF'))
                self.grid_widget.rule_colors['default'] = live_color
                self.grid_widget.rule_colors['dead'] = dead_color
                self.grid_widget.update()
                self.live_color_button.setStyleSheet(f"background-color: {live_color.name()}")
                self.dead_color_button.setStyleSheet(f"background-color: {dead_color.name()}")
                # Apply sound settings
                self.sound_mode_combo.setCurrentText(preset.get('sound_mode', 'Grid Mapping Mode'))
                freq_range = preset.get('frequency_range', (200, 1000))
                self.freq_slider.setValue(freq_range[1])
                self.sound_manager.set_frequency_range(*freq_range)
                self.amp_slider.setValue(int(preset.get('amplitude', 0.5) * 100))
                self.sound_manager.set_amplitude(preset.get('amplitude', 0.5))
                self.waveform_combo.setCurrentText(preset.get('waveform', 'Sine'))
                self.sound_manager.set_waveform(preset.get('waveform', 'Sine'))
                self.transition_checkbox.setChecked(preset.get('smooth_transitions', True))
                self.sound_manager.set_smooth_transitions(preset.get('smooth_transitions', True))
                QMessageBox.information(self, "Success", "Preset loaded successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load preset.\nError: {str(e)}")

    def export_audio(self):
        """
        Exports the current soundscape as an audio file.
        """
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Audio", "", "WAV Files (*.wav)", options=options)
        if file_path:
            try:
                rec = Record(self.sound_manager.server, filename=file_path, fileformat=0).play()
                QMessageBox.information(self, "Exporting", "Recording started. Click OK to stop and save the audio.")
                # Stop recording after user clicks OK
                self.sound_manager.server.rec.stop()
                QMessageBox.information(self, "Success", "Audio exported successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to export audio.\nError: {str(e)}")

    def update_simulation(self):
        """
        Updates the simulation at each timer tick.
        """
        self.next_generation()

    def closeEvent(self, event):
        """
        Handles the window close event to ensure proper shutdown.
        """
        self.sound_manager.shutdown()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
