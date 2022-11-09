from .backend import SimulationBackend

from saveviewer.format import *

import struct
import io
import os

import importlib

class CellModeller4Backend(SimulationBackend):
	def __init__(self, params):
		super().__init__(params)

		self.params = params
		self.simulation = None
	
	def initialize(self):
		# We cannot import CellModeller the traditional way because we want the users to be able to run
		# the server even if they don't have all the versions of CellModeller installed.
		module = importlib.import_module("CellModeller.Simulator")

		# Setup simulator properties
		self.simulation = module.Simulator(self.params.name, self.params.delta_time, moduleStr=self.params.source, clPlatformNum=0, clDeviceNum=0, is_gui=False, saveOutput=False)
		self.simulation.outputDirPath = self.params.sim_root_dir

		if self.simulation.moduleStr:
			self.simulation.moduleOutput = self.simulation.moduleStr
		else:
			self.simulation.moduleOutput = inspect.getsource(self.simulation.module)
	
	def step(self):
		self.simulation.step()

	def _write_step_frame(self, path):
		cell_states = self.simulation.cellStates

		writer = PackedCellWriter()
		writer.write_header(len(cell_states))

		for it in cell_states.keys():
			state = cell_states[it]

			writer.write_cell(PackedCell.from_cellmodeller4(state))

		with open(path, "wb") as out_file:
			writer.flush_to_file(out_file)

	def _write_viz_frame(self, path):
		cell_states = self.simulation.cellStates

		byte_buffer = io.BytesIO()
		byte_buffer.write(struct.pack("<i", len(cell_states)))

		for it in cell_states.keys():
			state = cell_states[it]

			color_r = int(255.0 * min(state.color[0], 1.0))
			color_g = int(255.0 * min(state.color[1], 1.0))
			color_b = int(255.0 * min(state.color[2], 1.0))
			packed_color = 0xFF000000 | (color_b << 16) | (color_g << 8) | color_r

			# The length is computed differenty in CellModeller4 and CellModeller5. The front-end 
			# expects that the length will be calculated based on how its done in CM5.
			final_length = state.length + 1.0 - 2.0 * state.radius
			final_length = 0 if final_length <= 0 else final_length

			byte_buffer.write(struct.pack("<fff", state.pos[0], state.pos[2], state.pos[1]))
			byte_buffer.write(struct.pack("<fff", state.dir[0], state.dir[2], state.dir[1]))
			byte_buffer.write(struct.pack("<ffI", final_length, state.radius, packed_color))

		for it in cell_states.keys():
			state = cell_states[it]

			byte_buffer.write(struct.pack("<Q", int(state.id)))

		with open(path, "wb") as out_file:
			out_file.write(self.compress_step(byte_buffer.getbuffer()))

	def write_step_files(self):
		base_file_name = "step-%05i" % self.simulation.stepNum

		pickle_path = os.path.join(self.simulation.outputDirPath, f"{base_file_name}.cm5_step")
		viz_bin_path = os.path.join(self.params.cache_dir, f"{base_file_name}.cm5_viz")

		pickle_file_relative = os.path.join(".", f"{base_file_name}.cm5_step")
		cached_file_relative = os.path.join(self.params.cache_relative_prefix, f"{base_file_name}.cm5_viz")

		# Write pickle
		self._write_step_frame(pickle_path)

		# Write binary finle
		self._write_viz_frame(viz_bin_path)

		return pickle_file_relative, cached_file_relative

	def shutdown(self):
		del self.simulation
		self.simulation = None