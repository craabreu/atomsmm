from simtk.openmm.app.statedatareporter import StateDataReporter
import time
class shortName(StateDataReporter):
	
	def _constructHeaders(self):

			headers = []
			if self._progress:
				headers.append('%')
			if self._step:
				headers.append('Step')
			if self._time:
				headers.append('t')
			if self._potentialEnergy:
				headers.append('PE')
			if self._kineticEnergy:
				headers.append('KE')
			if self._totalEnergy:
				headers.append('TotE')
			if self._temperature:
				headers.append('T')
			if self._volume:
				headers.append('BoxV ')
			if self._density:
				headers.append('D')
			if self._speed:
				headers.append('Sp')
			if self._elapsedTime:
				headers.append('Elt')
			if self._remainingTime:
				headers.append('tRem')
			return headers

	def report(self, simulation, state):

			if not self._hasInitialized:
				self._initializeConstants(simulation)
				headers = self._constructHeaders()
				print('%s' % (self._separator).join(headers), file=self._out)
				try:
					self._out.flush()
				except AttributeError:
					pass
				self._initialClockTime = time.time()
				self._initialSimulationTime = state.getTime()
				self._initialSteps = simulation.currentStep
				self._hasInitialized = True

			# Check for errors.
			self._checkForErrors(simulation, state)

			# Query for the values
			values = self._constructReportValues(simulation, state)

			# Write the values.
			print(self._separator.join(str(v) for v in values), file=self._out)
			try:
				self._out.flush()
			except AttributeError:
				pass
