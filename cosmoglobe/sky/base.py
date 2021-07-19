from cosmoglobe.utils import utils
import cosmoglobe.utils.bandpass as bp

from abc import ABC, abstractmethod
from tqdm import tqdm
from typing import Dict
from sys import exit
import astropy.units as u
import healpy as hp
import numpy as np
import sys
import warnings


class _Component(ABC):
    """Abstract base class for a sky component"""

    amp: u.Quantity
    freq_ref: u.Quantity
    spectral_parameters: Dict[str, u.Quantity]

    def __init__(self, amp, freq_ref, **spectral_parameters):
        """Initializes a sky component."""
        
        self.amp = amp
        self.freq_ref = self._reshape_freq_ref(freq_ref)
        self.spectral_parameters = spectral_parameters
    
    @abstractmethod
    def _smooth_emission(self, emission, fwhm):
        """Smooths the component emission given a beam FWHM."""

    @u.quantity_input(
        freqs=u.Hz, 
        bandpass=(u.Jy/u.sr, u.K, None), 
        fwhm=(u.rad, u.deg, u.arcmin),
    )
    def __call__(
        self, freqs, bandpass=None, fwhm=0.0 * u.rad, output_unit=u.uK
    ):
        r"""Simulates the component sky emission. 

        This method is the main use case of component object. It 
        simulates the sky emission a single frequency :math:`\nu` or 
        integrated over a bandpass :math:`\tau`.

        Parameters
        ----------
        freqs : `astropy.units.Quantity`
            A frequency, or a list of frequencies for which to evaluate 
            the sky emission.
        bandpass : `astropy.units.Quantity`, optional
            Bandpass profile corresponding to the frequencies. Default is 
            None. If `bandpass` is None and `freqs` is a single frequency,
            a delta peak is assumed (unless `freqs` is a list of 
            frequencies, for which a top-hat bandpass is used to perform  
            bandpass integration instead).
        fwhm : `astropy.units.Quantity`, optional
            The full width half max parameter of the Gaussian (Default is 
            0.0, which indicates no smoothing of output maps).
        output_unit : `astropy.units.UnitBase`, optional
            The desired output units of the emission (By default the 
            output unit of the model is always in 
            :math:`\mathrm{\mu K_{RJ}}`.

        Returns
        -------
        `astropy.units.Quantity`
            The component emission.

        Notes
        -----
        This function computes the following expression for a given 
        component:
        
        .. math::

            \boldsymbol{s}_i(\nu) = \boldsymbol{a}
            _i(\nu_{0,i}) \; f_{i}
            (\nu),

        where :math:`\boldsymbol{a}_i` is the amplitude map of 
        component :math:`i` at some reference frequency 
        :math:`\nu_{0,i}`, and :math:`f_i(\nu)` is the 
        scaling factor given by the SED of the component.

        See Also
        --------
        Model.__call__
            See for explicit expressions for :math:`\boldsymbol{s}_i(\nu)`.

        Examples
        --------
        Simulated dust emission at :math:`350\; \mathrm{GHz}`:

        >>> from cosmoglobe import skymodel
        >>> import astropy.units as u
        >>> model = skymodel(nside=256) 
        >>> model.dust(350*u.GHz)[0]
        [21.12408523 -0.30044442  5.8907252  ...  4.6465226   6.94981578
          8.23490773] uK

        Simulated synchrotron emission at :math:`500\; \mathrm{GHz}` 
        smoothed with a :math:`50\; '` Gaussian beam, outputed in units of 
        :math:`\mathrm{MJy} / \mathrm{sr}`:

        >>> model.synch(40*u.GHz, fwhm=50*u.arcmin, output_unit='MJy/sr')[0]
        [0.00054551 0.00053428 0.00051471 ... 0.00046559 0.00047185 0.00047065]
         MJy / sr
        """

        # If a single frequency is provided we assume emission from a delta peak
        if freqs.size == 1:
            emission = self._get_delta_emission(
                freqs, fwhm=fwhm, output_unit=output_unit
            )
        # If a list of frequencies is provided we perform bandpass integration
        else:
            emission = self._get_bandpass_emission(
                freqs, bandpass, fwhm=fwhm, output_unit=output_unit
            )

        # If a beam FWHM is provided we smooth the diffuse emission
        if fwhm != 0.0 and isinstance(self, _DiffuseComponent):
            fwhm = fwhm.to(u.rad).value
            if self._is_polarized:
                emission = u.Quantity(
                    hp.smoothing(emission, fwhm=fwhm), unit=emission.unit
                )
            else:
                emission[0] = u.Quantity(
                    hp.smoothing(emission[0], fwhm=fwhm), unit=emission.unit
                )

        return emission

    @abstractmethod
    def _get_delta_emission(self, freq, fwhm, output_unit):
        """Simulates the component emission at a delta frequency.
        
        Parameters
        ----------
        freq : `astropy.units.Quantity`
            A delta frequency.
        fwhm : `astropy.units.Quantity`
            The full width half max parameter of the Gaussian.
        output_unit : `astropy.units.UnitBase`
            The desired output unit of the emission. Must be signal units. 
            Default: None

        Returns
        -------
        emission : `astropy.units.Quantity`
            Simulated emission.
        """

    @abstractmethod
    def _get_bandpass_emission(self, freqs, bandpass, fwhm, output_unit):
        """Computes the simulated component emission over a bandpass.

        If no bandpass is passed, a top-hat bandpass is assumed.

        Parameters
        ----------
        freqs : `astropy.units.Quantity`
            Bandpass frequencies.
        bandpass : `astropy.units.Quantity`
            Bandpass profile. Default: None
        fwhm : `astropy.units.Quantity`
            The full width half max parameter of the Gaussian. Default: 0.0
        output_unit : `astropy.units.UnitBase`
            The desired output unit of the emission. Default: None

        Returns
        -------
        emission : `astropy.units.Quantity`
            Simulated emission.
        """

    def _get_bandpass_scaling(self, freqs, bandpass):
        """Returns the frequency scaling factor given a bandpass profile and a
        corresponding frequency array. 
        
        Parameters
        ----------
        freqs : `astropy.units.Quantity`
            List of frequencies.
        bandpass : `astropy.units.Quantity`
            Normalized bandpass profile.

        Returns
        -------
        bandpass_scaling : float, `numpy.ndarray`
            Frequency scaling factor given a bandpass.
        """
        
        grid = bp.get_interpolation_grid(self.spectral_parameters)

        if not grid:
        # Component does not have any spatially varying spectral parameters.
        # In this scenaraio we simply integrate the emission at each frequency 
        # weighted by the bandpass.
            freq_scaling = self._get_freq_scaling(
                freqs, self.freq_ref, **self.spectral_parameters
            )

            return np.expand_dims(
                np.trapz(freq_scaling*bandpass, freqs), axis=1
            )

        elif len(grid) == 1:
        # Component has one sptatially varying spectral parameter. In this 
        # scenario we perform a 1D-interpolation in spectral parameter space.
            return bp.interp1d(freqs, bandpass, grid, self)

        elif len(grid) == 2:    
        # Component has two sptatially varying spectral parameter. In this 
        # scenario we perform a 2D-interpolation in spectral parameter space.
            return bp.interp2d(freqs, bandpass, grid, self)

        else:
            raise NotImplementedError(
                'Bandpass integration for comps with more than two spectral '
                'parameters is not currently supported'
            )

    @staticmethod
    def _reshape_freq_ref(freq_ref):
        """Reshapes the reference frequency to a broadcastable shape."""
        if freq_ref is None:
            return
        elif freq_ref.size == 1:
            return freq_ref
        elif freq_ref.size == 2:
            return np.expand_dims(
                u.Quantity([freq_ref[0], freq_ref[1], freq_ref[1]]), axis=1
            )
        elif freq_ref.size == 3:
            return freq_ref.reshape((3,1))
        else:
            raise ValueError('Unrecognized shape.')

    @property
    def _is_polarized(self):
        """Returns True if component is polarized and False if not."""

        if self.amp.shape[0] == 3:
            return True

        return False

    def __repr__(self):
        """Representation of the component."""

        main_repr = f'{self.__class__.__name__}'
        main_repr += '('
        extra_repr = ''
        for key in self.spectral_parameters.keys():
            extra_repr += f'{key}, '
        if extra_repr:
            extra_repr = extra_repr[:-2]
        main_repr += extra_repr
        main_repr += ')'

        return main_repr


class _DiffuseComponent(_Component):
    """Abstract base class for a diffuse sky component"""

    def __init__(self, amp, freq_ref, **spectral_parameters):
        super().__init__(amp, freq_ref, **spectral_parameters)

        # Expand dimension on rank-1 arrays from from (`npix`,) to (`npix`, 1)
        # to support broadcasting with (1, `npix`) or (3, `npix`) arrays
        self.amp = amp if amp.ndim != 1 else np.expand_dims(amp, axis=0)
        self.spectral_parameters = {
            key: (np.expand_dims(value, axis=0) if value.ndim == 1 else value)
            for key, value in spectral_parameters.items()
        }

    @abstractmethod
    def _get_freq_scaling(freq, freq_ref, **spectral_parameters):
        r"""Computes the frequency scaling for a component.
        
        Parameters
        ----------
        freq : `astropy.units.Quantity`
            Frequency at which to evaluate the model.
        freq_ref : `astropy.units.Quantity`
            Reference frequencies for the components `amp` map.
        spectral_parameters : `np.ndarray`, `astropy.units.Quantity`
            The spectral parameters of the component. 
            
        Returns
        -------
        scaling : `astropy.units.Quantity`
            Frequency scaling factor with dimensionless units.
        """

    def _get_delta_emission(self, freq, fwhm=None, output_unit=u.uK):
        """See base class."""

        scaling = self._get_freq_scaling(
            freq, self.freq_ref, **self.spectral_parameters
        )
        emission = self.amp * scaling

        if output_unit is not None:
            emission = utils.emission_to_unit(emission, freq, output_unit)

        return emission

    def _get_bandpass_emission(
        self, freqs, bandpass=None, fwhm=None, output_unit=u.uK
    ):
        """See base class."""

        if bandpass is None:
            warnings.warn('No bandpass was passed. Default to top-hat bandpass')
            freqs_len = len(freqs)
            bandpass = np.ones(freqs_len)/freqs_len * u.K

        bandpass = bp.get_normalized_bandpass(bandpass, freqs)
        bandpass_coefficient = bp.get_bandpass_coefficient(
            bandpass, freqs, output_unit
        )

        bandpass_scaling = self._get_bandpass_scaling(freqs, bandpass)
        emission = self.amp * bandpass_scaling * bandpass_coefficient

        return emission

    def _smooth_emission(self, emission, fwhm):
        """Smooths the diffuse emission using hp.smoothing."""
        if fwhm == 0.0:
            return emission
        
        fwhm = fwhm.to(u.rad).value
        if self._is_polarized:
            emission = u.Quantity(
                hp.smoothing(emission, fwhm=fwhm), unit=emission.unit
            )
        else:
            emission[0] = u.Quantity(
                hp.smoothing(emission[0], fwhm=fwhm), unit=emission.unit
            )

        return emission


class _PointSourceComponent(_Component):
    """Abstract base class for a point source sky component"""

    def __init__(self, amp, freq_ref, nside, **spectral_parameters):
        self.nside = nside

        super().__init__(amp, freq_ref, **spectral_parameters)

        # Expand dimension on rank-1 arrays from from (`npix`,) to (`npix`, 1)
        # to support broadcasting with (1, `npix`) or (3, `npix`) arrays
        self.spectral_parameters = {
            key: (np.expand_dims(value, axis=0) if value.ndim == 1 else value)
            for key, value in spectral_parameters.items()
        }

    @abstractmethod
    def _get_freq_scaling(freq, freq_ref, **spectral_parameters):
        r"""Computes the frequency scaling for a component.
        
        Parameters
        ----------
        freq : `astropy.units.Quantity`
            Frequency at which to evaluate the model.
        freq_ref : `astropy.units.Quantity`
            Reference frequencies for the components `amp` map.
        spectral_parameters : `np.ndarray`, `astropy.units.Quantity`
            The spectral parameters of the component. 
            
        Returns
        -------
        scaling : `astropy.units.Quantity`
            Frequency scaling factor with dimensionless units.
        """

    def _get_delta_emission(self, freq, fwhm=0.0 * u.rad, output_unit=u.uK):
        """See base class."""

        scaling = self._get_freq_scaling(
            freq, self.freq_ref, **self.spectral_parameters
        )

        scaled_amps = self.amp * scaling
        emission = self._points_to_map(scaled_amps, fwhm=fwhm)

        if output_unit is not None:
            emission = utils.emission_to_unit(emission, freq, output_unit)

        return emission

    def _get_bandpass_emission(
        self, freqs, bandpass=None, fwhm=0.0 * u.rad, output_unit=u.uK
    ):
        """See base class."""

        if bandpass is None:
            warnings.warn('No bandpass was passed. Default to top-hat bandpass')
            freqs_len = len(freqs)
            bandpass = np.ones(freqs_len)/freqs_len * u.K

        bandpass = bp.get_normalized_bandpass(bandpass, freqs)
        bandpass_coefficient = bp.get_bandpass_coefficient(
            bandpass, freqs, output_unit
        )

        bandpass_scaling = self._get_bandpass_scaling(freqs, bandpass)
        scaled_amps = self.amp * bandpass_scaling
        emission = (
            self._points_to_map(scaled_amps, fwhm=fwhm) * bandpass_coefficient
        )

        return emission

    def _smooth_emission(self, emission, fwhm):
        """Smooths the diffuse emission using hp.smoothing."""

        return self._points_to_map(emission, fwhm=fwhm)

    def _points_to_map(
        self, amp, nside=None, fwhm=0.0 * u.rad, sigma=None, n_fwhm=2
    ):
        """Maps the cataloged point sources onto a healpix map with a truncated 
        gaussian beam. For more information, see 
         `Mitra et al. (2010) <https://arxiv.org/pdf/1005.1929.pdf>`_.

        Parameters
        ----------
        amp : `astropy.units.Quantity`
            Amplitudes of the point sources.
        nside : int
            The healpix map resolution of the output map. If component is part 
            of a sky model, we automatically select the model nside. 
            Default: None.
        fwhm : `astropy.units.Quantity`
            The full width half max parameter of the Gaussian. Default: 0.0
        sigma : float
            The sigma of the Gaussian (beam radius). Overrides fwhm. 
            Default: None
        n_fwhm : int, float
            The fwhm multiplier used in computing radial cut off r_max 
            calculated as r_max = n_fwhm * fwhm of the Gaussian.
            Default: 2.
        """

        nside = self.nside

        if amp.ndim > 1:
            amp = np.squeeze(amp)
        healpix_map = u.Quantity(
            np.zeros(hp.nside2npix(nside)), unit=amp.unit
        )
        pix_lon, pix_lat = hp.pix2ang(
            nside, np.arange(hp.nside2npix(nside)), lonlat=True
        )
        angular_coords = self.angular_coords

        fwhm = fwhm.to(u.rad)
        if sigma is None:
            sigma = fwhm / (2*np.sqrt(2*np.log(2)))

        # No smoothing nesecarry. We directly map the sources to pixels
        if sigma == 0.0:
            warnings.warn('mapping point sources to pixels without beam smoothing.')
            pixels = hp.ang2pix(nside, *angular_coords.T, lonlat=True)
            beam_area = hp.nside2pixarea(nside) * u.sr
            healpix_map[pixels] = amp

        # Apply a truncated gaussian beam to each point source
        else:
            pix_res = hp.nside2resol(nside)
            if fwhm.value < pix_res:
                raise ValueError(
                    'fwhm must be >= pixel resolution to resolve the '
                    'point sources.'
                )
            beam_area = 2 * np.pi * sigma**2
            r_max = n_fwhm * fwhm.value

            with tqdm(total=len(angular_coords), file=sys.stdout) as pbar:
                sigma = sigma.value
                beam = utils.gaussian_beam_2D
                print('Smoothing point sources')

                for idx, (lon, lat) in enumerate(angular_coords):
                    vec = hp.ang2vec(lon, lat, lonlat=True)
                    inds = hp.query_disc(nside, vec, r_max)
                    r = hp.rotator.angdist(
                        np.array(
                            [pix_lon[inds], pix_lat[inds]]), np.array([lon, lat]
                        ),
                        lonlat=True
                    )
                    healpix_map[inds] += amp[idx] * beam(r, sigma)
                    pbar.update()

        healpix_map = healpix_map.to(
            u.uK, u.brightness_temperature(self.freq_ref, beam_area)
        )

        return np.expand_dims(healpix_map, axis=0)

    def _read_coords(self, catalog):
        """Reads in the angular coordinates of the point sources from a 
        given catalog.

        Parameters
        ----------
        catalog : str
            Path to the point source catalog. Default is the COM_GB6 
            catalog.
        
        Returns
        -------
        coords : `numpy.ndarray`
            Longitude and latitude values of each point source
        """
        
        try:
            coords = np.loadtxt(catalog, usecols=(0,1))
        except OSError:
            raise OSError('Could not find point source catalog')

        if len(coords) == len(self.amp[0]):
            return coords
        else:
            raise ValueError('Cataloge does not match chain catalog')


class _LineComponent(_DiffuseComponent):
    def __init__(self, amp, freq_ref, **spectral_parameters):
        super().__init__(amp, freq_ref, **spectral_parameters)