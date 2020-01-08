from mesa.agent import Agent
import numpy as np
import requests
import math
import pandas as pd
import json
kmh_to_grdm = 111.32*60/3.6
grd_to_m = (111.32*1000)


class TruckAgent(Agent):
    def __init__(self,model, index, pos,speed):
    
        super().__init__(index, model)
        self.index = index
        self.moving = False
        self.working = False
        self.pos = pos
        self.speed = speed
        self.capacity = 0
        self.id_station_dest = 0
        self.station_dest_pos = [0,0]
        self.station_address = ""
        self.route = []
        self.cnt_route = 0
        self.returning = False
        self.model.stations_revised[self.index]= self.id_station_dest
        self.cnt_st = 0                     #Number of steps moving to the same station
        self.maxCapacityThreshold = 15
        self.minCapacityThreshold = 0
            
    
    def step(self):
        self.cnt_st += 1
        station_dest = self.model.space._index_to_agent[self.id_station_dest]
        #Comprobamos si puede volver a cocheras        
        if((self.returning == True) & (self.capacity == 0)):
            #Destroy the truck agent
            self.model.schedule.remove(self)
            self.model.space.remove_agent(self)
            del self.model.stations_revised[self.index]
            return

        if((self.moving == False) & (self.working == False)):
            station_dest = self.get_station()
            self.id_station_dest = station_dest.index
            self.station_dest_pos = station_dest.pos
            self.station_address = station_dest.address
            self.model.stations_revised[self.index]= self.id_station_dest
            self.route, duration,distance = self.get_route(self.pos,self.station_dest_pos)
            self.cnt_route = 0
            self.moving = True

        if(self.moving == True):
            self.move()
            if(((self.pos[0] == self.route[-1][0])&(self.pos[1] == self.route[-1][1]))):
                self.moving = False
                self.working = True

        
        if(self.working == True):
            #If the station is high the truck takes a bike
            if((station_dest.priority == 1) & (self.capacity <self.maxCapacityThreshold)):
                self.capacity +=1
                station_dest.dock_bikes -= 1
                station_dest.free_bases += 1
                if(self.capacity >= self.maxCapacityThreshold):
                    self.working = False     

                #Elif the station is Low the truck gives a bike
            elif((station_dest.priority == 2) & (self.capacity > self.minCapacityThreshold)):
                self.capacity -=1
                station_dest.dock_bikes += 1
                station_dest.free_bases -= 1
                if(self.capacity <= self.minCapacityThreshold):
                    self.working = False
            else:
                self.working = False    

    
    def get_station(self):
        if(self.returning == False):
            if(self.capacity <self.maxCapacityThreshold/5):
                station_dest = self.get_station_high(self.pos)
            #if  semi-full or more get nearest Low load station to unload the truck
            else:
                station_dest = self.get_station_low(self.pos)
                
        else:
            #Comportamiento cuando returning = True, dejar las bicis y volver a cocheras
            station_dest = self.get_station_low(self.pos)

        return station_dest
    
        
    def get_pos():
        return pos
    
    
    def move(self):
        global kmh_to_grdm
        self.model.space.move_agent(self,self.pos, self.speed/kmh_to_grdm)
        
    def get_station_high(self,pos):
        global grd_to_m
        punct_lower = math.inf
        latitude_ini = pos[0]
        longitude_ini = pos[1]
        
        stations = self.model.space.get_stations_agents()
        station_final = stations[0]
        #Recorremos el array de estaciones para ver la mas cercana
        for station in stations:
            for ind in self.model.stations_revised.values():
                if(station.index == ind):
                    continue
            if (station.priority == 1):
                latitude_dist = station.latitude - latitude_ini
                longitude_dist = station.longitude - longitude_ini   
                dist = abs(math.sqrt(math.pow(latitude_dist,2)+math.pow(longitude_dist,2)))*grd_to_m
                punct = dist + station.free_bases*200
                if(punct < punct_lower):
                    station_final = station

            

             
        return station_final
        
    def get_station_low(self,pos):
        global grd_to_m
        punct_lower = math.inf
        latitude_ini = pos[0]
        longitude_ini = pos[1]
        stations = self.model.space.get_stations_agents()
        station_final = stations[0]
        #Recorremos el array de estaciones para ver la mas cercana
        for station in stations:
            for ind in self.model.stations_revised:
                if(station.index == ind):
                    continue
            if (station.priority == 2):
                latitude_dist = station.latitude - latitude_ini
                longitude_dist = station.longitude - longitude_ini   
                dist = abs(math.sqrt(math.pow(latitude_dist,2)+math.pow(longitude_dist,2)))*grd_to_m
                punct = dist + station.free_bases*200
                if(punct < punct_lower):
                    station_final = station
            
        return station_final
    
        
    def get_route(self,ini_pos, fin_pos):
        url = "http://ors-madrid.gsi.upm.es/ors/routes"  
        querystring = {"profile":"driving-car", "coordinates": str(ini_pos[1])+","+ str(ini_pos[0]) +"|"+str(fin_pos[1])+","+ str(fin_pos[0]), "preference":"fastest", "geometry_format":"geojson"}
        headers = {'Content-Type': "application/json"}
        response = requests.request("GET", url, headers=headers, params=querystring)
        
        response_json = json.loads(response.text)
        distance = response_json['routes'][0]['summary']['distance']
        duration = response_json['routes'][0]['summary']['duration']
        coordenadas = []
        for coords in response_json['routes'][0]['geometry']['coordinates']:
            coordenadas.append([coords[1], coords[0]])
        return coordenadas, duration, distance