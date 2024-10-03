import unittest
from src.ems import EMS
from src.bms import BMS
from src.battery_pack import BatteryPack
from src.battery_cell import BatteryCell

class TestEMS(unittest.TestCase):

    def setUp(self):
        self.battery_capacity = 2.0  # Ah
        self.initial_voltage = 3.7  # V
        self.num_cells = 5
        
        self.battery_pack = BatteryPack(num_cells=self.num_cells, cell_capacity=self.battery_capacity, initial_voltage=self.initial_voltage, initial_soc=80)
        self.bms = BMS(battery_pack=self.battery_pack)
        
        self.ems = EMS(bms=self.bms, solar_capacity=5.0, max_grid_power=3.0)

    def test_predict_demand_daytime(self):
        """Test demand prediction during daytime."""
        demand = self.ems.predict_demand(12)  # Noon
        self.assertGreater(demand, 3.0)  # Expecting demand to be higher than base load

    def test_predict_demand_evening(self):
        """Test demand prediction during evening."""
        demand = self.ems.predict_demand(19)  # 7 PM
        self.assertGreater(demand, 3.0)  # Expecting demand to be higher than base load

    def test_predict_demand_night(self):
        """Test demand prediction during night time."""
        demand = self.ems.predict_demand(2)  # 2 AM
        self.assertLess(demand, 5.0)  # Expecting lower demand at night
        self.assertGreater(demand, 3.0)  # But still above base load

    def test_predict_solar_generation(self):
        """Test solar generation prediction during peak sunlight hours."""
        generation = self.ems.predict_solar_generation(12)  # Noon
        self.assertGreater(generation, 0.5 * self.ems.solar_capacity)
        self.assertLess(generation, 1.2 * self.ems.solar_capacity)

    def test_predict_solar_generation_night(self):
        """Test solar generation prediction during night hours."""
        generation = self.ems.predict_solar_generation(1)  # 1 AM
        self.assertEqual(generation, 0)

    def test_optimize_energy_flow(self):
        """Test energy flow optimization logic."""
        self.bms.battery_pack.cells[0].state_of_charge = 50  # Set SOC to a mid-level for testing
        self.ems.solar_generation = 3.0  # Set a sample solar generation
        self.ems.demand = 4.0  # Set a sample demand
        grid_power, battery_power = self.ems.optimize_energy_flow(12)  # Noon
        
        self.assertGreaterEqual(grid_power, 0)
        self.assertIsInstance(battery_power, float)

    def test_optimize_energy_flow_temperature_low(self):
        """Test energy flow optimization with low temperature."""
        self.bms.battery_pack.cells[0].temperature = 0  # Set temperature low
        self.bms.battery_pack.cells[0].state_of_charge = 30  # Set SOC low
        self.ems.solar_generation = 4.0
        self.ems.demand = 3.0
        grid_power, battery_power = self.ems.optimize_energy_flow(12)
        
        self.assertGreaterEqual(grid_power, 0)
        self.assertGreaterEqual(battery_power, 0)  # Expect positive battery power (charging)

    def test_optimize_energy_flow_peak_hours(self):
        """Test energy flow optimization during peak hours."""
        self.bms.battery_pack.cells[0].state_of_charge = 60
        self.ems.solar_generation = 1.0
        self.ems.demand = 4.0
        grid_power, battery_power = self.ems.optimize_energy_flow(19)  # Peak hour
        
        self.assertLessEqual(grid_power, self.ems.max_grid_power * 1.5)  # Check if grid power is limited by peak hour multiplier

    def test_optimize_energy_flow_max_discharge_power(self):
        """Test energy flow optimization with max discharge power limit."""
        self.bms.battery_pack.cells[0].voltage = 4.1  # Set voltage high to limit discharge power
        self.bms.battery_pack.cells[0].state_of_charge = 90  # Set SOC high to trigger discharging
        self.ems.solar_generation = 1.0
        self.ems.demand = 4.0
        grid_power, battery_power = self.ems.optimize_energy_flow(12)
        
        max_discharge_power = (4.1 - self.bms.battery_pack.min_voltage) * self.bms.battery_pack.cells[0].capacity / 1000
        self.assertGreaterEqual(battery_power, -max_discharge_power)

    def test_update_system_state(self):
        """Test updating the system state."""
        solar_generation, grid_power, battery_power = self.ems.update(time=12, time_step=1, solar_generation=3.0, demand=4.0)
        
        self.assertGreaterEqual(solar_generation, 0)
        self.assertGreaterEqual(grid_power, 0)
        self.assertIsInstance(battery_power, float)

    def test_get_system_state(self):
        """Test getting the current state of the system."""
        state = self.ems.get_system_state()
        
        self.assertIn("battery_voltage", state)
        self.assertIn("battery_current", state)
        self.assertIn("battery_temperature", state)
        self.assertIn("battery_soc", state)
        self.assertIn("solar_generation", state)
        self.assertIn("demand", state)

    def test_get_bms_actions(self):
        """Test getting BMS actions."""
        actions = self.ems.get_bms_actions()
        self.assertIsInstance(actions, list)

    # def test_apply_battery_degradation(self):
    #     """Test battery degradation application."""
    #     initial_soc = self.bms.battery_pack.cells[0].state_of_charge
    #     self.ems.apply_battery_degradation(self.bms.battery_pack.cells[0])
    #     self.assertLess(self.bms.battery_pack.cells[0].state_of_charge, initial_soc)

    def test_get_last_action(self):
        """Test getting the last action."""
        self.ems.last_action = "Test action"
        self.assertEqual(self.ems.get_last_action(), "Test action")

if __name__ == '__main__':
    unittest.main()