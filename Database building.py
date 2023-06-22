#%% Importing packages

import json
import pandas as pd
import pint
import mario
import plotly.express as px

#%% Importing the color palette

Colors = {'Non-Renewable Electricity': '#A48806',
 'Services': '#00CC66',
 'Other manufacturing': '#F7921C',
 'Transport': '#7DBFEC',
 'Primary': '#808080',
 'Metal products': '#FBBE75',
 'Gas and heating': '#FA4F46',
 'Households': '#E59FEF',
 'Petroleum and chemicals': '#000000',
 'Renewable Electricity': '#F9DC5C',
 'Transport and electrical equipment': '#3DA0E2',
 'Construction': '#844A04',}

#%% Define the unit registry
ureg = pint.UnitRegistry()

# Load project paths
with open('Project paths.json', 'r') as f:
    P = json.load(f)

# Load database
World = mario.hybrid_sut_exiobase(path=P['exio_H']['path'], extensions=["resource","Land","Emiss",])

# Aggregate database
World.aggregate('Aggregation/Aggregation EU RoW.xlsx')

# Get some numbers
sN = slice(None)
region = 'EU'
level = 'Commodity' # Commodity or Activity
items = World.search(level, 'Natural gas', ignore_case=False)

prod = World.X.loc[(region,level,items)]
unit = World.units[level].loc[items]
cons = World.Z.loc[(sN,level,items),region].sum().sum() + World.Y.loc[(sN,level,items),region].sum().sum()

# Print results
print(prod)
print(prod/prod.sum())
print(unit)

# Define GHG and GWP
ghg =  ['N2O', 'CH4', 'CO2 - fossil', 'CO2 - biogenic']
gwp = [298, 25, 1, 1]

# Calculate emissions
emi = World.E.loc[ghg]
emi_ghg = emi.T.multiply(gwp).T
emi_ghg_reg = emi_ghg.sum().sum(level=0)
emi_ghg_tot = (emi_ghg.sum().sum() * ureg('tonne')).to('Gton')

# Calculate shock
World.shock_calc('Shock/Shock - EU power to low carbon.xlsx', z=True, scenario='EU power to low carbon.xlsx')

# Aggregate for result analysis
World.get_aggregation_excel('Aggregation/Aggregation_template.xlsx')
World_agg = World.aggregate('Aggregation/Aggregation for results analysis.xlsx', inplace=False)

# Calculate impact
impact = World_agg.query(['E'], base_scenario='baseline', scenarios=['EU power to low carbon.xlsx'])
impact.rename_axis('Account', inplace=True)

# Plot results
plot = impact.loc[ghg,(sN,'Activity')].T.multiply(gwp).T.stack([0,1,2]).to_frame().reset_index()
plot.columns = ['GHG','Region','Level','Sector','Value']

emi_ghg_hh = World_agg.EY.loc[ghg].T.multiply(gwp).T.sum().groupby(['Region','Item']).sum() * 1e-9
emi_ghg_in = World_agg.E.loc[ghg,(sN,'Activity')].T.multiply(gwp).T.sum().groupby(['Region','Item']).sum() * 1e-9
global_ghg = emi_ghg_hh.append(emi_ghg_in)

#%% Plot sunburst chart
fig = px.sunburst(global_ghg.reset_index(), path=['Region','Item'], values=0, color='Item', color_discrete_map=Colors)
fig.update_layout(font_family='Trebuchet MS', template='plotly_white', title_text=f'Global GHG emissions {global_ghg.sum().sum():.2f} Gton')
fig.show()
fig.write_html('Plot/Global emissions.html')

ghg_saved = (plot.sum().Value * ureg('tonne')).to('Gton') 

#%% Plot bar chart
fig = px.bar(plot, x="GHG", y="Value", color="Sector", pattern_shape="Region", color_discrete_map=Colors)
fig.update_layout(font_family='Trebuchet MS', template='plotly_white', legend_title_text='Sector, Region (hatched fill is RoW)', title_text=f'Saved GHG emissions: {-ghg_saved:.2f}')
fig.show()
fig.write_html('Plot/Saved GHG emissions.html')

#%% Check emission factors
power_carb_int = World.e.loc['CO2 - fossil',(sN,sN,World.search('Activity','Production of electricity'))]
(power_carb_int[16] * ureg('ton/TJ')).to('kg/MWh')
