#server.py
from model import BikeModel
#Debugger
import pdb; 
#Chart
from bikemodel.modules.ChartVisualization import ChartModule
#Number of agents slider
from bikemodel.UserParam import UserSettableParameter
from bikemodel.Visualization import ModularServer
   
occupancy_chart = ChartModule([{"Label": "Full stations", "Color": "#2488ff"},
                          {"Label": "Empty stations", "Color": "#5AEDFF"}
                          ])
failures_chart = ChartModule([{"Label": "Failure to complete the trip", "Color": "#233189"},
              {"Label": "Check-in incentives", "Color": "#A2FFC9"},
              {"Label": "Check-out incentives", "Color": "#455FFF"}
                          ])
success_chart = ChartModule([
              {"Label": "Successful trips", "Color": "#2488ff"}])
activeAgents_chart = ChartModule([{"Label": "Number of active bikers", "Color": "#2488ff"}])

model_params = {
    "model_type": UserSettableParameter("choice", "Model to execute", value="Select a model",
                                           choices=list(["Base Model", "Incentive Model", "Incentive + Truck model"])),
    "percTrips": UserSettableParameter("slider", "Percentage of real trips (%)", 0.25, 0, 1, 0.01),
    "walking_max_dist": UserSettableParameter("slider", "Max. distance to walk (m)", 250, 0, 1000, 10),
    "riding_max_dist": UserSettableParameter("slider", "Max. distance to ride (m)", 1000, 0, 2000, 10),
    "initial_trucks": UserSettableParameter("slider", "Number of initial trucks", 5, 0, 10, 1),
    "truck_speed": UserSettableParameter("slider", "Truck speed (km/h)", 40, 0, 80, 2),
    "bike_speed": UserSettableParameter("slider", "Bike speed (km/h)", 12, 0, 30, 1)
}

#pdb.set_trace()
textDescript = "Bicycle traffic using OpenStreetMap routing service designed by Alberto López Santiago - GSI 2018-2019 ©"
server = ModularServer(BikeModel, "Bipy",[occupancy_chart,success_chart,failures_chart,activeAgents_chart],textDescript,model_params)