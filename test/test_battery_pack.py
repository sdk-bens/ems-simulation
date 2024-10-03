import unittest
# from src import BatteryPack
from src.battery_pack import BatteryPack
from src.battery_cell import BatteryCell 

class TestBatteryPack(unittest.TestCase):

    def setUp(self):
        """
        Set up a BatteryPack instance for testing.
        """
        self.pack = BatteryPack(num_cells=5, cell_capacity=2.0, initial_voltage=3.7, initial_soc=80)

    def test_initial_conditions(self):
        """
        Test the initial conditions of the BatteryPack.
        Verifies the number of cells and initial pack voltage.
        """
        self.assertEqual(len(self.pack.cells), 5)
        self.assertAlmostEqual(self.pack.get_pack_voltage(), 18.5)  # 5 * 3.7

    def test_pack_current(self):
        """
        Test the pack current calculation.
        Sets the current of one cell and checks if the pack current is correct.
        """
        self.pack.cells[0].current = 1.0
        self.assertEqual(self.pack.get_pack_current(), 1.0)

    def test_pack_temperature(self):
        """
        Test the pack temperature calculation.
        Sets the temperature of all cells and verifies the pack temperature.
        """
        for cell in self.pack.cells:
            cell.temperature = 30
        self.assertEqual(self.pack.get_pack_temperature(), 30)

    def test_pack_soc(self):
        """
        Test the pack state of charge (SOC) calculation.
        Verifies that the pack SOC matches the initial SOC set in setUp.
        """
        self.assertAlmostEqual(self.pack.get_pack_soc(), 80)

if __name__ == '__main__':
    unittest.main()