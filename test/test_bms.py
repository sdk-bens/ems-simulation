import unittest
from src.battery_pack import BatteryPack
from src.bms import BMS
from src.battery_cell import BatteryCell

class TestBMS(unittest.TestCase):

    def setUp(self):
        """
        Set up the test environment by creating a BatteryPack and BMS instance.
        """
        # Create a battery pack with varying initial voltages
        self.pack = BatteryPack(num_cells=5, cell_capacity=2.0, initial_voltage=3.7)
        # Manually set different voltages for testing
        self.pack.cells[0].voltage = 3.8
        self.pack.cells[1].voltage = 3.6
        self.pack.cells[2].voltage = 3.7
        self.pack.cells[3].voltage = 3.9
        self.pack.cells[4].voltage = 3.5
        
        self.bms = BMS(battery_pack=self.pack)

    def test_monitoring(self):
        """
        Test the monitoring function of the BMS.
        Verifies that the initial pack voltage and current are correct.
        """
        pack_voltage, pack_current, _, _, _ = self.bms.monitor()
        self.assertAlmostEqual(pack_voltage, 18.5)  # Initial voltage check
        self.assertEqual(pack_current, 0)            # Initial current is zero

    def test_balance_cells(self):
        """
        Test the cell balancing function of the BMS.
        Checks if cells with higher SOC are balanced and if all cells end up with similar SOC.
        """
        # Check initial state of charge before balancing
        initial_socs = [cell.state_of_charge for cell in self.pack.cells]
        min_initial_soc = min(initial_socs)
        
        balancing_actions = self.bms.balance_cells()
        
        # Check if balancing occurred on the cells with higher SOC
        for i, cell in enumerate(self.pack.cells):
            if initial_socs[i] > min_initial_soc:
                self.assertTrue(balancing_actions[i], f"Cell {i} should have been balanced")
            else:
                self.assertFalse(balancing_actions[i], f"Cell {i} should not have been balanced")
        
        # Verify that all cells now have the same SOC (or very close)
        final_socs = [cell.state_of_charge for cell in self.pack.cells]
        self.assertAlmostEqual(max(final_socs), min(final_socs), delta=0.1)

    def test_safety_check_normal_operation(self):
        """
        Test the safety check function during normal operation.
        Verifies that the BMS reports safe conditions under normal circumstances.
        """
        result = self.bms.ensure_safety()
        self.assertTrue(result)

    def test_safety_check_overcharge_protection(self):
        """
        Test the safety check function for overcharge protection.
        Simulates an overcharge condition and verifies that the BMS detects it.
        """
        # Simulate overcharging by setting a high voltage
        for cell in self.pack.cells:
            cell.voltage = 4.3
        
        result = self.bms.ensure_safety()
        self.assertFalse(result)

    def test_get_last_action(self):
        """
        Test the get_last_action function of the BMS.
        Performs several actions and verifies that the last action is correctly recorded.
        """
        # Perform some actions
        self.bms.monitor()
        self.bms.balance_cells()
        self.bms.ensure_safety()
        
        # Check if last action is recorded
        last_action = self.bms.get_last_action()
        self.assertIsNotNone(last_action)
        self.assertIsInstance(last_action, str)
        self.assertEqual(last_action, "Safety Check Passed")

    def test_get_actions(self):
        """
        Test the get_actions function of the BMS.
        Performs several actions and verifies that all actions are correctly recorded.
        """
        # Perform some actions
        self.bms.monitor()
        self.bms.balance_cells()
        self.bms.ensure_safety()
        
        # Check if actions are recorded
        actions = self.bms.get_actions()
        self.assertIsInstance(actions, list)
        self.assertGreater(len(actions), 0)
        self.assertEqual(actions[-1], "Safety Check Passed")  # This should be the last action performed

    def test_clear_actions(self):
        """
        Test the clear_actions function of the BMS.
        Performs actions, clears them, and verifies that the actions list is empty.
        """
        # Perform some actions
        self.bms.monitor()
        self.bms.balance_cells()
        
        # Clear actions
        self.bms.clear_actions()
        
        # Check if actions list is empty
        actions = self.bms.get_actions()
        self.assertEqual(len(actions), 0)

if __name__ == '__main__':
    unittest.main()