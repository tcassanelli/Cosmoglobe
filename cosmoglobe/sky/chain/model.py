import inspect
from typing import Dict, List, Type, Union, Optional, Literal

import astropy.units as u
import healpy as hp
from tqdm import tqdm

from cosmoglobe.h5.chain import Chain, ChainVersion
from cosmoglobe.h5._exceptions import (
    ChainComponentNotFoundError,
    ChainKeyError,
    ChainFormatError,
)
from cosmoglobe.sky.base_components import (
    SkyComponent,
    DiffuseComponent,
    PointSourceComponent,
)
from cosmoglobe.sky.chain.context import chain_context
from cosmoglobe.sky.csm import REGISTERED_SKY_MODELS, SkyComponentLabel
from cosmoglobe.sky.model import SkyModel

DEFAULT_SAMPLE = -1

def model_from_chain(
    chain: Union[str, Chain],
    nside: int,
    components: Optional[List[str]] = None,
    samples: Optional[Union[range, int, Literal["all"]]] = DEFAULT_SAMPLE,
    burn_in: Optional[int] = None,
    model: str = "BeyondPlanck",
) -> SkyModel:
    """Initialize and return a cosmoglobe sky model from a chainfile.

    Parameters
    ----------
    chain
        Path to a Cosmoglobe chainfile or a Chain object.
    components
        List of components to include in the model.
    nside
        Model HEALPIX map resolution parameter.
    samples
        The sample number for which to extract the model. If the input
        is 'all', then the model will an average of all samples in the chain.
        Defaults to the last sample in the chain.
    burn_in
        Burn in sample for which all previous samples are disregarded.

    Returns
    -------
    model
        Initialized sky mode object.
    """

    if not isinstance(chain, Chain):
        chain = Chain(chain, burn_in)

    if isinstance(samples, str):
        if samples.lower() == "all":
            samples = None
        else:
            raise ValueError("samples must be either 'all', an int, or a range")

    if chain.version is ChainVersion.OLD:
        raise ChainFormatError(
            "cannot initialize a sky model from a chain without a " "parameter group"
        )

    sky_model = REGISTERED_SKY_MODELS.get_model(model)

    print(f"Initializing model from {chain.path.name}")
    if components is None:
        components = chain.components
    elif any(component not in chain.components for component in components):
        raise ChainComponentNotFoundError(f"component was not found in chain")

    initialized_components: Dict[str, SkyComponent] = {}
    with tqdm(total=len(components), ncols=75) as progress_bar:
        padding = len(max(chain.components, key=len))
        for component in components:
            progress_bar.set_description(f"{component:<{padding}}")
            try:
                component_class = sky_model.components[SkyComponentLabel(component)]
            except KeyError:
                raise ChainComponentNotFoundError(
                    f"{component=!r} is not part in the Cosmoglobe Sky Model"
                )
            initialized_components[component] = comp_from_chain(
                chain, nside, component, component_class, samples
            )
            progress_bar.update()

    return SkyModel(nside=nside, components=initialized_components, info=sky_model.info)


def comp_from_chain(
    chain: Chain,
    nside: int,
    component_label: str,
    component_class: Type[SkyComponent],
    samples: Optional[Union[range, int]] = None,
) -> SkyComponent:
    """Initialize and return a sky component from a chainfile.

    Parameters
    ----------
    component
        Name of the component in the chain.
    chain
        Chain object.
    nside
        Model HEALPIX map resolution parameter.

    Returns
    -------
        Initialized sky component object.
    """

    class_args = get_comp_signature(component_class)
    args = {}

    # Contexts are operations that needs to be done to the data in the
    # chain before it can be used in the sky model.
    mappings = chain_context.get_mappings(component_class)
    units = chain_context.get_units(component_class)
    for arg in class_args:
        chain_arg = mappings.get(arg, arg)
        chain_params = chain.parameters[component_label]

        if chain_arg in chain_params:
            value = chain_params[chain_arg]
        else:
            try:
                value = chain.mean(f"{component_label}/{chain_arg}_alm", samples=samples)
                is_alm = True
            except ChainKeyError:
                try:
                    value = chain.mean(f"{component_label}/{chain_arg}", samples=samples)
                except ChainKeyError:
                    value = chain.mean(f"{component_label}/{chain_arg}_map", samples=samples)
                is_alm = False

            if is_alm:
                pol = True if arg == "amp" and value.shape[0] == 3 else False
                lmax = chain.get(f"{component_label}/{chain_arg}_lmax", samples=0)
                value = hp.alm2map(
                    value,
                    nside=nside if nside is not None else chain_params["nside"],
                    lmax=lmax,
                    fwhm=(chain_params["fwhm"] * u.arcmin).to("rad").value,
                    pol=pol,
                )

        args[arg] = u.Quantity(value, unit=units[arg] if arg in units else None)

    contexts = chain_context.get_context(component_class)
    for context in contexts:
        args.update(context(args))

    return component_class(**args)


def get_comp_signature(comp_class: Type[SkyComponent]) -> List[str]:
    """Extracts and returns the parameters to extract from the chain."""

    EXCLUDE = ["self", "spectral_parameters", "freqs"]
    arguments: List[str] = []
    class_signature = inspect.signature(comp_class)
    arguments.extend(list(class_signature.parameters.keys()))
    if issubclass(comp_class, (DiffuseComponent, PointSourceComponent)):
        SED_signature = inspect.signature((comp_class.get_freq_scaling))
        arguments.extend(list(SED_signature.parameters.keys()))

    arguments = [arg for arg in arguments if arg not in EXCLUDE]

    return arguments
