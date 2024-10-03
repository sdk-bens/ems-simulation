import numpy as np
from typing import Tuple, List
from .bms import BMS
import math

class EMS:
    def __init__(self, bms: BMS, solar_capacity: float, max_grid_power: float, peak_hours: Tuple[int, int] = (18, 21)):
        """
        Initialize the Energy Management System.

        Args:
            bms (BMS): Battery Management System instance.
            solar_capacity (float): Maximum solar generation capacity in kW.
            max_grid_power (float): Maximum power that can be drawn from the grid in kW.
            peak_hours (Tuple[int, int]): Start and end hours for peak grid pricing (default: 18-21).
        """
        self.bms = bms
        self.solar_capacity = solar_capacity  # kW
        self.max_grid_power = max_grid_power  # kW
        self.time_of_day = 0
        self.last_action = "No action"
        self.peak_hours = peak_hours  # tuple for defining peak grid cost hours
        self.solar_generation = 0
        self.demand = 0
        
        # configuring thresholds
        self.charge_threshold = 0.8  # start charging when SoC is below 80%
        self.discharge_threshold = 0.2  # stop discharging when SoC is below 20%
        self.grid_charge_threshold = 0.4  # start grid charging when SoC is below 40%
        
        # battery degradation settings
        self.degradation_factor = 0.0001  # simulated degradation per cycle

        

    def predict_demand(self, time: float) -> float:
        """
        Predict energy demand based on time of day.

        Args:
            time (float): Current time of day (0-24).

        Returns:
            float: Predicted energy demand in kW.
        """

        base_demand = 3.0  # base load in kW
        day_factor = math.sin(math.pi * (time - 6) / 12) ** 2  # peak at noon
        evening_factor = 0.7 * (1 + math.cos(math.pi * (time - 18) / 6))  # higher in the evening
        
        if 6 <= time < 18:  # daytime
            demand = base_demand + 4 * day_factor
        elif 18 <= time < 24:  # evening
            demand = base_demand + 4.5 * evening_factor
        else:  # nighttime
            demand = base_demand + 1
        
        # adding some random variability to simulate real-world fluctuations
        variability = np.random.normal(0, 0.2)
        return demand + variability

    def predict_solar_generation(self, time: float) -> float:
        """
        Predict solar generation based on time of day.

        Args:
            time (float): Current time of day (0-24).

        Returns:
            float: Predicted solar generation in kW.
        """

        hour = time % 24
        
        if 6 <= hour <= 18:
            base_generation = self.solar_capacity * np.sin(np.pi * (hour - 6) / 12)
            seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * (hour - 12) / 24)  # seasonal variation
            cloud_cover = np.random.uniform(0.7, 1.0)  # simulating weather variability
            return base_generation * seasonal_factor * cloud_cover
        else:
            return 0

    def optimize_energy_flow(self, time_of_day: float) -> Tuple[float, float]:
        """
        Optimize energy flow based on current state, time of day, and system constraints.

        This method determines the optimal energy flow between the grid, solar generation,
        and battery storage. It takes into account factors such as time-of-day pricing,
        battery state of charge, temperature, voltage, and current limits.

        Args:
            time_of_day (float): Current time of day (0-24).

        Returns:
            Tuple[float, float]: A tuple containing:
                - grid_power (float): Optimized power drawn from or fed to the grid in kW.
                - battery_power (float): Optimized power charged to or discharged from the battery in kW.
                  Positive values indicate charging, negative values indicate discharging.

        Note:
            This method updates the `last_action` attribute with a description of the decision made.
        """

        voltage, current, temperature, soc, soh = self.bms.monitor()
        grid_cost_multiplier = 1.0

        max_charge_rate = self.bms.battery_pack.cells[0].capacity * 0.5  # 0.5C charge rate
        max_discharge_rate = self.bms.battery_pack.cells[0].capacity * 1  # 1C discharge rate

        # adjusting max charge/discharge rates based on SoH
        soh_factor = soh / 100
        max_charge_rate *= soh_factor
        max_discharge_rate *= soh_factor

        # peak hours cost higher grid power (dynamic pricing simulation)
        if self.peak_hours[0] <= time_of_day <= self.peak_hours[1]:
            grid_cost_multiplier = 1.5

        # temperature-based adjustments
        if temperature > 40:  # high temperature scenario
            max_charge_rate = 0.5 * self.max_grid_power  # reduce charging rate
        elif temperature < 0:  # low temperature scenario
            max_charge_rate = 0.7 * self.max_grid_power  # reduce charging rate less severely
        else:
            max_charge_rate = self.max_grid_power

        # initialize max_discharge_rate
        max_discharge_rate = self.max_grid_power

        # voltage-based adjustments
        if voltage > 4.1:  # high voltage scenario
            max_charge_rate = min(max_charge_rate, 0.3 * self.max_grid_power)  # Further reduce charging rate
        elif voltage < 3.2:  # low voltage scenario
            max_discharge_rate = 0.5 * self.max_grid_power  # reduce discharging rate

        if soc < self.grid_charge_threshold and temperature < 45:  # temperature check
            grid_power = min(max_charge_rate * grid_cost_multiplier, self.demand - self.solar_generation)
            battery_power = max(0, grid_power)
            self.last_action = "Grid charging (temperature adjusted)"
        
        elif self.solar_generation > self.demand and soc < self.charge_threshold and temperature < 45:
            battery_power = min(self.solar_generation - self.demand, max_charge_rate)
            grid_power = max(0, self.demand - self.solar_generation)
            self.last_action = "Charging battery with excess solar (temperature adjusted)"
        
        elif self.solar_generation < self.demand and soc > self.discharge_threshold and voltage > 3.2:
            battery_power = min(self.demand - self.solar_generation, max_discharge_rate)
            grid_power = max(0, self.demand - self.solar_generation - battery_power)
            self.last_action = "Discharging battery to meet demand (voltage adjusted)"
        
        else:
            battery_power = 0
            grid_power = max(0, self.demand - self.solar_generation)
            self.last_action = "Balancing grid and solar (no battery action due to constraints)"

        # current-based safety check
        if abs(current + battery_power / voltage) > self.bms.battery_pack.cells[0].capacity * 2:  # 2C rate limit
            battery_power = 0
            grid_power = max(0, self.demand - self.solar_generation)
            self.last_action = "Current limit reached, using grid power only"

        return grid_power, battery_power

    def update(self, time: float, time_step: float, solar_generation: float, demand: float):
        """
        Update system state based on the current time, time step, solar generation, and demand.

        Args:
            time (float): Current time of day (0-24).
            time_step (float): Time step for the simulation in hours.
            solar_generation (float): Actual solar generation in kW.
            demand (float): Actual energy demand in kW.

        Returns:
            Tuple[float, float, float]: Solar generation, grid power, and battery power in kW.
        """

        self.time_of_day = time
        self.solar_generation = solar_generation
        self.demand = demand
        
        grid_power, battery_power = self.optimize_energy_flow(time)

        # handling faults before updating battery state
        unresolved_faults = self.bms.handle_faults()


         # checking SoH and get replacement message
        replacement_message = self.bms.check_soh_and_recommend_replacement()
        if replacement_message:
            self.last_action = replacement_message

        if not unresolved_faults:
            if battery_power != 0:
                battery_current = battery_power * 1000 / self.bms.battery_pack.get_pack_voltage()
                
                for cell in self.bms.battery_pack.cells:
                    cell.update(battery_current, time_step)
                    self.apply_battery_degradation(cell)
            
            # balancing cells and ensuring safety after updates
            self.bms.balance_cells()
            safety_check_result = self.bms.ensure_safety()
        else:
            # if there are unresolved faults, adjust the energy flow
            self.last_action = f"System limited due to faults: {', '.join(unresolved_faults)}"
            battery_power = 0  # prevent battery usage if there are unresolved faults
            grid_power = max(0, demand - solar_generation)

        return self.solar_generation, grid_power, battery_power
    

    def apply_battery_degradation(self, cell):
        """
        Simulate battery degradation over time.

        Args:
            cell: Battery cell object to apply degradation to.
        """

        cell.state_of_charge = max(0, cell.state_of_charge - self.degradation_factor * (1 - cell.state_of_charge))

    def get_system_state(self) -> dict:
        """
        Get the current state of the system.

        Returns:
            dict: A dictionary containing current system state information.
        """

        voltage, current, temperature, soc, soh = self.bms.monitor()
        
        return {
            "battery_voltage": voltage,
            "battery_current": current,
            "battery_temperature": temperature,
            "battery_soc": soc,
            "battery_soh": soh,
            "solar_generation": self.solar_generation,
            "demand": self.demand,
            "last_action": self.last_action,
            "grid_power": self.demand - self.solar_generation,  # simplified calculation
            "battery_power": current * voltage / 1000,  # convert to kW
        }

    def get_last_action(self) -> str:
        """
        Return the last action taken by the EMS.

        Returns:
            str: Description of the last action taken.
        """
        return self.last_action

    def get_bms_actions(self) -> List[str]:
        """
        Get the actions performed by the BMS.

        Returns:
            List[str]: List of actions performed by the Battery Management System.
        """
        return self.bms.get_actions()