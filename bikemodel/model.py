#model.py
import random 
import time
from mesa.datacollection import DataCollector
from mesa.bikespace import BikeSpace
from mesa import Agent, Model
from mesa.time import RandomActivation 
from TruckAgent import TruckAgent
from StationAgent import StationAgent
import numpy as np
import requests
import math
import pandas as pd
import json

#Constants
grd_to_m = (111.32*1000)
truck_prob = [0,-1,-3,1,-1,1,1,1,1,1,-1,-1,-1,-2,2,2,-2,-1,2,2,-3,-2,4,0]

station_df = pd.read_csv('../datasets_procesados/stations_08-12.csv').drop('Unnamed: 0', axis=1)
df = pd.read_csv('../datasets_procesados/route_08_11.csv')
id_stations = pd.DataFrame({'id':station_df['id'].drop_duplicates().values})



#Cargamos el array de pesos de las estaciones
prob_df_u = pd.read_csv('../probabilidades/prob_df_0_u.csv').drop('Unnamed: 0', axis=1).transpose()
#Cargamos la matriz de pesos de las rutas
prob_df_p_default = pd.read_csv('../probabilidades/prob_dest_default.csv').drop('Unnamed: 0', axis=1).transpose()
prob_df_p_610 = pd.read_csv('../probabilidades/prob_dest_610.csv').drop('Unnamed: 0', axis=1).transpose()
prob_df_p_1316 = pd.read_csv('../probabilidades/prob_dest_1316.csv').drop('Unnamed: 0', axis=1).transpose()
prob_df_p_1821 = pd.read_csv('../probabilidades/prob_dest_1821.csv').drop('Unnamed: 0', axis=1).transpose()

#We define Model class
class BikeModel(Model):
    """Simulación de bicicletas"""
    def __init__(self,model_type):
        self.running = True
        self.number_trips = self.get_number_trips()
        self.day = 0
        self.hour = 0
        self.minutes = 0
        self.fallos = 0
        self.finished_routes = 0
        self.cnt_agents = 0
        if(model_type == "Base model"):
            self.model_type = 1
        elif(model_type == "Incentive model"):
            self.model_type = 2
        elif(model_type == "Truck model"):
            self.model_type = 3
        else:
            self.model_type = 1

        pos1 = [40.206828, -3.409855]
        pos2 = [40.602209, -3.907157]
        self.space = BikeSpace(pos2[0], pos2[1], False, pos1[0], pos1[1])
        self.schedule = RandomActivation(self)
        self.create_stations_agents()
        if(self.model_type == 3):
            self.create_truck_agents(5)


        self.datacollector = DataCollector(
        model_reporters={"Low occupancy stations": lambda m: self.get_low_st(m),
                        "High occupancy stations": lambda m: self.get_high_st(m),
                        "Failure to complete the trip": lambda m: self.fallos,
                        "Successful trips": lambda m: self.finished_routes})  
        
                
    def step(self):

        if(self.model_type==3):
            if(self.minutes == 40):
                change_truck = int(truck_prob[self.hour])
                print(change_truck)
                if(change_truck<0):
                #Mandamos a los camiones que vuelvan a casa
                    self.change_returning(-change_truck)
                else:
                    self.create_truck_agents(change_truck)

        self.datacollector.collect(self)
        self.schedule.step()
        self.create_bike_agents(self.number_trips[self.hour]/2,self.hour)
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
    
     
    @staticmethod
    def get_low_st(model):
        st_low = 0
        stations = model.space.get_stations_agents()
        for station in stations:
            if(station.dock_bikes<3):
                st_low +=1
        print(st_low)
        return st_low
    @staticmethod
    def get_high_st(model):
        st_high = 0
        stations = model.space.get_stations_agents()
        for station in stations:
            if(station.free_bases<3):
                st_high +=1
        print(st_high)
        return st_high

    #Model Methods 
    def change_returning(self,N):
        truck_agents = self.space.get_truck_agents()
        for tr_i in range(N):
            truck_agents[tr_i].returning = True

    def get_number_trips(self):
        x=[]
        for i in range(24):
            
            x.append(len(df.loc[(df['weekday']<=4)&(df['Hour']==i)])/len(df.loc[(df['weekday']<=4)].drop_duplicates('Day')))
        return x

    
    def get_station_pos(self, ind):
        pos = self.space._index_to_agent[ind].pos
        return pos
    
    def create_stations_agents(self):
        for i in id_stations.values:
            station = station_df.loc[(station_df['id'] == i[0]) &(station_df['Hour']==0)&(station_df['weekday']==0)]
            address = station['address'].values[0]
            latitude = float(station['latitude'].values[0])
            longitude = float(station['longitude'].values[0])
            pos = [latitude,longitude]
            free_bases = int(station['free_bases'].mean())
            #dock_bikes = total_bases - free_bases
            dock_bikes = int(station['dock_bikes'].mean())
            total_bases = dock_bikes + free_bases
            
            a = StationAgent(self, self.cnt_agents,address, latitude, longitude, free_bases, total_bases, dock_bikes)
            self.space.place_agent(a,pos)
            self.schedule.add(a)
            self.cnt_agents += 1


    def create_truck_agents(self,N):
        global cnt_agents
        emt_pos = [40.400254, -3.675383]
        for i in range(N):
            #Creamos los camiones
            print('Creado camión', cnt_agents)
            a = TruckAgent(self,cnt_agents, emt_pos)
            self.schedule.add(a)
            self.space.place_agent(a,emt_pos)
            cnt_agents +=1

    
    def create_bike_agents(self, N, hour):
        n_routes  = int(abs(np.random.normal(loc=N/60, scale=1.0, size=None)))
        
        for i in range(n_routes):
            
            #Creamos los agentes 
            id_orig,id_dest = self.get_id()
            ini_pos = self.get_station_pos(id_orig)
            route = []
            a = BikeAgent(self,self.cnt_agents,id_dest,id_orig,route,ini_pos)
            self.schedule.add(a)
            self.space.place_agent(a,ini_pos)
            self.cnt_agents +=1

    
    
    def get_id(self):
        agents = self.space.get_stations_agents()
        id_orig = np.random.choice(agents,p=prob_df_u[self.hour]).index
        #Index to get the prob
            
        if(self.hour >= 6 & self.hour <10):
            id_dest = np.random.choice(agents,p=prob_df_p_610[id_orig].tolist()).index

        elif(self.hour>=13 & self.hour <16):
            id_dest = np.random.choice(agents,p=prob_df_p_1316[id_orig].tolist()).index
                
        elif(self.hour>=18 & self.hour < 21):
            id_dest = np.random.choice(agents,p=prob_df_p_1821[id_orig].tolist()).index
     
        else:
            id_dest = np.random.choice(agents,p=prob_df_p_default[id_orig].tolist()).index
            
        return [id_orig,id_dest]
        


#We define Agent class
duration_array = []
distance_array = []
class BikeAgent(Agent):
    def __init__(self,model, unique_id, id_dest, id_orig,route,pos):
    
        super().__init__(unique_id, model)
        self.moving = True
        self.unique_id = unique_id
        self.agent_type = 0
        self.id_dest = id_dest
        self.id_orig = id_orig
        self.route = route
        self.cnt_route = 0
        self.checkin = False
        self.checkout = False
        self.wait_cnt = 0
        self.pos = pos
        self.duration = 0
        self.distance = 0

    def move(self):
        self.model.space.move_agent(self,self.pos, 0.0027)

        
       
            
   
    def step(self):
        station_orig, station_dest = self.get_station()
        if(self.model.model_type != 1):
            station_orig, station_dest = self.check_incentive(station_orig,station_dest)
        if((self.checkin ==False)):
            if((station_orig.dock_bikes > 0)):
                station_orig.dock_bikes -= 1
                station_orig.free_bases += 1
                #Get route
                ini_pos = [station_orig.latitude,station_orig.longitude]
                fin_pos = [station_dest.latitude,station_dest.longitude]
                self.route, self.duration,self.distance = self.get_route(ini_pos,fin_pos)
                self.checkin =True
            else:
                dist, station_f = self.get_orig_station_dock_bike(station_orig)
                if(dist<250):
                    self.id_orig = station_f.index
                else:
                    self.model.fallos += 1
                    #If failed the agent is deleted
                    self.model.schedule.remove(self)
                    self.model.space.remove_agent(self)
                

        elif((self.checkin == True)&(self.checkout ==False)):
            self.move()
            #If the pos is the last point of the route the trip has finished
            if(((self.pos[0] == self.route[-1][0])&(self.pos[1] == self.route[-1][1]))):
                if(station_dest.free_bases > 0):
                    self.checkout = True
                else:
                    dist,station_f = self.get_dest_station_free_base(station_dest)
                    if(dist<1000):
                    #print('Estacion destino cambiada de:',station_dest.index,station_f.index)
                        self.id_dest = station_f.index
                        fin_pos = self.model.space._index_to_agent[self.id_dest].pos
                        self.route, duration_tmp,distance_tmp = self.get_route(self.pos,fin_pos)
                        self.duration += duration_tmp
                        self.distance += distance_tmp
                        self.cnt_route = 0
                
        elif(self.checkout == True):
            self.model.finished_routes += 1
            station_dest.dock_bikes += 1
            station_dest.free_bases -= 1
            #After the trip the agent is deleted
            self.model.schedule.remove(self)
            self.model.space.remove_agent(self)
            

    def check_incentive(self,station_orig,station_dest):
        global grd_to_m
        if(station_orig.priority != 1):
            #Get the nearest station with High load
            dist,station_final = self.get_orig_station_high(station_orig)
            
            dist = grd_to_m*dist
            #Check the commitness of the agent
            if((dist <250)&(np.random.choice([True,False],p=[0.9,0.1]))):
                    station_dest = station_final
                    self.distance += dist 
            elif((dist <500)&(np.random.choice([True,False],p=[0.5,0.5]))):
                station_dest = station_final
                self.distance += dist
            elif((dist <750)&(np.random.choice([True,False],p=[0.2,0.8]))):
                station_dest = station_final
                self.distance += dist
                   
        if(station_dest.priority != 2):
            
            #Get the nearest station with Low load
            dist,station_final = self.get_dest_station_low(station_dest)
            dist = grd_to_m*dist
            #Check the commitness of the agent
            if((dist <250)&(np.random.choice([True,False],p=[0.9,0.1]))):
                    station_dest = station_final
                    self.distance += dist 
            elif((dist <500)&(np.random.choice([True,False],p=[0.5,0.5]))):
                station_dest = station_final
                self.distance += dist
            elif((dist <750)&(np.random.choice([True,False],p=[0.2,0.8]))):
                station_dest = station_final
                self.distance += dist
                
                
        return station_orig,station_dest

    def get_route(self,ini_pos, fin_pos):
        url = "http://localhost:8080/ors/routes"  
        querystring = {"profile":"cycling-regular", "coordinates": str(ini_pos[1])+","+ str(ini_pos[0]) +"|"+str(fin_pos[1])+","+ str(fin_pos[0]), "preference":"recommended", "geometry_format":"geojson"}
        headers = {'Content-Type': "application/json"}
        response = requests.request("GET", url, headers=headers, params=querystring)
        
        response_json = json.loads(response.text)
        distance = response_json['routes'][0]['summary']['distance']
        duration = response_json['routes'][0]['summary']['duration']
        coordenadas = []
        for coords in response_json['routes'][0]['geometry']['coordinates']:
            coordenadas.append([coords[1], coords[0]])
        return coordenadas, duration, distance     
           
    def get_station(self):
        station_orig = self.model.space._index_to_agent[self.id_orig]
        station_dest = self.model.space._index_to_agent[self.id_dest]
        return[station_orig,station_dest]

    def get_orig_station_high(self,station):
        dist_lower = math.inf
        station_final = station
        latitude_ini = station.latitude
        longitude_ini = station.longitude
        #Recorremos el array de estaciones para ver la mas cercana
        for station_2 in self.model.space.get_stations_agents():
            if(station_2 != station):
                if (station_2.priority == 1):
                    
                    latitude_dist = station_2.latitude - latitude_ini
                    longitude_dist = station_2.longitude - longitude_ini
                    
                    dist = abs(math.sqrt(math.pow(latitude_dist,2)+math.pow(longitude_dist,2)))
                    if(dist < dist_lower):
                        dist_lower = dist
                        station_final = station_2
            

                    
        return dist_lower,station_final
        
    def get_dest_station_low(self,station):
        dist_lower = math.inf
        station_final = station
        latitude_ini = station.latitude
        longitude_ini = station.longitude
        #Recorremos el array de estaciones para ver la mas cercana
        for station_2 in self.model.space.get_stations_agents():
            if(station_2 != station):
                if (station_2.priority == 2):
                    latitude_dist = station_2.latitude - latitude_ini
                    longitude_dist = station_2.longitude - longitude_ini
                    dist = abs(math.sqrt(math.pow(latitude_dist,2)+math.pow(longitude_dist,2)))
                    if(dist < dist_lower):
                        dist_lower = dist
                        station_final = station_2

    def get_orig_station_dock_bike(self,station):
        grd_to_m
        dist_lower = math.inf
        station_final = station
        latitude_ini = station.latitude
        longitude_ini = station.longitude
        #Recorremos el array de estaciones para ver la mas cercana
        for station_2 in self.model.space.get_stations_agents():
            
            if(station_2.index == station.index):
                continue
            elif (station_2.dock_bikes <= 0):
                continue
            else:
                latitude_dist = station_2.latitude - latitude_ini
                longitude_dist = station_2.longitude - longitude_ini
                dist = math.sqrt(math.pow(latitude_dist,2)+math.pow(longitude_dist,2))
                if(dist < dist_lower):
                    dist_lower = dist
                    station_final = station_2
                    
        return dist_lower*grd_to_m,station_final
        
    def get_dest_station_free_base(self,station):
        global grd_to_m
        dist_lower = math.inf
        station_final = station
        latitude_ini = station.latitude
        longitude_ini = station.longitude
        #Recorremos el array de estaciones para ver la mas cercana
        for station_2 in self.model.space.get_stations_agents():
            
            if(station_2.index == station.index):
                continue
            elif (station_2.free_bases <= 0):
                continue
            else:
                latitude_dist = station_2.latitude - latitude_ini
                longitude_dist = station_2.longitude - longitude_ini
                dist = math.sqrt(math.pow(latitude_dist,2)+math.pow(longitude_dist,2))
                if(dist < dist_lower):
                    dist_lower = dist
                    station_final = station_2
                    
        return dist_lower*grd_to_m,station_final



