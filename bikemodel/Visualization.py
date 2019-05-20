import os
import tornado.autoreload
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.escape
import tornado.gen
import webbrowser

import json
from .UserParam import UserSettableParameter

# Suppress several pylint warnings for this file.
# Attributes being defined outside of init is a Tornado feature.
# pylint: disable=attribute-defined-outside-init


class VisualizationElement:
    """
    Defines an element of the visualization.

    Attributes:
        package_includes: A list of external JavaScript files to include that
                          are part of the Mesa packages.
        local_includes: A list of JavaScript files that are local to the
                        directory that the server is being run in.
        js_code: A JavaScript code string to instantiate the element.

    Methods:
        render: Takes a model object, and produces JSON data which can be sent
                to the client.

    """

    package_includes = []
    local_includes = []
    js_code = ''
    render_args = {}

    def __init__(self):
        pass

    def render(self, model):
        """ Build visualization data from a model object.

        Args:
            model: A model object

        Returns:
            A JSON-ready object.

        """
        return "<b>VisualizationElement goes here</b>."

# =============================================================================
# Actual Tornado code starts here:


class PageHandler(tornado.web.RequestHandler):
    """ Handler for the HTML template which holds the visualization. """

    def get(self):
        elements = self.application.visualization_elements
        for i, element in enumerate(elements):
            element.index = i
        self.render("modular_template.html", port=self.application.port,
                    model_name=self.application.model_name,
                    description=self.application.description,
                    package_includes=self.application.package_includes,
                    local_includes=self.application.local_includes,
                    scripts=self.application.js_code)


class SocketHandler(tornado.websocket.WebSocketHandler):
    """ Handler for websocket. """
    def open(self):
        if self.application.verbose:
            print("Socket opened!")

    def check_origin(self, origin):
        return True

    @property
    def viz_state_message(self):
        return {
            "type": "viz_state",
            "data": self.application.render_model()
        }

    def on_message(self, message):
        """ Receiving a message from the websocket, parse, and act accordingly.

        """

        if self.application.verbose:
            print(message)
        msg = tornado.escape.json_decode(message)

        if msg["type"] == "get_step":
            if not self.application.model.running:
                self.write_message({"type": "end"})
            else:
                self.application.model.step()
                #Send station and Agent data
                data_json = self.get_situation_json()
                self.write_message({'type': 'get_situation',
                'data': data_json} ) 
                self.write_message(self.viz_state_message)

        elif msg["type"] == "reset":
            self.application.reset_model()


        elif msg["type"] == "submit_params":
            param = msg["param"]
            value = msg["value"]

            # Is the param editable?
            if param in self.application.user_params:
                if isinstance(self.application.model_kwargs[param], UserSettableParameter):
                    self.application.model_kwargs[param].value = value
                else:
                    self.application.model_kwargs[param] = value

        elif msg["type"] == "get_params":
            self.write_message({
                "type": "model_params",
                "params": self.application.user_params
            })

        else:
            if self.application.verbose:
                print("Unexpected message!")


    def get_situation_json(self):
        data_json = {}
        data_json['stations'] = []
        data_json['bike'] = []
        data_json['trucks'] = []
        data_json['Hour'] = {}
        data_json['Hour']['D'] = self.application.model.day
        data_json['Hour']['H'] = self.application.model.hour
        data_json['Hour']['M'] = self.application.model.minutes

        stations = self.application.model.space.get_stations_agents()
        bike = self.application.model.space.get_bike_agents()
        trucks = self.application.model.space.get_truck_agents()
        for i in range(len(stations)):
            
            data = {}
            data['address'] = stations[i].address
            data['priority'] = stations[i].priority
            data['latitude'] =stations[i].latitude
            data['longitude'] =stations[i].longitude
            data['free_bases'] =stations[i].free_bases
            data['total_bases'] =stations[i].total_bases
            data['dock_bikes'] =stations[i].dock_bikes
            data_json['stations'].append(data)

        for i in range(len(bike)):
            data = {}
            data['latitude'] =bike[i].pos[0]
            data['longitude'] =bike[i].pos[1]
            data['id_dest'] =bike[i].id_dest
            data['id_orig'] = bike[i].id_orig
            data_json['bike'].append(data)

        for i in range(len(trucks)):
            data = {}
            data['address'] = trucks[i].station_address
            data['latitude'] =trucks[i].pos[0]
            data['longitude'] =trucks[i].pos[1]
            data['capacity'] =trucks[i].capacity
            data['id_station_dest'] =trucks[i].id_station_dest
            data_json['trucks'].append(data)

        return json.dumps(data_json)




class ModularServer(tornado.web.Application):
    """ Main visualization application. """
    verbose = True

    port = 8521  # Default port to listen on
    max_steps = 100000

    # Handlers and other globals:
    page_handler = (r'/', PageHandler)
    socket_handler = (r'/ws', SocketHandler)
    static_handler = (r'/static/(.*)', tornado.web.StaticFileHandler,
                      {"path": os.path.dirname(__file__) + "/templates"})
    local_handler = (r'/local/(.*)', tornado.web.StaticFileHandler,
                     {"path": ''})

    handlers = [page_handler, socket_handler, static_handler, local_handler]

    settings = {"debug": True,
                "autoreload": False,
                "template_path": os.path.dirname(__file__) + "/templates"}


    def __init__(self, model_cls, name="Mesa Model",visualization_elements=[],description= "",
                 model_params={}):
        """ Create a new visualization server with the given elements. """
        # Prep visualization elements:
        self.visualization_elements = visualization_elements
        self.package_includes = set()
        self.local_includes = set()
        self.js_code = []
        for element in self.visualization_elements:
            for include_file in element.package_includes:
                self.package_includes.add(include_file)
            for include_file in element.local_includes:
                self.local_includes.add(include_file)
            self.js_code.append(element.js_code)

        # Initializing the model
        self.model_name = name
        self.model_cls = model_cls
        self.description = description

        self.model_kwargs = model_params
        self.reset_model()

        # Initializing the application itself:
        super().__init__(self.handlers, **self.settings)

    @property
    def user_params(self):
        result = {}
        for param, val in self.model_kwargs.items():
            if isinstance(val, UserSettableParameter):
                result[param] = val.json

        return result

    def reset_model(self):
        """ Reinstantiate the model object, using the current parameters. """

        model_params = {}
        for key, val in self.model_kwargs.items():
            if isinstance(val, UserSettableParameter):
                if val.param_type == 'static_text':    # static_text is never used for setting params
                    continue
                model_params[key] = val.value
            else:
                model_params[key] = val

        self.model = self.model_cls(**model_params)

    def render_model(self):
        """ Turn the current state of the model into a dictionary of
        visualizations

        """
        visualization_state = []
        for element in self.visualization_elements:
            element_state = element.render(self.model)
            visualization_state.append(element_state)
        return visualization_state

    def launch(self, port=None):
        """ Run the app. """
        startLoop = not tornado.ioloop.IOLoop.initialized()
        if port is not None:
            self.port = port
        url = 'http://127.0.0.1:{PORT}'.format(PORT=self.port)
        print('Interface starting at {url}'.format(url=url))
        self.listen(self.port)
        webbrowser.open(url)
        tornado.autoreload.start()
        if startLoop:
            tornado.ioloop.IOLoop.instance().start()
