from .components import Component
from ..tools.exceptions import NsideError

import astropy.units as u
import healpy as hp
import numpy as np

class Model:
    """A sky model.

    This class acts as a container for the various components making up the
    sky model and provides methods to simulate the sky emission at a given
    frequency or over a bandpass.

    Args:
    -----
    components (list):
        A list of `cosmoglobe.sky.Component` objects that will be added to the
        model.
    nside (int):
        Healpix map resolution. Represents the resolution of the sky model. If
        None, nside will be set to the nside of the first inserted component.
        Default: None

    """
    def __init__(self, components=None, nside=None):
        self.nside = nside
        self.components = {}
        if components:
            for component in components:
                self._add_component(component)


    def _add_component(self, component):
        if not issubclass(component.__class__, Component):
            raise TypeError(
                f'{component} is not a subclass of cosmoglobe.sky.Component'
            )

        name = component.name
        nside = hp.get_nside(component.amp)
        if name in self.components:
            raise KeyError(f'component {name} already exists in model')
        if nside != self.nside:
            if self.nside is None:
                self.nside = nside
            else:
                raise NsideError(
                    f'component {name!r} has a reference map at NSIDE='
                    f'{nside}, but model NSIDE is set to {self.nside}'
                )

        setattr(self, name, component)
        self.components[name] = component


    def insert(self, component):
        """Insert a new component to the model.

        Args:
        -----
        component (a subclass of `cosmoglobe.sky.Component`):
            Sky component to be added to the model. Must be a subclass of 
            `cosmoglobe.sky.Component`.

        """
        self._add_component(component)


    def remove(self, name):
        """Removes a component from the model.

        Args:
        -----
        name (str):
            Component attribute name.

        """
        del self[name]


    @u.quantity_input(freq=u.Hz, bandpass=(u.Jy/u.sr, u.K, None))
    def get_emission(self, freq, bandpass=None, output_unit=u.uK):
        """Returns the full model sky emission at a single or multiple
        frequencies.

        Args:
        -----
        freq (`astropy.units.Quantity`):
            A frequency, or list of frequencies for which to evaluate the
            component emission. Must be in units of Hertz.
        bandpass (`astropy.units.Quantity`):
            Bandpass profile corresponding to the frequency list. If None, a
            delta peak in frequency is assumed at the given frequencies.
            Default: None
        output_unit (`astropy.units.Unit`):
            The desired output units of the emission. Must be signal units. 
            Default : uK

        Returns:
        --------
        (`astropy.units.Quantity`)
            Model emission at the given frequency.

        """
        if bandpass is None and freq.ndim > 0:
            return [self._get_model_emission(freq, bandpass, output_unit)
                    for freq in freq]

        return self._get_model_emission(freq, bandpass, output_unit)


    def _get_model_emission(self, freq, bandpass, output_unit):
        if self.is_polarized:
            model_emission = np.zeros((3, hp.nside2npix(self.nside)))
        else:
            model_emission = np.zeros((1, hp.nside2npix(self.nside)))
        model_emission = u.Quantity(model_emission, unit=output_unit)

        for comp in self:
            comp_emission = comp.get_emission(freq, bandpass, output_unit)
            for idx, col in enumerate(comp_emission):
                model_emission[idx] += col

        return model_emission


    def to_nside(self, new_nside):
        """ud_grades all maps in the component to a new nside.

        Args:
        -----
        new_nside (int):
            Healpix map resolution parameter.

        """
        if new_nside == self.nside:
            return
        if not hp.isnsideok(new_nside, nest=True):
            raise ValueError(f'nside: {new_nside} is not valid.')
        
        self.nside = new_nside
        for comp in self:
            comp.to_nside(new_nside)
        

    @property
    def is_polarized(self):
        """Returns True if model includes a polarized component and False 
        otherwise.
        """
        for comp in self:
            if comp.is_polarized:
                return True
        return False


    def __iter__(self):
        return iter(self.components.values())


    def __len__(self):
        return len(self.components)


    def __delitem__(self, name):
        if name not in self.components:
            raise KeyError(f'component {name} does not exist')

        delattr(self, name)
        del self.components[name]


    def __repr__(self):
        reprs = []
        for key, component in self.components.items():
            component_repr = repr(component) + '\n'
            reprs.append(f'({key}): {component_repr}')

        main_repr = f'Model('
        main_repr += '\n ' + ' '.join(reprs)
        main_repr += f'), nside={self.nside}'

        return main_repr