#
# Class for when there is no anode decomposition
#
import pybamm
from scipy import constants 

class NoAnodeDecomposition(pybamm.BaseSubModel):
    """Base class for no graphite anode decomposition in Li-ion batteries.

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel
    reactions : dict, optional
        Dictionary of reaction terms

    **Extends:** :class:`pybamm.BaseSubModel`
    """
    def __init__(self, param):
        super().__init__(param)

    def get_fundamental_variables(self):

        variables = {
            "Relative SEI thickness": pybamm.Scalar(0),
            "Anode decomposition reaction rate": pybamm.Scalar(0),
        }
        
        return variables