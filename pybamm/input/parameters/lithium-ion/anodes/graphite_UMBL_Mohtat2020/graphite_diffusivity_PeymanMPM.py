import pybamm


def graphite_diffusivity_PeymanMPM(sto, T, T_inf, E_D_s, R_g):
    """
    Graphite diffusivity as a function of stochiometry, in this case the
    diffusivity is taken to be a constant. The value is taken from Peyman MPM.

    References
    ----------
    .. [1] http://www.cchem.berkeley.edu/jsngrp/fortran.html

    Parameters
    ----------
    sto: :class: `numpy.Array`
        Electrode stochiometry
    T: :class: `numpy.Array`
        Dimensional temperature
    T_inf: double
        Reference temperature
    E_D_s: double
        Solid diffusion activation energy
    R_g: double
        The ideal gas constant

    Returns
    -------
    : double
        Solid diffusivity
   """

    D_ref = 5.0 * 10 ** (-15)
    arrhenius = pybamm.exp(E_D_s / R_g * (1 / T_inf - 1 / T))

    # Removing the fudge factor 0 * sto requires different handling of either
    # either simplifications or how sto is passed into this function.
    # See #547
    return D_ref * arrhenius + 0 * sto