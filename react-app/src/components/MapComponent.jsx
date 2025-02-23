import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Polyline, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import axios from "axios";

const ORS_API_KEY = "5b3ce3597851110001cf624882ff503deb274a2981515b5272c8cb05";
const ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson";
const TOMTOM_API_KEY = "eZEcIlVKK9lGUqDzqLtnm8b7xOG1FfFG";
const TOMTOM_TRAFFIC_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json";

function MapUpdater({ center }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, 14);
  }, [center, map]);
  return null;
}

function App() {
  const [source, setSource] = useState([17.575139, 78.422813]); // Default values
  const [destination, setDestination] = useState([17.498044, 78.361187]);
  const [route, setRoute] = useState([]);
  const [trafficColor, setTrafficColor] = useState("blue");

  // Fetch Route Data from ORS
  const fetchRoute = async () => {
    try {
      const response = await axios.post(
        ORS_URL,
        {
          coordinates: [[source[1], source[0]], [destination[1], destination[0]]],
        },
        {
          headers: { Authorization: `Bearer ${ORS_API_KEY}` },
        }
      );

      if (response.data && response.data.features.length > 0) {
        const routeCoords = response.data.features[0].geometry.coordinates.map(coord => [coord[1], coord[0]]);
        setRoute(routeCoords);
      } else {
        console.error("No route data found.");
      }
    } catch (error) {
      console.error("Error fetching route:", error);
    }
  };

  // Fetch Traffic Data from TomTom
  const fetchTraffic = async () => {
    try {
      const response = await axios.get(
        `${TOMTOM_TRAFFIC_URL}?point=${source[0]},${source[1]}&unit=KMPH&key=${TOMTOM_API_KEY}`
      );

      if (response.data.flowSegmentData) {
        const trafficData = response.data.flowSegmentData;
        const speedRatio = trafficData.currentSpeed / trafficData.freeFlowSpeed;

        if (speedRatio > 0.8) setTrafficColor("blue"); // No traffic
        else if (speedRatio > 0.5) setTrafficColor("yellow"); // Normal traffic
        else setTrafficColor("red"); // High traffic
      }
    } catch (error) {
      console.error("Error fetching traffic data:", error);
    }
  };

  const handleNavigate = () => {
    fetchRoute();
    fetchTraffic();
  };

  return (
    <div>
      <h1>Live Navigation with Real-Time Traffic</h1>
      <div>
        <label>Source: </label>
        <input
          type="text"
          placeholder="Lat,Lng"
          onBlur={(e) => setSource(e.target.value.split(",").map(Number))}
        />
        <label> Destination: </label>
        <input
          type="text"
          placeholder="Lat,Lng"
          onBlur={(e) => setDestination(e.target.value.split(",").map(Number))}
        />
        <button onClick={handleNavigate}>Start Navigation</button>
      </div>

      <MapContainer center={source} zoom={14} style={{ height: "500px", width: "100%" }}>
        <MapUpdater center={source} />
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />
        <Marker position={source} />
        <Marker position={destination} />
        {route.length > 0 && <Polyline positions={route} color={trafficColor} />}
      </MapContainer>
    </div>
  );
}

export default App;
