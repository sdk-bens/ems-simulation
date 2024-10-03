# importing libraries
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

# importing the custom classes
from .battery_cell import BatteryCell
from .battery_pack import BatteryPack
from .bms import BMS
from .ems import EMS

# initialize the dashboard
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# initialize the attributes
num_cells = 4
cell_capacity = 5.0  # Ah
initial_voltage = 3.7  # V
initial_soc = 80  # %
solar_capacity = 5  # kW
max_grid_power = 10  # kW

# creating a battery pack, BMS, and EMS
battery_pack = BatteryPack(num_cells, cell_capacity, initial_voltage, initial_soc)
bms = BMS(battery_pack)
ems = EMS(bms, solar_capacity, max_grid_power)

def simulate_solar_generation(t, max_power, cloud_factor):
    """
    Simulate solar power generation based on time of day and weather conditions.

    Args:
    t (float): Time in hours
    max_power (float): Maximum solar power capacity in kW
    cloud_factor (float): Factor representing cloud cover (0-1)

    Returns:
    float: Simulated solar power generation in kW
    """
    hour = t % 24
    base = max_power * np.sin(np.pi * (hour - 6) / 12) ** 2
    base = np.where((hour >= 6) & (hour <= 18), base, 0)
    noise = np.random.normal(0, 0.1 * max_power)
    return max(0, cloud_factor * base + noise)

def simulate_demand(t, base_load, peak_factor):
    """
    Simulate power demand based on time of day and day of week.

    Args:
    t (float): Time in hours
    base_load (float): Base power demand in kW
    peak_factor (float): Factor to determine peak demand

    Returns:
    float: Simulated power demand in kW
    """
    hour = t % 24
    
    # morning peak
    morning_peak = peak_factor * np.exp(-((hour - 8) ** 2) / 8)
    
    # evening peak
    evening_peak = peak_factor * 1.5 * np.exp(-((hour - 19) ** 2) / 8)
    
    demand = base_load + morning_peak + evening_peak
    noise = np.random.normal(0, 0.05 * base_load)
    return max(0, demand + noise)

def simulate_ems(duration, time_step, solar_scenario, demand_scenario):
    """
    Simulate the Energy Management System (EMS) over a specified duration.

    Args:
    duration (float): Simulation duration in hours
    time_step (float): Time step for simulation in hours
    solar_scenario (dict): Parameters for solar generation simulation
    demand_scenario (dict): Parameters for demand simulation

    Returns:
    tuple: Contains arrays of time, voltage, current, temperature, SoC, SoH,
           solar data, grid power, battery power, demand data, and console output
    """
    time = np.arange(0, duration, time_step)
    solar_data = []
    demand_data = []
    grid_power = []
    battery_power = []
    soc = []
    soh = []
    voltage = []
    current = []
    temperature = []
    console_output = []
    last_ems_action = ""
    last_bms_actions = set()
    cycle_count = []
    
    # Record initial state
    initial_state = ems.get_system_state()
    soc.append(80)
    soh.append(initial_state['battery_soh'])
    voltage.append(initial_state['battery_voltage'])
    current.append(initial_state['battery_current'])
    temperature.append(25)
    cycle_count.append(ems.bms.battery_pack.get_average_cycle_count())
    solar_data.append(0)  # no solar generation at t=0
    demand_data.append(0)  # no demand at t=0
    grid_power.append(0)  # no grid power at t=0
    battery_power.append(0)  # no battery power at t=0
    
    for t in time:
        # simulating solar generation and demand
        solar_gen = simulate_solar_generation(t, solar_scenario['max_power'], solar_scenario['cloud_factor'])
        demand = simulate_demand(t, demand_scenario['base_load'], demand_scenario['peak_factor'])
        
        # updating EMS
        solar, grid, battery = ems.update(t, time_step, solar_gen, demand)
        
        # getting system state
        state = ems.get_system_state()
        
        # appending data
        solar_data.append(solar)
        demand_data.append(demand)
        grid_power.append(grid)
        battery_power.append(battery)
        soc.append(state['battery_soc'])
        soh.append(state['battery_soh'])
        voltage.append(state['battery_voltage'])
        current.append(state['battery_current'])
        temperature.append(state['battery_temperature'])
        cycle_count.append(ems.bms.battery_pack.get_average_cycle_count())
        
        # logging actions (limit to every hour to reduce very long system log on the dashboard)
        if t % 1 < time_step:
            ems_action = ems.get_last_action()
            if ems_action != last_ems_action:
                if "WARNING" in ems_action:  # This is the replacement message
                    console_output.append(f"Time {t:.2f}h: BMS - {ems_action}")
                else:
                    console_output.append(f"Time {t:.2f}h: EMS - {explain_ems_action(ems_action, solar, demand, grid, battery)}")
                last_ems_action = ems_action
            
            
            new_bms_actions = set(bms.get_actions()) - last_bms_actions
            for action in new_bms_actions:
                if "Balancing" in action:
                    balancing_info = bms.get_balancing_info()
                    console_output.append(f"Time {t:.2f}h: BMS - {explain_bms_action(action, balancing_info)}")
                else:
                    console_output.append(f"Time {t:.2f}h: BMS - {explain_bms_action(action)}")
            last_bms_actions = set(bms.get_actions())
            
            bms.clear_actions()
    
    return time, voltage, current, temperature, soc, soh, solar_data, grid_power, battery_power, demand_data, console_output, cycle_count

def explain_ems_action(action, solar, demand, grid, battery):
    """
    Generate a detailed explanation of an EMS action.

    Args:
    action (str): The EMS action taken
    solar (float): Solar power generation in kW
    demand (float): Power demand in kW
    grid (float): Grid power in kW
    battery (float): Battery power in kW

    Returns:
    str: Detailed explanation of the EMS action
    """
    if "Charging" in action:
        return f"{action} - Excess power available (Solar: {solar:.2f}kW, Demand: {demand:.2f}kW, Grid: {grid:.2f}kW, Battery: {battery:.2f}kW)"
    elif "Discharging" in action:
        return f"{action} - High demand or low solar (Solar: {solar:.2f}kW, Demand: {demand:.2f}kW, Grid: {grid:.2f}kW, Battery: {battery:.2f}kW)"
    else:
        return f"{action} - Balanced power flow (Solar: {solar:.2f}kW, Demand: {demand:.2f}kW, Grid: {grid:.2f}kW, Battery: {battery:.2f}kW)"

def explain_bms_action(action, balancing_info=None):
    """
    Generate a detailed explanation of a BMS action.

    Args:
    action (str): The BMS action taken
    balancing_info (dict, optional): Information about cell balancing

    Returns:
    str: Detailed explanation of the BMS action
    """
    if "Balancing" in action:
        if balancing_info:
            cells_to_discharge = ", ".join([f"Cell {i}" for i in balancing_info['cells_to_discharge']])
            return f"{action} - Equalizing cell voltages for optimal performance and longevity. Cells to discharge: {cells_to_discharge}"
        else:
            return f"{action} - Equalizing cell voltages for optimal performance and longevity"
    elif "Temperature" in action:
        return f"{action} - Ensuring safe operating temperature for the battery pack"
    elif "Current" in action:
        return f"{action} - Protecting cells from excessive current flow"
    else:
        return action

# scenarios
scenarios = {
    "Sunny Summer Day": {
        "solar": {"max_power": 5, "cloud_factor": 1.0},
        "demand": {"base_load": 2, "peak_factor": 3}
    },
    "Cloudy Winter Day": {
        "solar": {"max_power": 3, "cloud_factor": 0.5},
        "demand": {"base_load": 3, "peak_factor": 3}
    },
    "High Demand Day": {
        "solar": {"max_power": 5, "cloud_factor": 0.8},
        "demand": {"base_load": 3, "peak_factor": 5}
    }
}

# configuring the dashbaord layout
app.layout = dbc.Container([
    html.H2("Functional Prototype of a Basic (BMS) & (EMS) in Software", className="my-4"),
    html.H3("VistaPower Interview - Seddik Benaissa", className="my-4"),
    
    dbc.Row([
        dbc.Col(html.Label("Scenario:"), width="auto", className="align-self-center"),
        dbc.Col(
            dcc.Dropdown(
                id='scenario-dropdown',
                options=[{'label': k, 'value': k} for k in scenarios.keys()],
                value='Sunny Summer Day'
            ),
            width=4
        ),
        dbc.Col(html.Label("Duration (hours):"), width="auto", className="ms-2  align-self-center"),
        dbc.Col(
            dbc.Input(
                id='duration-input',
                type='number',
                placeholder='Simulation duration (hours)',
                value=24,
                min=1,
                max=627,  # simualtion for maximum 1 month
                step=1
            ),
            width=1
        ),
        dbc.Col(
            dbc.Button('Run Simulation', id='run-button', color="primary", className="ml-2"),
            width=4
        ),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col(dcc.Graph(id='power-graph'), width=12, lg=6),
        dbc.Col(dcc.Graph(id='battery-graph'), width=12, lg=6),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col(dcc.Graph(id='temperature-current-graph'), width=12, lg=6),
        dbc.Col(dcc.Graph(id='soh-cycles-graph'), width=12, lg=6),  # New SoH graph
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4("System Logs ⚙️", className="card-title"),
                    html.Div(id='console-output', style={'maxHeight': '400px', 'overflowY': 'auto'}),
                ]),
            ),
            width=12
        ),
    ], className="mb-4"),

    dcc.Store(id='simulation-results'),
    dcc.Store(id='current-interval', data=0),
    dcc.Interval(id='update-interval', interval=1000, n_intervals=0, disabled=True),

], fluid=True)

# combining callback for running simulation and updating graphs
@app.callback(
    [Output('simulation-results', 'data'),
     Output('power-graph', 'figure'),
     Output('battery-graph', 'figure'),
     Output('temperature-current-graph', 'figure'),
     Output('soh-cycles-graph', 'figure'), 
     Output('console-output', 'children'),
     Output('current-interval', 'data'),
     Output('update-interval', 'disabled')],
    [Input('run-button', 'n_clicks'),
     Input('update-interval', 'n_intervals')],
    [State('scenario-dropdown', 'value'),
     State('duration-input', 'value'),
     State('simulation-results', 'data'),
     State('current-interval', 'data')]
)
def update_simulation_and_graphs(n_clicks, n_intervals, selected_scenario, duration, simulation_results, current_interval):
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_id == 'run-button':
        if n_clicks == 0:
            raise PreventUpdate

        # runing the simulation
        time_step = 0.1
        solar_scenario = scenarios[selected_scenario]["solar"]
        demand_scenario = scenarios[selected_scenario]["demand"]
        simulation_results = simulate_ems(duration, time_step, solar_scenario, demand_scenario)

        # converting numpy arrays to lists for JSON serialization (for system log)
        serializable_results = [r.tolist() if isinstance(r, np.ndarray) else r for r in simulation_results]
        
        # reseting the graphs
        empty_fig = go.Figure()
        empty_output = []
        
        return serializable_results, empty_fig, empty_fig, empty_fig, empty_fig, empty_output, 0, False

    elif triggered_id == 'update-interval':
        if simulation_results is None:
            raise PreventUpdate

        # extracting data from simulation results
        time, voltage, current, temperature, soc, soh, solar_data, grid_power, battery_power, demand_data, console_output, cycle_count = simulation_results

        # incrementing the current interval
        current_interval += 1

        # calculating the number of data points to show based on the current interval
        data_points = min(len(time), current_interval * 10)  # show 10 data points per second

        # Create power graph
        power_fig = go.Figure()
        power_fig.add_trace(go.Scatter(x=time[:data_points], y=solar_data[:data_points], name='Solar Power', line=dict(color='orange')))
        power_fig.add_trace(go.Scatter(x=time[:data_points], y=demand_data[:data_points], name='Demand', line=dict(color='red')))
        power_fig.add_trace(go.Scatter(x=time[:data_points], y=grid_power[:data_points], name='Grid Power', line=dict(color='blue')))
        power_fig.add_trace(go.Scatter(x=time[:data_points], y=battery_power[:data_points], name='Battery Power', line=dict(color='green')))
        power_fig.update_layout(title='🔌 Power Flow', xaxis_title='Time (hours)', yaxis_title='Power (kW)')

        # battery graph
        battery_fig = go.Figure()
        battery_fig.add_trace(go.Scatter(x=time[:data_points], y=soc[:data_points], name='State of Charge', line=dict(color='purple')))
        battery_fig.add_trace(go.Scatter(x=time[:data_points], y=voltage[:data_points], name='Voltage', line=dict(color='cyan'), yaxis='y2'))
        battery_fig.update_layout(
            title='🔋 Battery Status', 
            xaxis_title='Time (hours)', 
            yaxis_title='SoC (%)',
            yaxis=dict(range=[80, max(soc)+5]),
            yaxis2=dict(title='Voltage (V)', overlaying='y', side='right', 
                        tickvals=[0, 25, 125, 250, 400, 550, 700, 800, 1000,  1200],
                        ticktext=['1', '2.5', '2.7', '2.9', '3.1', '3.3', '3.5', '3.7', '3.9', '4.2'])
        )

        # temperature and current graph
        temp_current_fig = go.Figure()
        temp_current_fig.add_trace(go.Scatter(x=time[:data_points], y=temperature[:data_points], name='Temperature', line=dict(color='red')))
        temp_current_fig.add_trace(go.Scatter(x=time[:data_points], y=current[:data_points], name='Current', line=dict(color='blue'), yaxis='y2'))
        temp_current_fig.update_layout(
            title='Temperature 🌡️ & Current ⚡️', 
            xaxis_title='Time (hours)', 
            yaxis_title='Temperature (°C)',
            yaxis2=dict(
                title='Current (A)', 
                overlaying='y', 
                side='right',
                range=[-100, 600],
                tickvals=[50, 100, 150, 200, 250, 300, 350, 400, 450, 500],
                ticktext=['0', '5', '10', '15', '25', '50', '75', '100', '125', '150']
            ),
            yaxis=dict(range=[min(min(temperature), 20), max(max(temperature), 100)])  # Adjust temperature range as needed
        )

        # SoH vs Cycles graph
        soh_cycles_fig = go.Figure()
        soh_cycles_fig.add_trace(go.Scatter(x=cycle_count[:data_points], y=soh[:data_points], name='State of Health', line=dict(color='green')))
        soh_cycles_fig.update_layout(
            title='State of Health vs Charge 🔋 / Discharge 🪫 Cycles', 
            xaxis_title='Charge/Discharge Cycles',
            yaxis_title='SoH (%)'
        )

        # formatting console output (UI optimization)
        formatted_output = []
        for line in console_output[:data_points]:
            parts = line.split(' - ')
            timestamp = parts[0]
            if 'EMS' in line:
                icon = '⚡'
                if "fault" in line.lower():
                    color = '#ffa500' 
                elif "discharging" in line.lower():
                    icon='🪫'
                    color = '#ffa500' 
                else:
                    color = '#28a745' 
                action = parts[1] if len(parts) > 1 else ''
                details = parts[2] if len(parts) > 2 else ''
            elif 'BMS' in line:
                icon = '🔋'
                if "WARNING" in line and "replace" in line.lower():
                    color = '#dc3545'  # red  for replacement warning
                elif "fault(s) detected" in line.lower():
                    icon ='🚨'
                    color = '#ffa500'  # orange for detected faults
                elif "cooling" in line.lower():
                    icon ='❄️'
                    color = '#007bff' 
                elif "discharging" in line.lower():
                    icon='🪫'
                    color = '#007bff' 
                else:
                    color = '#007bff' 
                action = parts[1] if len(parts) > 1 else ''
                details = parts[2] if len(parts) > 2 else ''
            else:
                icon = '📊'
                color = '#6c757d'  # Gray
                action = parts[1] if len(parts) > 1 else ''
                details = ''

            formatted_output.append(
                dbc.Card(
                    dbc.CardBody([
                        html.Div([
                            html.Span(icon, style={'fontSize': '16px', 'marginRight': '5px'}),
                            html.Span(timestamp, style={'fontWeight': 'bold', 'fontSize': '0.8em'}),
                            html.Span(action, style={'marginLeft': '5px', 'fontWeight': 'bold', 'fontSize': '0.8em'}),
                        ]),
                        html.Div(details, style={'fontSize': '0.75em', 'marginTop': '2px'}),
                    ], className="p-2"),
                    className="mb-1",
                    style={'backgroundColor': color, 'color': 'white'}
                )
            )


        # checking if we've reached the end of the simulation
        if data_points >= len(time):
            return simulation_results, power_fig, battery_fig, temp_current_fig, soh_cycles_fig, formatted_output, current_interval, True  # Disable the interval
        else:
            return simulation_results, power_fig, battery_fig, temp_current_fig, soh_cycles_fig, formatted_output, current_interval, False

    # if neither input was triggered  (UI only updates when the expected inputs are triggered)
    raise PreventUpdate

