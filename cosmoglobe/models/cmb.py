from .skycomponent import SkyComponent
from ..chaintools import get_alms
import astropy.units as u
import astropy.constants as const
import healpy as hp 
import numpy as np

# Initializing common astrophy units
h = const.h
c = const.c
k_B = const.k_B
T_0 = 2.7255*u.K


class CMB(SkyComponent):
    """
    Parent class for all Synchrotron models.
    """
    comp_label = 'cmb'

    def __init__(self, data, model_params):
        super().__init__(data, model_params)


class BlackBody(CMB):
    """
    Model for CMB emission.

    """    
    model_label = 'cmb'

    def __init__(self, data, model_params):
        super().__init__(data, model_params)

    @u.quantity_input(nu=u.Hz)
    def get_emission(self, nu):
        """
        Returns the model emission of at a given frequency in units of K_RJ.

        Parameters
        ----------
        nu : 'astropy.units.quantity.Quantity'
            Frequency at which to evaluate the model. 

        Returns
        -------
        emission : 'astropy.units.quantity.Quantity'
            Model emission at given frequency in units of K_RJ.

        """
        emission = self.compute_emission(nu)

        return emission


    @u.quantity_input(nu=u.Hz)
    def compute_emission(self, nu):
        """
        Computes the simulated emission CMB of at a given frequency .

        Parameters
        ----------
        nu : 'astropy.units.quantity.Quantity'
            Frequency at which to evaluate the CMB radiation.    
            
        Returns
        -------
        emission : 'astropy.units.quantity.Quantity'
            CMB emission at a given frequency.

        """
        emission = self.amp.copy()

        return self.KCMB_to_KRJ(emission, nu)