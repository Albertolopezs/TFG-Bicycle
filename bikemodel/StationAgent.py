from mesa import Agent
import numpy as np
import requests
import math
import pandas as pd
import json

class StationAgent(Agent):
    def __init__(self,model, index,index_st,address, latitude, longitude, free_bases, total_bases, dock_bikes):
    
        super().__init__(index, model)
        self.index = index
        self.index_st = index_st
        self.address = address
        self.avaliable = True
        self.latitude = latitude
        self.longitude = longitude
        self.free_bases = free_bases
        self.total_bases = total_bases
        self.dock_bikes = dock_bikes
        self.pos = [latitude,longitude]
        """
            Priority Normal - 0
            Priority High - 1
            Priority Low - 2
        """
        
        if(self.dock_bikes <0.3*self.total_bases):
            self.priority = 2
        elif(self.free_bases <0.3*self.total_bases):
            self.priority = 1
        else:
            self.priority = 0
            
    
    def step(self):
        if(self.dock_bikes <0.3*self.total_bases):
            self.priority = 2
        elif(self.free_bases <0.3*self.total_bases):
            self.priority = 1
        else:
            self.priority = 0
        
       
    def get_pos():
        return self.latitude,self.longitude