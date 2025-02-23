from fastapi import FastAPI, HTTPException
import requests
import folium
import openrouteservice
from fastapi.responses import HTMLResponse

app = FastAPI()
TOMTOM_API_KEY = "eZEcIlVKK9lGUqDzqLtnm8b7xOG1FfFG"
ORS_API_KEY = "5b3ce3597851110001cf624882ff503deb274a2981515b5272c8cb05"
ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
TOMTOM_TRAFFIC_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
TOMTOM_INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"

def fetch_route(origin: str, destination: str):
    """Fetch route data from ORS API."""
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    try:
        origin_lon, origin_lat = map(float, origin.split(","))
        destination_lon, destination_lat = map(float, destination.split(","))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid coordinate format. Use 'longitude,latitude'.")
    location_data = {
        "coordinates": [[origin_lon, origin_lat], [destination_lon, destination_lat]],
        "geometry": "geojson"
    }
    response = requests.post(ORS_URL, json=location_data, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"ORS API Error: {response.text}")
    data = response.json()
    if "routes" not in data or not data["routes"]:
        raise HTTPException(status_code=404, detail="No route found. Check if the locations are reachable.")
    print("success fteching route")
    return data

def get_traffic(lat: float, lon: float):
    """Fetch real-time traffic flow data from TomTom."""
    params = {"key": TOMTOM_API_KEY, "point": f"{lat},{lon}"}
    response = requests.get(TOMTOM_TRAFFIC_URL, params=params)
    if response.status_code != 200:
        return None  # Return None if traffic data is unavailable
    print("Sucess fetching traffic")
    return response.json()

def get_incidents(min_lat: float, min_lon: float, max_lat: float, max_lon: float):
    """Fetch real-time traffic incidents from TomTom with debugging."""
    params = {
        "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "key": TOMTOM_API_KEY
    }
    response = requests.get(TOMTOM_INCIDENTS_URL, params=params)
    print("Traffic API Response Status Code:", response.status_code)
    if response.status_code != 200:
        print("Traffic API Error Response:", response.text)
        return None  # Return None if incidents data is unavailable
    incidents_data = response.json()
    print("Success fetching incidents:", incidents_data)
    return incidents_data

@app.get("/map", response_class=HTMLResponse)
def show_map(origin: str, destination: str):
    origin_lon, origin_lat = map(float, origin.split(","))
    destination_lon, destination_lat = map(float, destination.split(","))
    data = fetch_route(origin, destination)
    if "routes" not in data:
        return HTMLResponse("<h1>Error: Route not found</h1>")
    
    client = openrouteservice.Client(key=ORS_API_KEY)
    route_coords = openrouteservice.convert.decode_polyline(data['routes'][0]['geometry'])
    route_coords = [(coord[1], coord[0]) for coord in route_coords['coordinates']]
    
    m = folium.Map(location=route_coords[0], zoom_start=13)
    
    segment_length = max(1, len(route_coords) // 30)
    for i in range(0, len(route_coords) - 1, segment_length):
        mid_index = i + segment_length // 2
        if mid_index >= len(route_coords):
            mid_index = len(route_coords) - 1
        mid_lat, mid_lon = route_coords[mid_index]
        traffic_data = get_traffic(mid_lat, mid_lon)
        color = "blue"
        if "flowSegmentData" in traffic_data:
            speed = traffic_data["flowSegmentData"].get("currentSpeed", 0)
            free_flow_speed = traffic_data["flowSegmentData"].get("freeFlowSpeed", 1)
            congestion_level = speed / free_flow_speed
            if congestion_level > 0.8:
                color = "green"
            elif congestion_level > 0.5:
                color = "yellow"
            else:
                color = "red"
        folium.PolyLine(route_coords[i:i + segment_length + 1], color=color, weight=5, opacity=0.7).add_to(m)
    
    folium.Marker(route_coords[0], tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(route_coords[-1], tooltip="End", icon=folium.Icon(color="red")).add_to(m)

    min_lat, min_lon = min(origin_lat, destination_lat), min(origin_lon, destination_lon)
    max_lat, max_lon = max(origin_lat, destination_lat), max(origin_lon, destination_lon)
    incidents_data = get_incidents(min_lat, min_lon, max_lat, max_lon)
    
    print("Traffic API Response:", incidents_data)
    if incidents_data and "incidents" in incidents_data:
        for incident in incidents_data["incidents"]:
            lat, lon = incident["geometry"]["coordinates"][1], incident["geometry"]["coordinates"][0]
            description = incident.get("properties", {}).get("description", "No details")
            folium.Marker(
                [lat, lon], 
                tooltip=f"🚨 Incident: {description}", 
                icon=folium.Icon(color="orange", icon="exclamation-triangle", prefix="fa")
            ).add_to(m)
    return m._repr_html_()

