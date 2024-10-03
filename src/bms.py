import numpy as np
from typing import List, Tuple
from .battery_pack import BatteryPack

class BMS:
    def __init__(self, battery_pack: BatteryPack):
        """
        Initialize the Battery Management System (BMS) with a battery pack.

        Args:
            battery_pack (BatteryPack): The battery pack to be managed.
        """
        self.battery_pack = battery_pack
        self.num_cells = len(battery_pack.cells)
        self.balancing_step = 0.01 
        self.min_soh = 80  # minimum acceptable SoH  
        self.replacement_message = ""

        # defining safe operating area (SOA) parameters
        self.min_cell_voltage = 2.5  # V
        self.max_cell_voltage = 4.2  # V
        self.max_charge_current = battery_pack.cells[0].capacity * 2  
        self.max_discharge_current = battery_pack.cells[0].capacity * 20 
        self.min_temperature = -20  # °C
        self.max_temperature = 60  # °C
        self.actions = []
        self.last_action = "Initialized"
        

    def monitor(self) -> Tuple[float, float, float, float, float]:
        """
        Monitor the battery pack and return key metrics.

        Returns:
            Tuple[float, float, float, float]: A tuple containing:
                - pack_voltage (float): The total voltage of the battery pack.
                - pack_current (float): The current flowing through the battery pack.
                - pack_temperature (float): The average temperature of the battery pack.
                - pack_soc (float): The state of charge of the battery pack.
        """
        pack_voltage = self.battery_pack.get_pack_voltage()
        pack_current = self.battery_pack.get_pack_current()
        pack_temperature = self.battery_pack.get_pack_temperature()
        pack_soc = self.battery_pack.get_pack_soc()
        pack_soh = self.battery_pack.get_pack_soh()
        
        self.actions.append("Monitoring")
        return pack_voltage, pack_current, pack_temperature, pack_soc, pack_soh
    
    def soc_to_voltage(self, soc: float) -> float:
        """
        Convert State of Charge (SOC) to voltage using a simplified linear relationship.

        Args:
            soc (float): The State of Charge as a percentage (0-100).

        Returns:
            float: The corresponding voltage.
        """
        min_voltage = 3.0
        max_voltage = 4.2
        return min_voltage + (max_voltage - min_voltage) * (soc / 100)

    def balance_cells(self) -> List[bool]:
        """
        Balance cells based on state of charge differences.

        Returns:
            List[bool]: A list of boolean values indicating which cells were balanced.
        """
        cells = self.battery_pack.cells
        cell_socs = [cell.state_of_charge for cell in cells]
        min_soc = min(cell_socs)
        
        balancing_actions = [False] * len(cells)
        
        for i, cell in enumerate(cells):
            if cell.state_of_charge > min_soc:
                target_voltage = self.soc_to_voltage(min_soc)
                while cell.voltage > target_voltage:
                    cell.voltage -= self.balancing_step
                    balancing_actions[i] = True

        if any(balancing_actions):
            self.actions.append("Cell Balancing")
        else:
            self.actions.append("No Balancing Needed")
        
        return balancing_actions

    def ensure_safety(self) -> bool:
        """
        Ensure that the pack is operating within safe limits.

        Returns:
            bool: True if the pack is operating safely, False otherwise.
        """
        faults = self.detect_faults()
        
        if faults:
            self.actions.append(f"Safety Check Failed: {', '.join(faults)}")
            return False
        
        self.actions.append("Safety Check Passed")
        return True

    def detect_faults(self) -> List[str]:
        """
        Detect faults in the battery pack.

        Returns:
            List[str]: A list of detected faults as strings.
        """
        faults = []
        pack_voltage, pack_current, pack_temperature, pack_soc, pack_soh = self.monitor()

        if pack_soh < self.min_soh:
            faults.append("Low pack state of health")
            self.check_soh_and_recommend_replacement()

        # checking individual cell SoH
        for i, cell in enumerate(self.battery_pack.cells):
            if cell.state_of_health < self.min_soh:
                faults.append(f"Cell {i} low state of health")

        # voltage based faults
        if pack_voltage > self.max_cell_voltage * self.num_cells:
            faults.append("Pack overvoltage")
        elif pack_voltage < self.min_cell_voltage * self.num_cells:
            faults.append("Pack undervoltage")

        # current based faults
        if abs(pack_current) > self.max_discharge_current:
            faults.append("Overcurrent")

        # temperature based faults
        if pack_temperature > self.max_temperature:
            faults.append("Pack overtemperature")
        elif pack_temperature < self.min_temperature:
            faults.append("Pack undertemperature")

        # cell level faults
        for i, cell in enumerate(self.battery_pack.cells):
            if cell.voltage > self.max_cell_voltage:
                faults.append(f"Cell {i} overvoltage")
            elif cell.voltage < self.min_cell_voltage:
                faults.append(f"Cell {i} undervoltage")
            if cell.temperature > self.max_temperature:
                faults.append(f"Cell {i} overtemperature")
            elif cell.temperature < self.min_temperature:
                faults.append(f"Cell {i} undertemperature")

        if faults:
            self.actions.append(f"Fault(s) Detected: {', '.join(faults)}")
        else:
            self.actions.append("No Faults Detected")
        
        return faults

    def handle_faults(self) -> List[str]:
        """
        Handle detected faults and return unresolved ones.

        Returns:
            List[str]: A list of unresolved faults as strings.
        """
        faults = self.detect_faults()
        unresolved_faults = []

        for fault in faults:
            if "overvoltage" in fault or "undervoltage" in fault:
                try:
                    cell_index = int(fault.split()[1])
                    if fault == "Low pack state of health":
                        unresolved_faults.append(fault)
                        self.actions.append("Low SoH Detected - Replacement Recommended")
                    elif "overvoltage" in fault:
                        self.battery_pack.cells[cell_index].discharge(0.1)  # Discharge by 0.1A
                        self.actions.append(f"Discharging Cell {cell_index}")
                    elif "undervoltage" in fault:
                        self.battery_pack.cells[cell_index].charge(0.1)  # Charge by 0.1A
                        self.actions.append(f"Charging Cell {cell_index}")
                except (ValueError, IndexError):
                    unresolved_faults.append(fault)
            elif "overtemperature" in fault:
                for cell in self.battery_pack.cells:
                    cell.temperature -= 2  # cool down by 1°C
                self.actions.append("Cooling Pack")
            elif "undertemperature" in fault:
                for cell in self.battery_pack.cells:
                    cell.temperature += 2  # warm up by 1°C
                self.actions.append("Heating Pack")
            else:
                unresolved_faults.append(fault)

        self.actions.append("Fault Handling Complete")
        return unresolved_faults
    
    def check_soh_and_recommend_replacement(self) -> str:
        """
        Check if the State of Health (SoH) is below the minimum threshold
        and recommend replacement if necessary.

        Returns:
            str: A message recommending replacement if SoH is below threshold, or an empty string otherwise.
        """
        pack_soh = self.battery_pack.get_pack_soh()
        if pack_soh < self.min_soh:
            self.replacement_message = f"WARNING: Battery pack SoH ({pack_soh:.2f}%) is below the minimum threshold ({self.min_soh}%). Please replace the device."
            self.actions.append("Replacement Recommended")
            return self.replacement_message
        return ""
    
    def get_actions(self) -> List[str]:
        """
        Return all actions taken by the BMS.

        Returns:
            List[str]: A list of all actions taken by the BMS.
        """
        return self.actions

    def get_last_action(self) -> str:
        """
        Return the last action taken by the BMS.

        Returns:
            str: The last action taken by the BMS, or "No actions recorded" if no actions have been taken.
        """
        return self.actions[-1] if self.actions else "No actions recorded"


    def clear_actions(self):
        """
        Clear the actions list.
        """
        self.actions = []

    def update_charge_state(self, current: float):
        """
        Update charging state based on current direction.

        Args:
            current (float): The current flowing through the battery pack.
        """
        if current > 0:
            self.last_action = "Charging"
        elif current < 0:
            self.last_action = "Discharging"
        else:
            self.last_action = "Idle"

    def get_balancing_info(self):
        """
        Get information about cell balancing.

        Returns:
            dict: A dictionary containing:
                - cells_to_discharge (List[int]): Indices of cells that need to be discharged.
                - avg_voltage (float): The average voltage of all cells.
        """
        cells_to_discharge = []
        avg_voltage = sum(cell.voltage for cell in self.battery_pack.cells) / len(self.battery_pack.cells)
        threshold = 0.05  # 50mV threshold for balancing

        for i, cell in enumerate(self.battery_pack.cells):
            if cell.voltage > avg_voltage + threshold:
                cells_to_discharge.append(i)

        return {
            'cells_to_discharge': cells_to_discharge,
            'avg_voltage': avg_voltage
        }
    
    def get_replacement_message(self) -> str:
        """
        Get the current replacement message.

        Returns:
            str: The current replacement message, or an empty string if no replacement is needed.
        """
        return self.replacement_message