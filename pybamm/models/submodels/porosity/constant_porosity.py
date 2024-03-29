#
# Class for constant porosity
#
import pybamm

from .base_porosity import BaseModel


class Constant(BaseModel):
    """Submodel for constant porosity

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel


    **Extends:** :class:`pybamm.porosity.BaseModel`
    """

    def get_fundamental_variables(self):
        if self.half_cell:
            eps_n = None
            deps_n_dt = None
        else:
            eps_n = self.param.epsilon_n_init
            deps_n_dt = pybamm.FullBroadcast(
                0, "negative electrode", "current collector"
            )

        eps_s = self.param.epsilon_s_init
        eps_p = self.param.epsilon_p_init

        deps_s_dt = pybamm.FullBroadcast(0, "separator", "current collector")
        deps_p_dt = pybamm.FullBroadcast(0, "positive electrode", "current collector")

        variables = self._get_standard_porosity_variables(
            eps_n, eps_s, eps_p, set_leading_order=True
        )
        variables.update(
            self._get_standard_porosity_change_variables(
                deps_n_dt, deps_s_dt, deps_p_dt, set_leading_order=True
            )
        )

        return variables
