import pybamm
import numpy as np
import os
import pickle
import scipy.interpolate as interp
import matplotlib.pyplot as plt

# change working directory to the root of pybamm
os.chdir(pybamm.root_dir())

"-----------------------------------------------------------------------------"
"Load comsol data"

try:
    comsol_variables = pickle.load(
        open("input/comsol_results/comsol_isothermal_1C.pickle", "rb")
    )
except FileNotFoundError:
    raise FileNotFoundError("COMSOL data not found. Try running load_comsol_data.py")

"-----------------------------------------------------------------------------"
"Create and solve pybamm model"

# load model and geometry
pybamm.set_logging_level("INFO")
pybamm_model = pybamm.lithium_ion.DFN()
geometry = pybamm_model.default_geometry

# load parameters and process model and geometry
param = pybamm_model.default_parameter_values
param.update(
    {
        "C-rate": 1,
        #    "Negative electrode conductivity [S.m-1]": 1e6,
        #    "Positive electrode conductivity [S.m-1]": 1e6,
    }
)
param.process_model(pybamm_model)
param.process_geometry(geometry)

# create mesh
var = pybamm.standard_spatial_vars
# var_pts = {var.x_n: 101, var.x_s: 31, var.x_p: 101, var.r_n: 31, var.r_p: 31}
var_pts = {var.x_n: 45, var.x_s: 11, var.x_p: 56, var.r_n: 51, var.r_p: 51}
mesh = pybamm.Mesh(geometry, pybamm_model.default_submesh_types, var_pts)

# discretise model
disc = pybamm.Discretisation(mesh, pybamm_model.default_spatial_methods)
disc.process_model(pybamm_model)

# discharge timescale
tau = param.evaluate(pybamm.standard_parameters_lithium_ion.tau_discharge)

# solve model at comsol times
time = comsol_variables["time"] / tau
pybamm_model.convert_to_format = "casadi"
# solver = pybamm.IDAKLUSolver(atol=1e-6, rtol=1e-6, root_tol=1e-6)
solver = pybamm.CasadiSolver(atol=1e-6, rtol=1e-6, root_tol=1e-6, mode="fast")
solution = solver.solve(pybamm_model, time)

"-----------------------------------------------------------------------------"
"Make Comsol 'model' for comparison"

whole_cell = ["negative electrode", "separator", "positive electrode"]
comsol_t = comsol_variables["time"]
L_x = param.evaluate(pybamm.standard_parameters_lithium_ion.L_x)


def get_interp_fun(variable, domain):
    """
    Create a :class:`pybamm.Function` object using the variable, to allow plotting with
    :class:`'pybamm.QuickPlot'` (interpolate in space to match edges, and then create
    function to interpolate in time)
    """
    if domain == ["negative electrode"]:
        comsol_x = comsol_variables["x_n"]
    elif domain == ["separator"]:
        comsol_x = comsol_variables["x_s"]
    elif domain == ["positive electrode"]:
        comsol_x = comsol_variables["x_p"]
    elif domain == whole_cell:
        comsol_x = comsol_variables["x"]
    # Make sure to use dimensional space
    pybamm_x = mesh.combine_submeshes(*domain)[0].nodes * L_x
    variable = interp.interp1d(comsol_x, variable, axis=0)(pybamm_x)

    def myinterp(t):
        return interp.interp1d(comsol_t, variable)(t)[:, np.newaxis]

    # Make sure to use dimensional time
    fun = pybamm.Function(myinterp, pybamm.t * tau)
    fun.domain = domain
    return fun


comsol_c_n_surf = get_interp_fun(comsol_variables["c_n_surf"], ["negative electrode"])
comsol_c_e = get_interp_fun(comsol_variables["c_e"], whole_cell)
comsol_c_p_surf = get_interp_fun(comsol_variables["c_p_surf"], ["positive electrode"])
comsol_phi_n = get_interp_fun(comsol_variables["phi_n"], ["negative electrode"])
comsol_phi_e = get_interp_fun(comsol_variables["phi_e"], whole_cell)
comsol_phi_p = get_interp_fun(comsol_variables["phi_p"], ["positive electrode"])
comsol_i_s_n = get_interp_fun(comsol_variables["i_s_n"], ["negative electrode"])
comsol_i_s_p = get_interp_fun(comsol_variables["i_s_p"], ["positive electrode"])
comsol_i_e_n = get_interp_fun(comsol_variables["i_e_n"], ["negative electrode"])
comsol_i_e_p = get_interp_fun(comsol_variables["i_e_p"], ["positive electrode"])
comsol_voltage = interp.interp1d(comsol_t, comsol_variables["voltage"])

# Create comsol model with dictionary of Matrix variables
comsol_model = pybamm.BaseModel()
comsol_model.variables = {
    "Negative particle surface concentration [mol.m-3]": comsol_c_n_surf,
    "Electrolyte concentration [mol.m-3]": comsol_c_e,
    "Positive particle surface concentration [mol.m-3]": comsol_c_p_surf,
    "Current [A]": pybamm_model.variables["Current [A]"],
    "Negative electrode potential [V]": comsol_phi_n,
    "Electrolyte potential [V]": comsol_phi_e,
    "Positive electrode potential [V]": comsol_phi_p,
    "Negative electrode current density [A.m-2]": comsol_i_s_n,
    "Positive electrode current density [A.m-2]": comsol_i_s_p,
    "Negative electrode electrolyte current density [A.m-2]": comsol_i_e_n,
    "Positive electrode electrolyte current density [A.m-2]": comsol_i_e_p,
    "Terminal voltage [V]": pybamm.Function(comsol_voltage, pybamm.t * tau),
}

"-----------------------------------------------------------------------------"
"Plot comparison"

plot_times = comsol_variables["time"]
pybamm_voltage = pybamm.ProcessedVariable(
    pybamm_model.variables["Terminal voltage [V]"], solution.t, solution.y, mesh=mesh
)(plot_times / tau)
comsol_voltage = pybamm.ProcessedVariable(
    comsol_model.variables["Terminal voltage [V]"], solution.t, solution.y, mesh=mesh
)(plot_times / tau)
plt.figure()
plt.plot(plot_times, pybamm_voltage, "-", label="PyBaMM")
plt.plot(plot_times, comsol_voltage, "o", label="COMSOL")
plt.xlabel("t")
plt.ylabel("Voltage [V]")
plt.legend()

# Get mesh nodes
x_n = mesh.combine_submeshes(*["negative electrode"])[0].nodes
x_s = mesh.combine_submeshes(*["separator"])[0].nodes
x_p = mesh.combine_submeshes(*["positive electrode"])[0].nodes
x = mesh.combine_submeshes(*whole_cell)[0].nodes


def whole_cell_by_domain_comparison_plot(var, plot_times=None):
    """
    Plot pybamm variable (defined over whole cell) against comsol variable
    (defined by component)
    """
    if plot_times is None:
        plot_times = comsol_variables["time"]

    # Process pybamm variable
    pybamm_var = pybamm.ProcessedVariable(
        pybamm_model.variables[var], solution.t, solution.y, mesh=mesh
    )

    # Process comsol variable in negative electrode
    comsol_var_n = pybamm.ProcessedVariable(
        comsol_model.variables["Negative electrode " + var[0].lower() + var[1:]],
        solution.t,
        solution.y,
        mesh=mesh,
    )
    # Process comsol variable in separator (if defined here)
    try:
        comsol_var_s = pybamm.ProcessedVariable(
            comsol_model.variables["Separator " + var[0].lower() + var[1:]],
            solution.t,
            solution.y,
            mesh=mesh,
        )
    except KeyError:
        comsol_var_s = None
        print("Variable " + var + " not defined in separator")
    # Process comsol variable in positive electrode
    comsol_var_p = pybamm.ProcessedVariable(
        comsol_model.variables["Positive electrode " + var[0].lower() + var[1:]],
        solution.t,
        solution.y,
        mesh=mesh,
    )

    # Make plot
    if comsol_var_s:
        n_cols = 3
    else:
        n_cols = 2
    fig, ax = plt.subplots(1, n_cols, figsize=(15, 8))
    cmap = plt.get_cmap("inferno")

    for ind, t in enumerate(plot_times):
        color = cmap(float(ind) / len(plot_times))
        ax[0].plot(x_n * L_x, comsol_var_n(x=x_n, t=t / tau), "o", color=color)
        ax[0].plot(x_n * L_x, pybamm_var(x=x_n, t=t / tau), "-", color=color)
        if comsol_var_s:
            ax[1].plot(x_s * L_x, comsol_var_s(x=x_s, t=t / tau), "o", color=color)
            ax[1].plot(x_s * L_x, pybamm_var(x=x_s, t=t / tau), "-", color=color)
        ax[n_cols - 1].plot(
            x_p * L_x,
            comsol_var_p(x=x_p, t=t / tau),
            "o",
            color=color,
            label="COMSOL" if ind == 0 else "",
        )
        ax[n_cols - 1].plot(
            x_p * L_x,
            pybamm_var(x=x_p, t=t / tau),
            "-",
            color=color,
            label="PyBaMM (t={:.0f} s)".format(t),
        )
    ax[0].set_xlabel("x_n")
    ax[0].set_ylabel(var)
    if comsol_var_s:
        ax[1].set_xlabel("x_s")
        ax[1].set_ylabel(var)
    ax[n_cols - 1].set_xlabel("x_p")
    ax[n_cols - 1].set_ylabel(var)
    plt.legend()
    plt.tight_layout()


def electrode_comparison_plot(var, plot_times=None):
    """
    Plot pybamm variable against comsol variable (both defined separately in the
    negative and positive electrode)
    """
    if plot_times is None:
        plot_times = comsol_variables["time"]

    # Process pybamm variable in negative electrode
    pybamm_var_n = pybamm.ProcessedVariable(
        pybamm_model.variables["Negative " + var], solution.t, solution.y, mesh=mesh
    )

    # Process pybamm variable in positive electrode
    pybamm_var_p = pybamm.ProcessedVariable(
        pybamm_model.variables["Positive " + var], solution.t, solution.y, mesh=mesh
    )

    # Process comsol variable in negative electrode
    comsol_var_n = pybamm.ProcessedVariable(
        comsol_model.variables["Negative " + var], solution.t, solution.y, mesh=mesh
    )

    # Process comsol variable in positive electrode
    comsol_var_p = pybamm.ProcessedVariable(
        comsol_model.variables["Positive " + var], solution.t, solution.y, mesh=mesh
    )

    # Make plot
    fig, ax = plt.subplots(1, 2, figsize=(15, 8))
    cmap = plt.get_cmap("inferno")

    for ind, t in enumerate(plot_times):
        color = cmap(float(ind) / len(plot_times))
        ax[0].plot(x_n * L_x, comsol_var_n(x=x_n, t=t / tau), "o", color=color)
        ax[0].plot(x_n * L_x, pybamm_var_n(x=x_n, t=t / tau), "-", color=color)
        ax[1].plot(
            x_p * L_x,
            comsol_var_p(x=x_p, t=t / tau),
            "o",
            color=color,
            label="COMSOL" if ind == 0 else "",
        )
        ax[1].plot(
            x_p * L_x,
            pybamm_var_p(x=x_p, t=t / tau),
            "-",
            color=color,
            label="PyBaMM (t={:.0f} s)".format(t),
        )
    ax[0].set_xlabel("x_n")
    ax[0].set_ylabel(var)
    ax[1].set_xlabel("x_p")
    ax[1].set_ylabel(var)
    plt.legend()
    plt.tight_layout()


def whole_cell_comparison_plot(var, plot_times=None):
    """
    Plot pybamm variable against comsol variable (both defined over whole cell)
    """
    if plot_times is None:
        plot_times = comsol_variables["time"]

    # Process pybamm variable
    pybamm_var = pybamm.ProcessedVariable(
        pybamm_model.variables[var], solution.t, solution.y, mesh=mesh
    )

    # Process comsol variable
    comsol_var = pybamm.ProcessedVariable(
        comsol_model.variables[var], solution.t, solution.y, mesh=mesh
    )

    # Make plot
    plt.figure(figsize=(15, 8))
    cmap = plt.get_cmap("inferno")

    for ind, t in enumerate(plot_times):
        color = cmap(float(ind) / len(plot_times))
        plt.plot(
            x * L_x,
            comsol_var(x=x, t=t / tau),
            "o",
            color=color,
            label="COMSOL" if ind == 0 else "",
        )
        plt.plot(
            x * L_x,
            pybamm_var(x=x, t=t / tau),
            "-",
            color=color,
            label="PyBaMM (t={:.0f} s)".format(t),
        )
    plt.xlabel("x")
    plt.ylabel(var)
    plt.legend()
    plt.tight_layout()


# Make plots
plot_times = comsol_variables["time"][0::10]
# plot_times = [600, 1200, 1800, 2400, 3000]
# potentials
electrode_comparison_plot("electrode potential [V]", plot_times=plot_times)
plt.savefig("iso1D_phi_s.eps", format="eps", dpi=1000)
whole_cell_comparison_plot("Electrolyte potential [V]", plot_times=plot_times)
plt.savefig("iso1D_phi_e.eps", format="eps", dpi=1000)
# current
electrode_comparison_plot("electrode current density [A.m-2]", plot_times=plot_times)
plt.savefig("iso1D_i_s.eps", format="eps", dpi=1000)
whole_cell_by_domain_comparison_plot(
    "Electrolyte current density [A.m-2]", plot_times=plot_times
)
plt.savefig("iso1D_i_e.eps", format="eps", dpi=1000)
# concentrations
electrode_comparison_plot(
    "particle surface concentration [mol.m-3]", plot_times=plot_times
)
plt.savefig("iso1D_c_surf.eps", format="eps", dpi=1000)
whole_cell_comparison_plot("Electrolyte concentration [mol.m-3]", plot_times=plot_times)
plt.savefig("iso1D_c_e.eps", format="eps", dpi=1000)
plt.show()
