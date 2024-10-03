class BatteryCell:
    def __init__(self, capacity: float, initial_voltage: float, initial_soc: float = 80):
        """
        Initialize a battery cell.

        Args:
            capacity (float): The capacity of the battery cell in Ampere-hours (Ah).
            initial_voltage (float): The initial voltage of the battery cell in Volts (V).
            initial_soc (float, optional): The initial state of charge of the battery cell as a percentage. Defaults to 50%.

        Attributes:
            capacity (float): The capacity of the battery cell in Ah.
            voltage (float): The current voltage of the battery cell in V.
            current (float): The current flowing through the cell in Amperes (A). Initialized to 0.
            temperature (float): The temperature of the battery cell in degrees Celsius (°C). Initialized to 25°C.
            state_of_charge (float): The current state of charge of the battery cell as a percentage.
            internal_resistance (float): The internal resistance of the battery cell in Ohms. Initialized to 0.5 Ohm.
            nominal_voltage (float): The nominal voltage of the battery cell, set to the initial voltage.
            min_voltage (float): The minimum voltage of the battery cell, set to 2.5V.
            voltage_tolerance (float): The voltage tolerance of the battery cell, set to 0.01V.
        """
        self.capacity = capacity  # Ah
        self.voltage = initial_voltage  # V
        self.current = 0  # A
        self.temperature = 25  # °C
        self.state_of_charge = initial_soc  # %
        self.internal_resistance = 0.5  # Ohm
        self.nominal_voltage = initial_voltage
        self.min_voltage = 2.5
        self.voltage_tolerance = 0.01
        self.state_of_health = 100 
        self.cycle_count = 0
        self.state_of_charge = initial_soc
        self.last_soc = initial_soc

    def update_state_of_health(self):
        # simple SoH model based on cycle count
        cycle_life = 1000  # assumin 1000 is the cycle life
        self.state_of_health = max(0, 100 - (self.cycle_count / cycle_life) * 100)

    def update(self, current: float, time_step: float):
        """
        Update cell state based on current and time.
        
        Args:
            current (float): The current flowing through the cell (A). Positive for charging, negative for discharging.
            time_step (float): The duration of the update step (s).
        
        This method updates the cell's state of charge, voltage, and temperature based on the applied current and time step.
        """
        self.current = current
        # calculating change in charge and update the state of charge
        charge_change = (current * time_step / 3600) / self.capacity  # convert time step to hours
        self.state_of_charge = max(0, min(100, self.state_of_charge + charge_change * 100))
        self.cycle_count += abs(charge_change)
        self.update_state_of_health()

        
        # calculating open circuit voltage (OCV) based on the state of charge
        ocv = self.nominal_voltage + 0.2 * (self.state_of_charge / 100 - 0.5)  # Open Circuit Voltage
        voltage_drop = abs(current) * self.internal_resistance

        # updating voltage based on charging/discharging state
        if current < 0:  # Discharging
            self.voltage = max(self.min_voltage + self.voltage_tolerance, ocv - voltage_drop)
        else:  # charging
            self.voltage = ocv + voltage_drop

        # updating temperature based on current flow and cooling
        if abs(current) > 0:
            heat_generation = (current ** 2) * self.internal_resistance * time_step / 3600  # J
            heat_capacity = 3  # J/kg/K (approximate for a lithium-ion cell)
            temperature_rise = heat_generation / heat_capacity
            cooling_rate = 0.01 * (self.temperature - 25) * time_step / 3600  # Natural cooling

        self.temperature += temperature_rise - cooling_rate
        self.temperature = max(25, min(60, self.temperature))  # limiting temperature between 25°C and 60°C


        # updating cycle count
        if (self.state_of_charge > self.last_soc and self.last_soc < 20) or \
           (self.state_of_charge < self.last_soc and self.last_soc > 80):
            self.cycle_count += 0.5  # Half cycle completed
        
        self.last_soc = self.state_of_charge

    def charge(self, current: float):
        """
        Charge the cell with the given current.
        
        Args:
            current (float): The charging current (A).
        
        This method calls the update function with a positive current and a 1 second time step.
        """
        self.update(current, 1/3600)  # assuming 1 second charge duration
        

    def discharge(self, current: float):
        """
        Discharge the cell with the given current.
        
        Args:
            current (float): The discharging current (A).
        
        This method calls the update function with a negative current and a 1 second time step.
        """
        self.update(-current, 1/3600)  # assuming 1 second discharge duration

    

    
