from .. import sky
from ..tools import utils

from numba import njit
import astropy.units as u
import h5py
import healpy as hp
import numpy as np
import inspect
<<<<<<< HEAD

param_group = 'parameters'  # Model parameter group name as implemented in commander
_ignored_comps = ['md', 'radio', 'relquad'] # These will be dropped from component lists
=======
from tqdm import tqdm
import sys

# Model parameter group name as implemented in commander
param_group = 'parameters'
# These will be dropped from component lists
_ignored_comps = ['md', 'radio', 'relquad']
>>>>>>> d2387d3e3215ae8835f0c053b5f3522cadf74bc5


def model_from_chain(file, nside=None, sample=None, burn_in=None, comps=None):
    """Returns a sky model from a commander3 chainfile.
    
    A cosmoglobe.sky.Model is initialized that represents the sky model used in 
    the given Commander run.

    Args:
    -----
    file (str):
        Path to commander3 hdf5 chainfile.
    nside (int):
        Healpix resolution parameter.
    sample (str, int, list):
        If sample is None, then the model will be initialized from sample 
        averaged maps. If sample is a string (or an int), the model will be 
        initialized from that specific sample. If sample is a list, then the 
        model will be initialized from an average over the samples in the list.
        Default: None
    burn_in (str, int):
        The sample number as a str or int where the chainfile is assumed to 
        have sufficently burned in. All samples before the burn_in are ignored 
        in the averaging process.
    comps (dict):
        Dictionary of which classes to use for each component. The keys must
        the comp group names in the chain file. If comps is None, a default set
        of components will be selected. Default: None

    Returns:
    --------
    (cosmoglobe.sky.Model):
        A sky model representing the results of a commander3 run.

    """
    model = sky.Model(nside=nside)

    default_comps = {
        'dust': sky.ModifiedBlackBody,
        'synch': sky.PowerLaw,
        'ff': sky.LinearOpticallyThinBlackBody,
        'ame': sky.SpDust2,
        'cmb': sky.BlackBodyCMB,
    }
    if not comps:
        comps = default_comps

    component_list = _get_components(file)
<<<<<<< HEAD
    for comp in component_list:
        model.insert(comp_from_chain(file, comp, comps[comp], 
                                     nside, sample, burn_in))

=======
    print('Loading components from chain')
    with tqdm(total=len(component_list), file=sys.stdout) as pbar:
        padding = len(max(component_list, key=len))
        for comp in component_list:
            pbar.set_description(f'{comp:<{padding}}')
            model.insert(comp_from_chain(file, comp, comps[comp], 
                                     nside, sample, burn_in))
            pbar.update(1)
        pbar.set_description('done')
>>>>>>> d2387d3e3215ae8835f0c053b5f3522cadf74bc5
    return model


def comp_from_chain(file, component, component_class, model_nside, 
                    sample=None, burn_in=None):
    """Returns a sky component from a commander3 chainfile.
    
    A sky component that subclasses cosmoglobe.sky.Component is initialized 
    from a given commander run.

    Args:
    -----
    file (str):
        Path to commander3 hdf5 chainfile.
    component (str):
        Name of a sky component. Must match the hdf5 component group name.
    sample (str, int, list):
        If sample is 'mean', then the model will be initialized from sample 
        averaged maps. If sample is a string (or an int), the model will be 
        initialized from that specific sample. If sample is a list, then the 
        model will be initialized from an average over the samples in the list.
        Default: 'mean'
    burn_in (str, int):
        The sample number as a str or int where the chainfile is assumed to 
        have sufficently burned in. All samples before the burn_in are ignored 
        in the averaging process.

    Returns:
    --------
    (sub class of cosmoglobe.sky.Component):
        A sky component initialized from a commander run.

    """
    # Getting component parameters from chain
    parameters = _get_component_params(file, component)
    freq_ref = (parameters['nu_ref']*u.Hz).to(u.GHz)
    fwhm_ref = (parameters['fwhm']*u.arcmin).to(u.rad)
    nside = parameters['nside']
    amp_unit = parameters['unit']
    if parameters['polarization'] == 'True':
        comp_is_polarized = True
    else:
        comp_is_polarized = False

    # Astropy doesnt have built in K_RJ or K_CMB so we manually set it to K
    if 'k_rj' in amp_unit.lower():
        amp_unit = amp_unit[:-3]
    elif 'k_cmb' in amp_unit.lower():
        amp_unit = amp_unit[:-4]
    amp_unit = u.Unit(amp_unit)

    # Getting arguments required to initialize component
    args_list = _get_comp_args(component_class) 
    args = {}

    if sample is None:
        get_items = _get_averaged_items
        sample = _get_samples(file)
        if burn_in is not None:
            sample = sample[burn_in:]
    else:
        get_items = _get_items
    if isinstance(sample, int):
        sample = _int_to_sample(sample)

    # Find which args are alms and which are precomputed maps
    alm_names = []
    map_names = []
    for arg in args_list:
        if arg != 'freq_ref':
            if _item_alm_exists(file, component, arg):
                alm_names.append(arg)
            elif _item_map_exists(file,component, arg):
                map_names.append(arg)
            else:
                raise KeyError(f'item {arg} is not present in the chain')


<<<<<<< HEAD
    maps_ = get_items(file, sample, component, [f'{map_}_map' for map_ in map_names])
    maps = dict(zip(map_names, maps_))
    if model_nside is not None and nside != model_nside:
        maps = {key:hp.ud_grade(value, model_nside) if isinstance(value, np.ndarray) 
=======
    maps_ = get_items(file, sample, component, 
                      [f'{map_}_map' for map_ in map_names])
    maps = dict(zip(map_names, maps_))
    if model_nside is not None and nside != model_nside:
        maps = {key:hp.ud_grade(value, model_nside) 
                if isinstance(value, np.ndarray) 
>>>>>>> d2387d3e3215ae8835f0c053b5f3522cadf74bc5
                else value for key, value in maps.items()}
    args.update(maps)

    if model_nside is None:
        model_nside = nside

<<<<<<< HEAD
    alms_ = get_items(file, sample, component, [f'{alm}_alm' for alm in alm_names])
    alms = dict(zip(alm_names, alms_))
    alms_lmax_ = get_items(file, sample, component, [f'{alm}_lmax' for alm in alm_names])
=======
    alms_ = get_items(file, sample, component, 
                      [f'{alm}_alm' for alm in alm_names])
    alms = dict(zip(alm_names, alms_))
    alms_lmax_ = get_items(file, sample, component, 
                           [f'{alm}_lmax' for alm in alm_names])
>>>>>>> d2387d3e3215ae8835f0c053b5f3522cadf74bc5
    alms_lmax = dict(zip(alm_names, [int(lmax) for lmax in alms_lmax_]))

    for key, value in alms.items():
        unpacked_alm = unpack_alms_from_chain(value, alms_lmax[key])
        if 'key' == 'amp':
            pol = True
        else:
            pol = False

        alms_ = hp.alm2map(unpacked_alm, 
                          nside=model_nside, 
                          lmax=alms_lmax[key], 
                          fwhm=fwhm_ref.value,
                          pol=pol,
                          verbose=False).astype('float32')

        alms[key] = alms_

    args.update(alms)
    args['amp'] = args['amp']*amp_unit
    args = utils._set_spectral_units(args)
<<<<<<< HEAD
    scalars = utils._extract_scalars(args)    # converts scalar maps to scalar values
=======
    scalars = utils._extract_scalars(args) # dont save scalar maps
>>>>>>> d2387d3e3215ae8835f0c053b5f3522cadf74bc5
    args.update(scalars)
    if 'freq_ref' in args_list:
        if comp_is_polarized:
            freq = u.Quantity(freq_ref[:-1])
        else:
            freq = u.Quantity(freq_ref[0])
        args['freq_ref'] = freq
            
    return component_class(name=component, **args)


def _get_comp_args(component_class):
    """Returns a list of arguments needed to initialize a component"""
    ignored_args = ['self', 'name']
    arguments = inspect.getargspec(component_class.__init__).args
    return [arg for arg in arguments if arg not in ignored_args]


def _get_samples(file):
    """Returns a list of all samples present in a chain file"""
    with h5py.File(file, 'r') as f:
        samples = list(f.keys())

    samples.remove(param_group)
    return samples


def _sample_to_int(samples, start=0):
    """Converts a sample or a list of samples to integers"""
    if isinstance(samples, (list, tuple)):
        return [int(sample) + start for sample in samples]
    
    return int(samples) + start


def _int_to_sample(samples, start=0):
    """Converts an integer or multiple integers to sample string format"""
    if isinstance(samples, (list, tuple)):
        return [f'{sample + start:06d}' for sample in samples]
    
    return f'{samples + start:06d}'


def _get_components(file, ignore_comps=True):
    """Returns a list of all components present in a chain file"""
    with h5py.File(file, 'r') as f:
        components = list(f[param_group].keys())

    if ignore_comps:    
        return [comp for comp in components if comp not in _ignored_comps]

    return components


def _get_component_params(file, component):
    """Returns a dictionary of the model parameters of a component"""
    return_params = {}
    with h5py.File(file, 'r') as f:
        params = f[param_group][component]
        for param, value in params.items():
            if isinstance(value[()], bytes):
                return_params[param] = value.asstr()[()]
            else:
                return_params[param] = value[()]

        return return_params
    

def _get_items(file, sample, component, items):
    """Return the value of one or many items for a component in the chain file.

    Args:
    -----
    file: str
        Path to h5 file.
    sample : str
        sample name.
    component: str
        Component group name.
    items: str, list, tuple
        Name of item to extract, or a list of names.

    Returns:
    --------
    list
        List of items extracted from the chain file.
    
    """
    with h5py.File(file, 'r') as f:
        items_to_return = []
        try:
            for item in items:
                items_to_return.append(f[sample][component].get(item)[()])

            return items_to_return
        except TypeError:
            return f[sample][component].get(items)[()]


def _get_averaged_items(file, samples, component, items):
    """Return the averaged value of one or many item for a component in the 
    chain file.

    Args:
    -----
    file: str
        Path to h5 file.
    samples : list
        List of samples to average over.
    component:
        Component group.
    items: str, list, tuple
        Name of item to extract, or a list of names. Items must be of types
        compatible with integer division.

    Returns:
    --------
    list
        List of items averaged over samples from the chain file.
    
    """
    with h5py.File(file, 'r') as f:
        if isinstance(items, (tuple, list)):
            items_to_return = []
            for sample in samples:
                for idx, item in enumerate(items):
                    try:
<<<<<<< HEAD
                        items_to_return[idx] += f[sample][component].get(item)[()]
                    except IndexError:
                        items_to_return.append(f[sample][component].get(item)[()])
=======
                        items_to_return[idx] += (
                            f[sample][component].get(item)[()]
                        )
                    except IndexError:
                        items_to_return.append(
                            f[sample][component].get(item)[()]
                        )
>>>>>>> d2387d3e3215ae8835f0c053b5f3522cadf74bc5

            return [item/len(samples) for item in items_to_return]

        for sample in samples:
            try:
                item_to_return += f[sample][component].get(items)[()]
            except UnboundLocalError:
                item_to_return = f[sample][component].get(items)[()]

        return item_to_return/len(samples)


def _item_alm_exists(file, component, item):
    """Returns True if component contains alms for the given item, else 
    returns False.
    """
    sample = _get_samples(file)[-1]

    with h5py.File(file, 'r') as f:
        params = list(f[sample][component].keys())

    if f'{item}_alm' in params:
        return True

    return False


def _item_map_exists(file, component, item):
    """Returns True if component contains precomputed map for item, else 
    returns False.
    """
    sample = _get_samples(file)[-1]

    with h5py.File(file, 'r') as f:
        params = list(f[sample][component].keys())

    if f'{item}_map' in params:
        return True

    return False


@njit
def unpack_alms_from_chain(data, lmax):
    """Unpacks alms from the Commander chain output.

    Unpacking algorithm: 
    https://github.com/trygvels/c3pp/blob/2a2937926c260cbce15e6d6d6e0e9d23b0be1262/src/tools.py#L9

    TODO: look over this function and see if it can be improved.

    Args:
    -----
    data (np.ndarray)
        alms from a commander chainfile.
    lmax : int
        Maximum value for l used in the alms.

    Returns:
    --------
    alms (np.ndarray)
        Unpacked version of the Commander alms (2-dimensional array)
    
    """
    n = len(data)
    n_alms = int(lmax * (2*lmax+1 - lmax) / 2 + lmax+1)
    alms = np.zeros((n, n_alms), dtype=np.complex128)

    for sigma in range(n):
        i = 0
        for l in range(lmax+1):
            j_real = l**2 + l
            alms[sigma, i] = complex(data[sigma, j_real], 0.0)
            i += 1

        for m in range(1, lmax+1):
            for l in range(m, lmax+1):
                j_real = l**2 + l + m
                j_comp = l**2 + l - m
                alms[sigma, i] = complex(data[sigma, j_real], 
                                         data[sigma, j_comp],)/ np.sqrt(2.0)
                i += 1

    return alms