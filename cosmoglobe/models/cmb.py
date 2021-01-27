from .skycomponent import SkyComponent
import astropy.units as u


class CMB(SkyComponent):
    """
    Parent class for all CMB models.

    """
    comp_label = 'cmb'

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)
        self.kwargs = kwargs

        if kwargs['nside'] is None:
            nside = self.params['nside']
        else:
            nside = kwargs['nside']

        if kwargs['fwhm']is None:
            fwhm = self.params['fwhm']
        else:
            fwhm = kwargs['fwhm']

        self.monopole = data.get_alms('amp',
                                      self.comp_label, 
                                      nside, 
                                      self.params['polarization'], 
                                      fwhm,
                                      multipole=0)*u.uK
        self.dipole = data.get_alms('amp',
                                      self.comp_label, 
                                      nside, 
                                      self.params['polarization'], 
                                      fwhm,
                                      multipole=1)*u.uK

        if kwargs.get('remove_monopole', False):
            self.amp -= self.monopole

        if kwargs.get('remove_dipole', False):
            self.amp -= self.dipole




class BlackBody(CMB):
    """
    Model for BlackBody CMB emission.

    """    
    model_label = 'cmb'

    def __init__(self, data, nside=None, fwhm=None,
                 remove_monopole=False, remove_dipole=False):

        super().__init__(data, nside=nside, fwhm=fwhm, 
                         remove_monopole=remove_monopole, 
                         remove_dipole=remove_dipole)


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
    
        return self.KCMB_to_KRJ(emission, nu).to(u.uK)