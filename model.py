#model.py
import random 
import time
from bikemodel.mesa.datacollection import DataCollector
from bikemodel.bikespace import BikeSpace
from bikemodel.mesa.agent import Agent
from bikemodel.mesa.model import  Model
from bikemodel.mesa.time import RandomActivation 
from bikemodel.TruckAgent import TruckAgent
from bikemodel.StationAgent import StationAgent
from bikemodel.BikeAgent import BikeAgent
from ast import literal_eval
import numpy as np
import requests
import math
import pandas as pd
import json

#Constants
grd_to_m = (111.32*1000)
truck_prob = [0,-1,-1,1,-1,1,1,0,1,1,-1,-1,-1,-2,1,2,-2,-1,2,2,-3,-2,3,0]

station_df = pd.read_csv('datasets/initialState-stations.csv').drop('Unnamed: 0', axis=1)
initialState_trips = pd.read_csv('datasets/initialState-trips.csv').drop('Unnamed: 0', axis=1)
#Cargamos el array de pesos de las estaciones
prob_df_u = pd.read_csv('datasets/prob_df_u.csv').drop('Unnamed: 0', axis=1).transpose()
#Cargamos la matriz de pesos de las rutas
prob_dest_df = pd.read_csv('datasets/prob_dest.csv').drop('Unnamed: 0', axis=1).transpose()

#We define Model class
class BikeModel(Model):
    """Simulación de bicicletas"""
    def __init__(self,model_type,walking_max_dist,riding_max_dist,initial_trucks,percTrips,truck_speed,bike_speed):
        self.running = True
        self.number_trips = self.get_number_trips()
        self.day = 0
        self.hour = 0
        self.minutes = 0
        self.failures = 0
        self.finished_routes = 0
        self.cnt_agents = 0
        self.stations_revised = {}
        self.checkin_incentive = 0
        self.checkout_incentive = 0
        self.walking_max_dist = walking_max_dist
        self.riding_max_dist = riding_max_dist
        self.percTrips = percTrips
        self.bike_speed = bike_speed
        self.truck_speed = truck_speed
        value = model_type
        if(value == "Base Model"):
            self.model_type = 1
        elif(value == "Incentive Model"):
            self.model_type = 2
        elif(value == "Incentive + Truck model"):
            self.model_type = 3
        else:
            self.model_type = 1
        pos1 = [40.206828, -3.409855]
        pos2 = [40.602209, -3.907157]
        self.space = BikeSpace(pos2[0], pos2[1], False, pos1[0], pos1[1])
        self.schedule = RandomActivation(self)
        self.create_stations_agents()
        if(self.model_type == 3):
            self.create_truck_agents(initial_trucks)


        self.datacollector = DataCollector(
        model_reporters={"Empty stations": lambda m: self.get_low_st(m),
                        "Full stations": lambda m: self.get_high_st(m),
                        "Failure to complete the trip": lambda m: self.failures,
                        "Successful trips": lambda m: self.finished_routes,
                        "Check-in incentives": lambda m: self.checkin_incentive,
                        "Check-out incentives": lambda m: self.checkout_incentive,
                        "Number of active bikers": lambda m: self.get_activeBikers(m)},
        agent_reporters={"Free bases": "free_bases","Dock bikes": "dock_bikes"})  

        self.datacollectorBikers = DataCollector(
            agent_reporters={"Duration":"duration", "Distance": "distance"}
            )
        
                
    def step(self):


        if(self.model_type==3):
            if(self.minutes == 0):
                change_truck = int(truck_prob[self.hour])
                if(change_truck<0):
                #Mandamos a los camiones que vuelvan a casa
                    self.change_returning(-change_truck)
                else:
                    self.create_truck_agents(change_truck)

        self.datacollector.collect(self)
        self.datacollectorBikers.collect(self)
        if(self.minutes==0):
            df = self.datacollector.get_agent_vars_dataframe()
            df.to_csv('logs/'+'logs_stations-h'+str(self.hour)+str(time.time())+'.csv')
            df = self.datacollectorBikers.get_agent_vars_dataframe()
            df.to_csv('logs/'+'logs_stations-Bikers'+str(time.time())+'.csv')
        self.schedule.step()
        self.create_bike_agents(self.number_trips[self.hour]*self.percTrips,self.hour)
        if(self.minutes<59):
            self.minutes += 1
        else:
            if(self.hour<23):
                self.hour += 1
                self.minutes = 0
            else:
                self.day +=1
                self.hour = 0
                self.minutes = 0
    
    #DataCollector methods
    @staticmethod
    def get_low_st(model):
        st_low = 0
        stations = model.space.get_stations_agents()
        for station in stations:
            if(station.dock_bikes <=0):
                st_low +=1
        return st_low

    @staticmethod
    def get_high_st(model):
        st_high = 0
        stations = model.space.get_stations_agents()
        for station in stations:
            if(station.free_bases<=0):
                st_high +=1
        return st_high

    @staticmethod
    def get_activeBikers(model):
        return len(model.space.get_bike_agents())

    #Model Methods 


        

    def reset_loc_var(self):
        self.day = 0
        self.hour = 0
        self.minutes = 0
        self.failures = 0
        self.finished_routes = 0
        self.cnt_agents = 0

    def change_returning(self,N):
        truck_agents = self.space.get_truck_agents()
        for tr_i in range(N):
            if(tr_i >= len(truck_agents)):
                break
            truck_agents[tr_i].returning = True

    def get_number_trips(self):
        
        nTrips = initialState_trips['Trips'].values
        return nTrips

    
    def get_station_pos(self, ind):
        pos = self.space._index_to_agent[ind].pos
        return pos
    
    def create_stations_agents(self):
        for i in range(len(station_df)):
            index_st = int(station_df['id'][i])
            address = station_df['address'][i]
            latitude = float(station_df['latitude'][i])
            longitude = float(station_df['longitude'][i])
            pos = [latitude,longitude]
            free_bases = int(station_df['free_bases'][i])
            #dock_bikes = total_bases - free_bases
            dock_bikes = int(station_df['dock_bikes'][i])
            total_bases = dock_bikes + free_bases
            
            a = StationAgent(self, self.cnt_agents,index_st,address, latitude, longitude, free_bases, total_bases, dock_bikes)
            self.space.place_agent(a,pos)
            self.schedule.add(a)
            self.cnt_agents += 1


    def create_truck_agents(self,N):
        global cnt_agents
        emt_pos = [40.400254, -3.675383]
        for i in range(N):
            #Creamos los camiones
            a = TruckAgent(self,self.cnt_agents, emt_pos,self.truck_speed)
            self.schedule.add(a)
            self.space.place_agent(a,emt_pos)
            self.cnt_agents +=1

    
    def create_bike_agents(self, N, hour):
        n_routes  = int(abs(np.random.normal(loc=N/60, scale=1.0, size=None)))
        """
        #Evento Wizink
        if(self.hour == 19):
            posWizink = [40.424056, -3.672555]
            stations = self.space.get_stations_agents()
            for i in range(2):
                station_close = []
                id_orig,id_dest = self.get_id()
                for j in stations:
                    if(self.space.get_distance(posWizink,[j.latitude,j.longitude]) < 0.003):
                        station_close.append(j)
                id_dest = np.random.choice(station_close).index
                ini_pos = self.get_station_pos(id_orig)
                route = []
                a =BikeAgent(self,self.cnt_agents,id_dest,id_orig,route,ini_pos,self.bike_speed)
                self.schedule.add(a)
                self.space.place_agent(a,ini_pos)
                self.cnt_agents +=1
        """
        #Comportamiento normal
        for i in range(n_routes):
            
            #Creamos los agentes 
            id_orig,id_dest = self.get_id()
            ini_pos = self.get_station_pos(id_orig)
            route = []
            a = BikeAgent(self,self.cnt_agents,id_dest,id_orig,route,ini_pos,self.bike_speed)
            self.schedule.add(a)
            self.space.place_agent(a,ini_pos)
            self.cnt_agents +=1

    
    
    def get_id(self):
        agents = self.space.get_stations_agents()[:167]
        
        prob_unplug =prob_df_u[self.hour].tolist()
        id_orig = np.random.choice(agents,p=prob_unplug).index 
        
        prob_plug=literal_eval(prob_dest_df[self.hour][id_orig])
        id_dest = np.random.choice(agents,p=prob_plug).index

        return [id_orig,id_dest]
        

