import unittest
# from src import BatteryCell
from src.battery_cell import BatteryCell
class TestBatteryCell(unittest.TestCase):
    
    def setUp(self):
        """
        Set up the test environment by creating a BatteryCell instance with initial conditions.
        """
        self.initial_voltage = 3.7
        self.cell = BatteryCell(capacity=2.0, initial_voltage=self.initial_voltage, initial_soc=80)

    def test_initial_conditions(self):
        """
        Test that the BatteryCell is initialized with the correct initial conditions.
        """
        self.assertEqual(self.cell.capacity, 2.0)
        self.assertEqual(self.cell.voltage, 3.7)
        self.assertEqual(self.cell.state_of_charge, 80)
        self.assertEqual(self.cell.temperature, 25)

    def test_update_charge(self):
        """
        Test that charging the battery increases its state of charge without exceeding 100%.
        """
        initial_soc = self.cell.state_of_charge
        self.cell.update(current=1.0, time_step=3600)  # charge for 1 hour
        self.assertGreater(self.cell.state_of_charge, initial_soc)
        self.assertLessEqual(self.cell.state_of_charge, 100)

    def test_update_discharge(self):
        """
        Test that discharging the battery decreases its state of charge.
        """
        initial_soc = self.cell.state_of_charge
        self.cell.update(current=-1.0, time_step=3600)  # Discharge for 1 hour
        self.assertLess(self.cell.state_of_charge, initial_soc)

    def test_voltage_limits(self):
        """
        Test that the battery voltage stays within safe limits during heavy discharge
        and decreases from its initial value.
        """
        # Use a more aggressive discharge current to trigger voltage drop
        initial_voltage = self.cell.voltage
        self.cell.update(current=-10.0, time_step=3600)  # Discharge heavily
        print(f"Voltage after heavy discharge: {self.cell.voltage}")  
        # self.assertGreater(self.cell.voltage, 2.5)  # Assuming 2.5V is the minimum safe voltage
        self.assertGreater(self.cell.voltage, self.cell.min_voltage)  # Check if voltage is above the minimum
        # self.assertLess(self.cell.voltage, self.cell.initial_voltage)  # Check if voltage has decreased
        self.assertLess(self.cell.voltage, initial_voltage - 1e-6)  # Check if voltage has decreased, with small tolerance
if __name__ == '__main__':
    unittest.main()