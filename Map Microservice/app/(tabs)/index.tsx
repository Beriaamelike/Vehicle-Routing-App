import React, { useRef, useState } from "react";
import MapView, { Marker, Polyline } from "react-native-maps";
import { StyleSheet, Text, View, FlatList, Pressable } from "react-native";
import deliveryMarkers from "@/assets/markers"; // Marker listesi

const GOOGLE_MAPS_APIKEY = "AIzaSyChn1mkTUiT6PfrWt08G4Qrp_HEsDpz8oI"; // API keyinizi buraya yazın
const ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes";

interface MarkerType {
  id: string;
  customerName: string;
  coordinates: { latitude: number; longitude: number };
  address: string;
  product: string;
  quantity: number;
  estimatedArrival: string;
  status: string;
  deliveryNote: string;
}

const HomeScreen = () => {
  const mapRef = useRef<MapView | null>(null);
  const [selectedCard, setSelectedCard] = useState<string>("");
  const [polylineCoords, setPolylineCoords] = useState<{ latitude: number; longitude: number }[]>([]);

  // **Rota oluşturma fonksiyonu**
  const generateRoute = async () => {
    if (deliveryMarkers.length === 0) {
      console.error("Teslimat noktaları eksik.");
      return;
    }

    const origin = deliveryMarkers[0].coordinates;
    const destination = deliveryMarkers[deliveryMarkers.length - 1].coordinates;

    const waypoints = deliveryMarkers.slice(1, -1).map(marker => ({
      location: { latLng: { latitude: marker.coordinates.latitude, longitude: marker.coordinates.longitude } }
    }));

    const requestBody: any = {
      origin: { location: { latLng: { latitude: origin.latitude, longitude: origin.longitude } } },
      destination: { location: { latLng: { latitude: destination.latitude, longitude: destination.longitude } } },
      travelMode: "DRIVE",
      routingPreference: "TRAFFIC_AWARE",
      polylineEncoding: "ENCODED_POLYLINE"
    };

    if (waypoints.length > 0) {
      requestBody.intermediates = waypoints;
    }

    try {
      const response = await fetch(ROUTES_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Goog-Api-Key": GOOGLE_MAPS_APIKEY,
          "X-Goog-FieldMask": "routes.polyline"
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();
      console.log("Routes API Response:", data);

      if (data.routes && data.routes.length > 0) {
        const encodedPolyline = data.routes[0].polyline.encodedPolyline;
        const decodedPolyline = decodePolyline(encodedPolyline);
        setPolylineCoords(decodedPolyline);
      } else {
        console.error("No routes found. Response:", data);
      }
    } catch (error) {
      console.error("Error fetching route:", error);
    }
  };

  const handleMarkerPress = (marker: MarkerType) => {
    setSelectedCard(marker.id);
    mapRef.current?.animateToRegion(
      {
        latitude: marker.coordinates.latitude,
        longitude: marker.coordinates.longitude,
        latitudeDelta: 0.02,
        longitudeDelta: 0.02,
      },
      1000
    );
  };

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        ref={mapRef}
        initialRegion={{
          latitude: deliveryMarkers[0]?.coordinates.latitude || 37.7749,
          longitude: deliveryMarkers[0]?.coordinates.longitude || -122.4194,
          latitudeDelta: 0.05,
          longitudeDelta: 0.05,
        }}
      >
        {deliveryMarkers.map((marker) => (
          <Marker key={marker.id} title={marker.customerName} coordinate={marker.coordinates} />
        ))}

        {polylineCoords.length > 0 && (
          <Polyline coordinates={polylineCoords} strokeWidth={4} strokeColor="#4285F4" />
        )}
      </MapView>

      <View style={styles.markerListContainer}>
        <FlatList
          horizontal
          data={deliveryMarkers}
          keyExtractor={(item) => item.id}
          renderItem={({ item: marker }) => (
            <Pressable
              onPress={() => handleMarkerPress(marker)}
              style={marker.id === selectedCard ? styles.activeMarkerButton : styles.markerButton}
            >
              <View style={styles.markerInfo}>
                <Text style={styles.markerName}>{marker.customerName}</Text>
                <Text style={styles.markerDescription}>{marker.address}</Text>
                <Text style={styles.markerStatus}>Durum: {marker.status}</Text>
                <Text style={styles.markerNote}>{marker.deliveryNote}</Text>
              </View>
            </Pressable>
          )}
          showsHorizontalScrollIndicator={false}
        />
      </View>

      <Pressable style={styles.routeButton} onPress={generateRoute}>
        <Text style={styles.routeButtonText}>Rota Oluştur</Text>
      </Pressable>
    </View>
  );
};

const decodePolyline = (encoded: string) => {
  let index = 0, lat = 0, lng = 0, coordinates = [];
  while (index < encoded.length) {
    let shift = 0, result = 0, byte;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lat += result & 1 ? ~(result >> 1) : result >> 1;
    shift = result = 0;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lng += result & 1 ? ~(result >> 1) : result >> 1;
    coordinates.push({ latitude: lat / 1e5, longitude: lng / 1e5 });
  }
  return coordinates;
};




// **Stiller**
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f0f0f0" },
  map: { flex: 1 },
  markerListContainer: { position: "absolute", bottom: 80, left: 0, right: 0, paddingHorizontal: 10 },
  activeMarkerButton: { backgroundColor: "#E7E3AC", borderRadius: 10, padding: 10, marginHorizontal: 5, elevation: 3, width: 300 },
  markerButton: { backgroundColor: "#fff", borderRadius: 10, padding: 10, marginHorizontal: 5, elevation: 3, width: 300 },
  markerInfo: { flex: 1 },
  markerName: { fontSize: 16, fontWeight: "bold", color: "#333" },
  markerDescription: { fontSize: 12, color: "#666", marginTop: 3 },
  markerProduct: { fontSize: 14, fontWeight: "600", color: "#222", marginTop: 3 },
  markerStatus: { fontSize: 12, color: "#008000", marginTop: 3 },
  markerNote: { fontSize: 12, color: "#666", marginTop: 3 },
  routeButton: { position: "absolute", bottom: 20, left: "50%", marginLeft: -75, backgroundColor: "#4285F4", padding: 10, borderRadius: 10, elevation: 3 },
  routeButtonText: { color: "#fff", fontSize: 16, fontWeight: "bold" },
});

export default HomeScreen;  