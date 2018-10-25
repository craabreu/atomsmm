"""
.. module:: integrators
   :platform: Unix, Windows
   :synopsis: a module for defining integrator classes.

.. moduleauthor:: Charlles R. A. Abreu <abreu@eq.ufrj.br>

"""

import math
import random
import re

import openmmtools.integrators as openmmtools
from simtk import openmm
from simtk import unit
from sympy import Symbol
from sympy.parsing.sympy_parser import parse_expr

import atomsmm.propagators as propagators
from atomsmm.propagators import Propagator as DummyPropagator
from atomsmm.utils import InputError


class Integrator(openmm.CustomIntegrator, openmmtools.PrettyPrintableIntegrator):
    def __init__(self, stepSize):
        super(Integrator, self).__init__(stepSize)
        self.addGlobalVariable("mvv", 0.0)
        self.obsoleteKinetic = True
        self.forceFinder = re.compile("f[0-9]*")
        self.obsoleteContextState = True

    def __str__(self):
        return self.pretty_format()

    def _required_variables(self, variable, expression):
        """
        Returns a list of strings containting the names of all global and per-dof variables
        required in an OpenMM CustomIntegrator operation.

        """
        definitions = ("{}={}".format(variable, expression)).split(";")
        names = set()
        symbols = set()
        for definition in definitions:
            name, expr = definition.split("=")
            names.add(Symbol(name.strip()))
            symbols |= parse_expr(expr.replace("^", "**")).free_symbols
        return list(str(element) for element in (symbols - names))

    def _checkUpdate(self, variable, expression):
        requirements = self._required_variables(variable, expression)
        if self.obsoleteKinetic and "mvv" in requirements:
            super(Integrator, self).addComputeSum("mvv", "m*v*v")
            self.obsoleteKinetic = False
        if self.obsoleteContextState and any(self.forceFinder.match(s) for s in requirements):
            super(Integrator, self).addUpdateContextState()
            self.obsoleteContextState = False

    def addUpdateContextState(self):
        if self.obsoleteContextState:
            super(Integrator, self).addUpdateContextState()
            self.obsoleteContextState = False

    def addComputeGlobal(self, variable, expression):
        if variable == "mvv":
            raise InputError("Cannot assign value to global variable mvv")
        self._checkUpdate(variable, expression)
        super(Integrator, self).addComputeGlobal(variable, expression)

    def addComputePerDof(self, variable, expression):
        self._checkUpdate(variable, expression)
        super(Integrator, self).addComputePerDof(variable, expression)
        if variable == "v":
            self.obsoleteKinetic = True

    def initializeVelocities(self, context, temperature):
        energy_unit = unit.dalton*(unit.nanometer/unit.picosecond)**2
        kT = unit.BOLTZMANN_CONSTANT_kB*unit.AVOGADRO_CONSTANT_NA*temperature/energy_unit
        system = context.getSystem()
        N = system.getNumParticles()
        masses = self.masses = [system.getParticleMass(i)/unit.dalton for i in range(N)]
        velocities = list()
        for m in masses:
            sigma = math.sqrt(kT/m)
            v = sigma*openmm.Vec3(random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))
            velocities.append(v)
        mtotal = sum(masses)
        ptotal = sum([m*v for (m, v) in zip(masses, velocities)], openmm.Vec3(0.0, 0.0, 0.0))
        vcm = ptotal/mtotal
        for i in range(len(velocities)):
            velocities[i] -= vcm
        twoK = sum(m*(v[0]**2 + v[1]**2 + v[2]**2) for (m, v) in zip(masses, velocities))
        factor = math.sqrt(3*N*kT/twoK)
        for i in range(len(velocities)):
            velocities[i] *= factor
        context.setVelocities(velocities)

    def setRandomNumberSeed(self, seed):
        super(Integrator, self).setRandomNumberSeed(seed)
        random.seed(seed)


class GlobalThermostatIntegrator(Integrator):
    """
    This class extends OpenMM's CustomIntegrator_ class in order to facilitate the construction
    of NVT integrators which include a global thermostat, that is, one that acts equally and
    simultaneously on all degrees of freedom of the system. In this case, a complete NVT step is
    split as:

    .. math::
        e^{\\delta t \\, iL_\\mathrm{NVT}} = e^{\\frac{1}{2} \\delta t \\, iL_\\mathrm{T}}
                                             e^{\\delta t \\, iL_\\mathrm{NVE}}
                                             e^{\\frac{1}{2} \\delta t \\, iL_\\mathrm{T}}

    The propagator :math:`e^{\\delta t \\, iL_\\mathrm{NVE}}` is a Hamiltonian


    corresponds to a Hamiltonian  :math:`iL_\\mathrm{T}`

    .. _CustomIntegrator: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.CustomIntegrator.html

    Parameters
    ----------
        stepSize : unit.Quantity
            The step size with which to integrate the system (in time unit).
        nveIntegrator : :class:`HamiltonianPropagator`
            The Hamiltonian propagator.
        thermostat : :class:`ThermostatPropagator`, optional, default=DummyPropagator()
            The thermostat propagator.
        randomSeed : int, optional, default=None
            A seed for random numbers.

    """
    def __init__(self, stepSize, nveIntegrator, thermostat=DummyPropagator()):
        super(GlobalThermostatIntegrator, self).__init__(stepSize)
        for propagator in [nveIntegrator, thermostat]:
            propagator.addVariables(self)
        thermostat.addSteps(self, 1/2)
        nveIntegrator.addSteps(self)
        thermostat.addSteps(self, 1/2)


class SIN_R_Integrator(Integrator):
    """
    This class extends OpenMM's CustomIntegrator_ class in order to facilitate the construction
    of NVT integrators which include a global thermostat, that is, one that acts equally and
    simultaneously on all degrees of freedom of the system. In this case, a complete NVT step is
    split as:

    .. math::
        e^{\\delta t \\, iL_\\mathrm{NVT}} = e^{\\frac{1}{2} \\delta t \\, iL_\\mathrm{T}}
                                             e^{\\delta t \\, iL_\\mathrm{NVE}}
                                             e^{\\frac{1}{2} \\delta t \\, iL_\\mathrm{T}}

    The propagator :math:`e^{\\delta t \\, iL_\\mathrm{NVE}}` is a Hamiltonian


    corresponds to a Hamiltonian  :math:`iL_\\mathrm{T}`

    .. _CustomIntegrator: http://docs.openmm.org/latest/api-python/generated/simtk.openmm.openmm.CustomIntegrator.html

    Parameters
    ----------
        stepSize : unit.Quantity
            The step size with which to integrate the system (in time unit).
        nveIntegrator : :class:`HamiltonianPropagator`
            The Hamiltonian propagator.
        thermostat : :class:`ThermostatPropagator`, optional, default=DummyPropagator()
            The thermostat propagator.
        randomSeed : int, optional, default=None
            A seed for random numbers.

    """
    def __init__(self, stepSize, loops, temperature, timeScale, frictionConstant=None):
        super(SIN_R_Integrator, self).__init__(stepSize)
        gamma = 1/timeScale if frictionConstant is None else frictionConstant
        isoF = propagators.SIN_R_Isokinetic_F_Propagator(temperature)
        isoN = propagators.SIN_R_Isokinetic_N_Propagator(temperature, timeScale)
        OU = propagators.SIN_R_OrnsteinUhlenbeckPropagator(temperature, timeScale, gamma, forced=True)
        v2boost = propagators.SIN_R_ThermostatBoostPropagator(temperature, timeScale)
        propagator = propagators.RespaPropagator(loops,
                                                core=propagators.TrotterSuzukiPropagator(OU, isoN),
                                                # crust=propagators.SuzukiYoshidaPropagator(propagators.TrotterSuzukiPropagator(isoN, v2boost)),
                                                #  crust=propagators.TrotterSuzukiPropagator(isoN, v2boost),
                                                 boost=isoF)


        translation = propagators.TranslationPropagator(constrained=False)
        propagator = OU
        propagator = propagators.TrotterSuzukiPropagator(propagator, translation)
        propagator = propagators.TrotterSuzukiPropagator(propagator, isoF)
        propagator = propagators.TrotterSuzukiPropagator(propagator, isoN)


        propagator.addVariables(self)
        propagator.addSteps(self)

    def initializeVelocities(self, context, temperature):
        super().initializeVelocities(context, temperature/4)
        energy_unit = unit.dalton*(unit.nanometer/unit.picosecond)**2
        kT = unit.BOLTZMANN_CONSTANT_kB*unit.AVOGADRO_CONSTANT_NA*temperature/energy_unit
        state = context.getState(getVelocities=True)
        v = state.getVelocities()*unit.picosecond/unit.nanometer
        Q1 = self.getGlobalVariableByName("Q1")
        Q2 = self.getGlobalVariableByName("Q2")
        v1 = self.getPerDofVariableByName("v1")
        v2 = self.getPerDofVariableByName("v2")
        sigma1 = math.sqrt(kT/Q1)
        sigma2 = math.sqrt(kT/Q2)
        for (i, m) in enumerate(self.masses):
            v1[i] = sigma1*openmm.Vec3(random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))
            v2[i] = sigma2*openmm.Vec3(random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))
            factor = [math.sqrt(kT/(m*x**2 + 0.5*Q1*y**2)) for (x, y) in zip(v[i], v1[i])]
            v[i] = openmm.Vec3(*[f*x for (f, x) in zip(factor, v[i])])
            v1[i] = openmm.Vec3(*[f*x for (f, x) in zip(factor, v1[i])])
        context.setVelocities(v)
        self.setPerDofVariableByName("v1", v1)
        self.setPerDofVariableByName("v2", v2)

    def check(self, context):
        Q1 = self.getGlobalVariableByName("Q1")
        v1s = self.getPerDofVariableByName("v1")
        state = context.getState(getVelocities=True)
        vs = state.getVelocities()*unit.picosecond/unit.nanometer
        for (m, v, v1) in zip(self.masses, vs, v1s):
            print([m*x**2 + 0.5*Q1*y**2 for (x, y) in zip(v, v1)])
