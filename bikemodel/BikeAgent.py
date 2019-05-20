from mesa.agent import Agent
import numpy as np
import requests
import math
import pandas as pd
import json

#Constants
kmh_to_grdm = (111.32)*60/3.6
grd_to_m = (111.32*1000)

class BikeAgent(Agent):
    def __init__(self,model, unique_id, id_dest, id_orig,route,pos,speed):
    
        super().__init__(unique_id, model)
        self.moving = True
        self.unique_id = unique_id
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
        self.speed = speed

    def move(self):
        global kmh_to_grdm
        self.model.space.move_agent(self,self.pos, self.speed/kmh_to_grdm)

        
       
            
   
    def step(self):

        station_orig, station_dest = self.get_station()
        
        if((self.checkin ==False)):
            if(self.model.model_type != 1):
                station_orig, station_dest = self.check_incentive(station_orig,station_dest)
            if((station_orig.dock_bikes > 0)):
                station_orig.dock_bikes -= 1
                station_orig.free_bases += 1
                if((station_orig.priority == 1) & (self.model.model_type != 1)):
                    self.model.checkin_incentive +=1
                #Get route
                ini_pos = [station_orig.latitude,station_orig.longitude]
                fin_pos = [station_dest.latitude,station_dest.longitude]
                self.pos = ini_pos
                self.route, self.duration,self.distance = self.get_route(ini_pos,fin_pos)
                self.checkin =True
            else:
                dist, station_f = self.get_orig_station_dock_bike(station_orig)
                if(dist<self.model.walking_max_dist):
                    self.id_orig = station_f.index
                else:
                    self.model.failures += 1
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
                    if(dist<self.model.riding_max_dist):
                    #print('Estacion destino cambiada de:',station_dest.index,station_f.index)
                        self.id_dest = station_f.index
                        fin_pos = self.model.space._index_to_agent[self.id_dest].pos
                        self.route, duration_tmp,distance_tmp = self.get_route(self.pos,fin_pos)
                        self.duration += duration_tmp
                        self.distance += distance_tmp
                        self.cnt_route = 0
                
        if(self.checkout == True):
            self.model.finished_routes += 1
            station_dest.dock_bikes += 1
            station_dest.free_bases -= 1
            if((station_dest.priority == 2) & (self.model.model_type != 1)):
                    self.model.checkout_incentive +=1
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
            if((dist <500)&(np.random.choice([True,False],p=[0.9,0.1]))):
                    station_dest = station_final
                    self.distance += dist 
            elif((dist <1000)&(np.random.choice([True,False],p=[0.5,0.5]))):
                station_dest = station_final
                self.distance += dist
            elif((dist <1500)&(np.random.choice([True,False],p=[0.2,0.8]))):
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

        return station_orig,station_dest

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

        return dist_lower*grd_to_m,station_final

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


