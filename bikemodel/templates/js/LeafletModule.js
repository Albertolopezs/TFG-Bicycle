;(function(undefined) {
  "use strict";

  /**
   * Leaflet Visualization
   */

  // Private constants
  var latitude_cnt = 40.426419, 
      longitude_cnt = -3.690926,
      zoom = 13.5,
      maxZoom= 18,
	  minZoom= 9;

  // Private variables
  var day,
  	  hour,
  	  minutes,
  	  model_type,
  	  stations,			// JSON data of the stations
      bikes,			// JSON data of the bikes
      trucks,           // JSON data of the trucks
      map;
  var station_layerGroup = new L.layerGroup(),
	  bike_layerGroup = new L.layerGroup(),
	  truck_layerGroup = new L.layerGroup();
  var bikeIcon = L.icon({
	  iconUrl: 'static/img/bike.svg',
	  iconSize: [20, 30], // size of the icon
	  }),
	  truckIcon = L.icon({
		  iconUrl: 'static/img/truck-icon.svg',
		  iconSize: [60, 40], // size of the icon
		  }),
	  stationIcon_green = L.icon({
		  iconUrl: 'static/img/bike-station-green.svg',
		  iconSize: [30, 50], // size of the icon
		  }),
	  stationIcon_red = L.icon({
		  iconUrl: 'static/img/bike-station-red.svg',
		  iconSize: [30, 50], // size of the icon
		  }),
	  stationIcon_blue = L.icon({
		  iconUrl: 'static/img/bike-station-blue.svg',
		  iconSize: [30, 50], // size of the icon
		  });


  	function reset_labels(){
  		var sidebar = document.getElementById('sidebar');
		sidebar.innerHTML += '<div id="map" style="height:500px;width:100%"></div><label class="label label-primary" for="fps" style="margin-right: 15px">Frames Per Second</label><input id="fps" data-slider-id="fps" type="text" />';
  	}


	function create_map() {
		
	    map = L.map('map').setView([latitude_cnt, longitude_cnt], zoom);
	    // load a tile layer
	    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
	       {
	        attribution: 'Map data (c) OpenStreetMap, Alberto Lopez Santiago - GSI',
	        maxZoom: maxZoom,
	        minZoom: minZoom
	        }).addTo(map);   

	}


	function update_data(json_data){ 
		var json = JSON.parse(json_data);
		console.log(json)
		day = json['Hour']['D']
		hour = json['Hour']['H'];
		minutes = json['Hour']['M'];
		stations = json['stations'];
		bikes = json['bike'];
		trucks = json['trucks'];
	}

	function set_station_markers(){
		stations.forEach(function(station) {
			var latitude = station.latitude,
			longitude = station.longitude,
			free_bases = station.free_bases,
			dock_bikes = station.dock_bikes,
			total_bases = station.total_bases,
			address = station.address,
			priority = parseInt(station.priority);
			var icon;
			if(priority == 1){
				icon = stationIcon_red
			}
			else if(priority ==2){
				icon = stationIcon_blue
			}
			else{
				icon = stationIcon_green
			}
			var list = "<h4>"+address+"</h4>"
			+"<dl><dt>Dock bikes</dt>"
           + "<dd>" + dock_bikes+ "</dd>"
           + "<dt>Free bases</dt>"
           + "<dd>" + free_bases + "</dd>"
           + "<dt>Total bases</dt>"
           + "<dd>" + total_bases + "</dd>"
           + "<dt>Priority</dt>"
           + "<dd>" + priority+ "</dd>"
        	var marker =  new L.Marker([latitude,longitude ],{icon: icon}).bindPopup(list).openPopup();
        	marker.addTo(station_layerGroup);
		});
		station_layerGroup.addTo(map);
		

	}



	function clear_station_markers(){
		station_layerGroup.clearLayers()
	}



	function set_bike_markers(){
		console.log(bikes);
		bikes.forEach(function(bike) {

			var latitude = bike.latitude,
			longitude = bike.longitude,
			id_dest = bike.id_dest,
			id_orig = bike.id_orig;
        	var marker =  new L.Marker([latitude,longitude ],{icon: bikeIcon});
        	marker.addTo(bike_layerGroup);
		});
		bike_layerGroup.addTo(map);
		

	}

	function clear_bike_markers(){
		bike_layerGroup.clearLayers()
	}


	function set_truck_markers(){
		var cnt = 0
		trucks.forEach(function(truck) {
			cnt +=1
			var latitude = truck.latitude,
			longitude = truck.longitude,
			capacity = truck.capacity,
			address = truck.address;
			var list = "<h4>Truck ID:"+cnt+"</h4>"
			+"<dl><dt>Capacity</dt>"
           + "<dd>" + capacity+ "</dd>"
           + "<dt>Destination station address</dt>"
           + "<dd>" + address + "</dd>"
        	var marker =  new L.Marker([latitude,longitude ],{icon: truckIcon}).bindPopup(list).openPopup();
        	marker.addTo(truck_layerGroup);
		});
		truck_layerGroup.addTo(map);
		

	}

	

	function clear_truck_markers(){
		truck_layerGroup.clearLayers()
	}

	function set_hour(){
		var hourDiv = document.getElementById("hour");
		hourDiv.innerHTML = "<b>Day:</b> "+ day+" \t <b>Hour:</b> "+ hour+ " <b>Minutes:</b>"+ minutes;
	}


	function clear_markers(){
		clear_station_markers();
		clear_bike_markers();
		clear_truck_markers();
	}
        /**
	}
	}
	}
	}
   * Exporting
   * ---------
   */
  this.LeafletVisualization = {

    // Functions
    create_map: create_map,
    update_data:update_data,
    set_station_markers: set_station_markers,
    clear_station_markers: clear_station_markers,
    set_bike_markers: set_bike_markers,
    clear_bike_markers: clear_bike_markers,
    set_truck_markers: set_truck_markers,
    clear_truck_markers: clear_truck_markers,
    set_hour:set_hour,
    reset_labels:reset_labels


    // Attributes
    /*
    model: {},
    nodes: undefined,
    links: undefined,

    // Getters
    color: color,
    shapes: shapes,
    colors: colors,
    get_attributes: get_attributes,
    get_nodes: get_nodes,

    // Statistics
    statistics: {},

    // Version
    version: '0.1'
    */
  };

}).call(this);
