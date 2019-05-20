import itertools
import math
import numpy as np
from bikemodel.TruckAgent import TruckAgent
from bikemodel.StationAgent import StationAgent
from bikemodel.BikeAgent import BikeAgent
class BikeSpace:
    """ Continuous space where each agent can have an arbitrary position.

    Assumes that all agents are point objects, and have a pos property storing
    their position as an (x, y) tuple. This class uses a numpy array internally
    to store agent objects, to speed up neighborhood lookups.

    """
    _grid = None

    def __init__(self, lat_max = 180.0, lon_max = 180.0, torus = False, lat_min=-180.0, lon_min=-180.0):
        """ Create a new continuous space.

        Args:
            lat_max, lon_max: maximum latitude and longitude, default 180.
            torus: Boolean for whether the edges loop around.
            lat_min, lon_min: (default -180) If provided, set the minimum lat and lon for the space

        """
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.lat_width = lat_max - lat_min
        self.lon_min = lon_min
        self.lon_max = lon_max
        self.lon_height = lon_max - lon_min
        self.center = np.array(((lat_max + lat_min) / 2, (lon_max + lon_min) / 2))
        self.size = np.array((self.lat_width, self.lon_height))
        self.torus = torus

        self._agent_points = None
        self._index_to_agent = {}
        self._agent_to_index = {}

    def place_agent(self, agent, pos):
        """ Place a new agent in the space.

        Args:
            agent: Agent object to place.
            pos: Coordinate tuple for where to place the agent.

        """

        if self._agent_points is None:
            self._agent_points = np.array([pos])
        else:
            self._agent_points = np.append(self._agent_points, np.array([pos]), axis=0)
        self._index_to_agent[self._agent_points.shape[0] - 1] = agent
        self._agent_to_index[agent] = self._agent_points.shape[0] - 1
        agent.pos = pos

    def move_agent(self, agent,agent_pos,distance):
        """ Move an agent from its current position to a new position.

        Args:
            agent: The agent object to move.
            distance: grados.

        """
        #18km/h -> 5 m/s
        #60km/h -> 16,66 m/s
        #1 grade = 111,32km
        #20 seconds -> 100 meters = 0.0009º
        #1 minute -> 300 meters = 0.0027º ---- BIKE
        #1 minute -> 1000 meters = 0.009º ---- TRUCK


        latlng_distance = distance
        cnt_route = agent.cnt_route
        route = agent.route

        #Latitude and longitude difs
        hip = self.get_distance(route[cnt_route], agent_pos)
        posf = []
        #Si la distancia a recorrer es menor a la distancia por step se coloca al agente en el final de la route
        if (hip < latlng_distance):
            posf.append(route[cnt_route][0])
            posf.append(route[cnt_route][1])
            if(agent.cnt_route < len(agent.route)-1):
                latlng_distance -= hip
                agent.cnt_route = agent.cnt_route + 1
                self.move_agent(agent,posf,latlng_distance)

        else:
        #Si no se mueve la distancia en dirección al punto de la route
            dlat = route[cnt_route][0]-agent_pos[0]
            dlon = route[cnt_route][1]-agent_pos[1]
            posf.append(float(agent.pos[0]) + float("{0:.6f}".format(latlng_distance*math.sin(math.atan2(dlat,dlon)))))
            posf.append(float(agent.pos[1]) + float("{0:.6f}".format(latlng_distance*math.cos(math.atan2(dlat,dlon)))))
        
        idagent = self._agent_to_index[agent]
        self._agent_points[idagent, 0] = posf[0]
        self._agent_points[idagent, 1] = posf[1]
        agent.pos = posf

    def remove_agent(self, agent):
        """ Remove an agent from the simulation.

        Args:
            agent: The agent object to remove
            """
        if agent not in self._agent_to_index:
            raise Exception("Agent does not exist in the space")
        idagent = self._agent_to_index[agent]
        del self._agent_to_index[agent]
        max_idagent = max(self._index_to_agent.keys())
        # Delete the agent's position and decrement the index/agent mapping
        self._agent_points = np.delete(self._agent_points, idagent, axis=0)
        for a, index in self._agent_to_index.items():
            if index > idagent:
                self._agent_to_index[a] = index - 1
                self._index_to_agent[index - 1] = a
        # The largest index is now redundant
        del self._index_to_agent[max_idagent]
        agent.pos = None

    def get_neighbors(self, pos, radius, include_center=True):
        """ Get all objects within a certain radius.

        Args:
            pos: (x,y) coordinate tuple to center the search at.
            radius: Get all the objects within this distance of the center.
            include_center: If True, include an object at the *exact* provided
                            coordinates. i.e. if you are searching for the
                            neighbors of a given agent, True will include that
                            agent in the results.

        """
        deltas = np.abs(self._agent_points - np.array(pos))
        if self.torus:
            deltas = np.minimum(deltas, self.size - deltas)
        dists = deltas[:, 0] ** 2 + deltas[:, 1] ** 2

        idagents, = np.where(dists <= radius ** 2)
        neighbors = [self._index_to_agent[x] for x in idagents if include_center or dists[x] > 0]
        return neighbors

    def get_heading(self, pos_1, pos_2):
        """ Get the heading angle between two points, accounting for toroidal space.

        Args:
            pos_1, pos_2: Coordinate tuples for both points.
        """
        one = np.array(pos_1)
        two = np.array(pos_2)
        if self.torus:
            one = (one - self.center) % self.size
            two = (two - self.center) % self.size
        heading = two - one
        if isinstance(pos_1, tuple):
            heading = tuple(heading)
        return heading

    def get_distance(self, pos_1, pos_2):
        """ Get the distance between two point, accounting for toroidal space.

        Args:
            pos_1, pos_2: Coordinate tuples for both points.

        """
        lat1, lon1 = pos_1
        lat2, lon2 = pos_2

        dlat = np.abs(lat1 - lat2)
        dlon = np.abs(lon1 - lon2)
        if self.torus:
            dlat = min(dlat, self.lat_width - dlat)
            dlon = min(dlon, self.lon_height - dlon)
        return np.sqrt(dlat * dlat + dlon * dlon)

    def get_stations_agents(self):
        """ Get the agents of type 1

        """
        station_agents = []
        for agent in self._agent_to_index:
            if(isinstance(agent,StationAgent)):
                station_agents.append(agent)

        return station_agents

    def get_truck_agents(self):
        """ Get the agents of type 2

        """
        truck_agents = []
        for agent in self._agent_to_index:
            if(isinstance(agent,TruckAgent)):
                truck_agents.append(agent)

        return truck_agents

    def get_bike_agents(self):
        """ Get the agents of type 3

        """
        bike_agents = []
        for agent in self._agent_to_index:
            if(isinstance(agent,BikeAgent)):
                bike_agents.append(agent)

        return bike_agents

    def torus_adj(self, pos):
        """Adjust coordinates to handle torus looping.
                        
                                If the coordinate is out-of-bounds and the space is toroidal, return
                                the corresponding point within the space. If the space is not toroidal,
                                raise an exception.
                        
                                Args:
                                    pos: Coordinate tuple to convert."""

      


        if not self.out_of_bounds(pos):
            return pos
        elif not self.torus:
            raise Exception("Point out of bounds, and space non-toroidal.")
        else:
            x = self.lat_min + ((pos[0] - self.lat_min) % self.lat_width)
            y = self.lon_min + ((pos[1] - self.lon_min) % self.lon_height)
            if isinstance(pos, tuple):
                return (x, y)
            else:
                return np.array((x, y))

    def out_of_bounds(self, pos):
        """ Check if a point is out of bounds. """
        x_a, y_a = pos
        x = float(x_a)
        y = float(y_a)
        return (x < self.lat_min or x >= self.lat_max or
                y < self.lon_min or y >= self.lon_max)

    def get_agents_list(self, model):
        """ Return a list of agents and their positions"""

        return self._agent_points
