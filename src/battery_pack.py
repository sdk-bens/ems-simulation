import numpy as np
from .battery_cell import BatteryCell

class BatteryPack:
    def __init__(self, num_cells: int, cell_capacity: float, initial_voltage: float, initial_soc: float = 80):
        """
        Initialize the battery pack with multiple cells.
        
        Args:
            num_cells (int): Number of cells in the battery pack.
            cell_capacity (float): Capacity of each cell in Ah.
            initial_voltage (float): Initial voltage of each cell in V.
            initial_soc (float): Initial state of charge of each cell in percentage (default 80%).
        """       
        self.cells = [BatteryCell(cell_capacity, initial_voltage, initial_soc) for _ in range(num_cells)]
        self.min_voltage = 2.5 
        self.max_voltage = 4.2 
        
    def get_pack_voltage(self) -> float:
        """
        Get the total voltage of the battery pack.
        
        Returns:
            float: Sum of voltages of all cells in the pack.
        """
        return sum(cell.voltage for cell in self.cells)

    def get_pack_current(self) -> float:
        """
        Get the current of the pack (assume all cells share the same current).
        
        Returns:
            float: Current of the first cell in the pack, or 0 if the pack is empty.
        """
        return self.cells[0].current if self.cells else 0

    def get_pack_temperature(self) -> float:
        """
        Get the highest temperature from any cell in the pack.
        
        Returns:
            float: Maximum temperature among all cells in the pack.
        """
        return max(cell.temperature for cell in self.cells)

    def get_pack_soc(self) -> float:
        """
        Get the average state of charge (SOC) of the pack.
        
        Returns:
            float: Mean state of charge of all cells in the pack.
        """
        return np.mean([cell.state_of_charge for cell in self.cells])
    
    def get_pack_soh(self) -> float:
        """
        Get the average state of health (SoH) of the pack.
        
        Returns:
            float: Mean state of health of all cells in the pack.
        """
        return np.mean([cell.state_of_health for cell in self.cells])
    
    def get_average_cycle_count(self) -> float:
        """
        Get the average cycle count of all cells in the pack.
        
        Returns:
            float: Mean cycle count of all cells in the pack.
        """
        return np.mean([cell.cycle_count for cell in self.cells])
