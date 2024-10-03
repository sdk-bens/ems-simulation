# Battery and Energy Management System Simulation

This project simulates a Battery Management System (BMS) and Energy Management System (EMS) for a solar-powered battery storage system. It provides a functional prototype to demonstrate the interaction between various components of the system.

## Features

- Battery cell and pack simulation
- Battery Management System (BMS) with safety checks and cell balancing
- Energy Management System (EMS) for optimizing power flow
- Solar generation and demand prediction
- Interactive dashboard for visualizing system behavior

## Project Structure

- `src/`: Source code for the simulation components
  - `battery_cell.py`: Battery cell model
  - `battery_pack.py`: Battery pack model
  - `bms.py`: Battery Management System
  - `ems.py`: Energy Management System
  - `visualization.py`: Dashboard for visualizing the simulation
- `test/`: Unit tests for each component
- `run_simulation.py`: Script to run the simulation dashboard

## Getting Started

1. Clone the repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the simulation:
   ```
   python run_simulation.py
   ```
4. Open a web browser and navigate to `http://127.0.0.1:8050/` to view the dashboard

## Running Tests

To run the unit tests:
python -m unittest discover -v -s test -p "test_*.py"




## Dashboard Features

The interactive dashboard allows you to:

- Choose different scenarios (e.g., Sunny Summer Day, Cloudy Winter Day)
- Set simulation duration
- View real-time graphs of power flow, battery status, temperature, and more
- Monitor system logs for EMS and BMS actions

## Contributing

Contributions to improve the simulation or add new features are welcome. Please submit a pull request or open an issue to discuss proposed changes.
