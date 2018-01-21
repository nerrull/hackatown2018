import numpy as np
def calculate_max_number_of_panels(usable_area):
    return  np.floor(usable_area *0.7 / 2) # x m^2/ 2 m^2

def calculate_price_per_panel(num_panels):
    cost_per_panel = 350
    return cost_per_panel*num_panels

def calculate_installation_cost(ease, num_panels):
    fixed_rate = 1000 - 500*ease
    cost_per_panel = 50
    panel_installation_cost = num_panels*cost_per_panel
    return fixed_rate + panel_installation_cost

def calculate_residential_returns(years):
    cost_per_kilowatt=0.10 #doulars
    return calculate_returns(cost_per_kilowatt, years)

def calculate_commercial_returns(years):
    cost_per_kilowatt=0.07#doulars
    return calculate_returns(cost_per_kilowatt, years)

# Returns = numPanels * calculate_*_returns

def calculate_residential_compound_returns(years):
    cost_per_kilowatt=0.10 #doulars
    return calculate_compound_returns(cost_per_kilowatt, years)

def calculate_commercial_compound_returns(years):
    cost_per_kilowatt=0.07#doulars
    return calculate_compound_returns(cost_per_kilowatt, years)

def calculate_returns(cost_per_kilowatt, years):
    panel_kw = 378  # kw/h
    degradation_factor_first_year = 0.975
    degradation_factor = 0.995
    returns = []
    returns.append(panel_kw * cost_per_kilowatt)
    panel_kw = panel_kw * degradation_factor_first_year
    for i in range(1, years):
        returns.append(panel_kw * cost_per_kilowatt + returns[-1])
        panel_kw = panel_kw * degradation_factor
    return returns


def calculate_compound_returns(cost_per_kilowatt, years):
    panel_kw = 378  # kw/h
    degradation_factor_first_year = 0.975
    degradation_factor = 0.995
    returns = []
    returns.append(panel_kw * cost_per_kilowatt)
    panel_kw = panel_kw * degradation_factor_first_year
    for i in range(1, years):
        returns.append(panel_kw * cost_per_kilowatt*(1+returns[i-1]/900) + returns[-1])
        panel_kw = panel_kw * degradation_factor
    return returns


if __name__ == "__main__":
    residential_returns = calculate_residential_returns(25)
    commercial_returns = calculate_commercial_returns(25)
    residential_compound_returns = calculate_residential_compound_returns(25)
    commercial_compound_returns = calculate_commercial_compound_returns(25)
    print residential_returns