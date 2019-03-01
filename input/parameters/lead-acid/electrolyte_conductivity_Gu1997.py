#
# Electrolyte conductivity
#
import numpy as np


def electrolyte_conductivity_Gu1997(c_e):
    """
    Dimensional conductivity in the electrolyte [S.m-1], from [1] citing [2] and
    agreeing with data in [3], as a function of the electrolyte concentration
    c_e [mol.m-3].

    [1] WB Gu, CY Wang, and BY Liaw. Numerical modeling of coupled electrochemical and
    transport processes in lead-acid batteries. Journal of The Electrochemical Society,
    144(6):2053–2061, 1997.
    [2] WH Tiedemann and J Newman. Battery design and optimization. Journal of
    Electrochemical Society, Softbound Proceeding Series, Princeton, New York, 79(1):23,
    1979.
    [3] TW Chapman and J Newman. Compilation of selected thermodynamic and transport
    properties of binary electrolytes in aqueous solution. Technical report, California
    Univ., Berkeley. Lawrence Radiation Lab., 1968.

    """
    return c_e * np.exp(6.23 - 1.34e-4 * c_e - 1.61e-8 * c_e ** 2) * 1e-4
