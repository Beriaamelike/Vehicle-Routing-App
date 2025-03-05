import React, { useRef, useState } from "react";
import MapView, { Marker, Polyline } from "react-native-maps";
import { StyleSheet, Text, View, FlatList, Pressable, Image } from "react-native";
import markers from "@/assets/markers"; // Marker listesi (latitude, longitude içermeli)

const GOOGLE_MAPS_APIKEY = "AIzaSyChn1mkTUiT6PfrWt08G4Qrp_HEsDpz8oI"; // API keyinizi buraya yazın
const ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes";

interface MarkerType {
  name: string;
  coordinates: { latitude: number; longitude: number };
  description: string;
  image: string;
}

const HomeScreen = () => {
  const mapRef = useRef<MapView | null>(null);
  const [selectedCard, setSelectedCard] = useState<string>("");
  const [polylineCoords, setPolylineCoords] = useState<{ latitude: number; longitude: number }[]>([]);

  // **Rota oluşturma fonksiyonu**
  const generateRoute = async () => {
    if (markers.length < 2) {
      console.error("At least two markers are required to calculate a route.");
      return;
    }

    const origin = markers[0].coordinates;
    const destination = markers[markers.length - 1].coordinates;

    // Ara noktalar (ilk ve son hariç)
    const waypoints = markers.slice(1, -1).map(marker => ({
      location: { latLng: { latitude: marker.coordinates.latitude, longitude: marker.coordinates.longitude } }
    }));

    // API'ye gönderilecek istek gövdesi
    const requestBody: any = {
      origin: { location: { latLng: { latitude: origin.latitude, longitude: origin.longitude } } },
      destination: { location: { latLng: { latitude: destination.latitude, longitude: destination.longitude } } },
      travelMode: "DRIVE",
      routingPreference: "TRAFFIC_AWARE",
      polylineEncoding: "ENCODED_POLYLINE"
    };

    if (waypoints.length > 0) {
      requestBody.intermediates = waypoints; // Ara noktaları ekle
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

  // **Haritadaki bir marker'a tıklanınca çalışır**
  const handleMarkerPress = (marker: MarkerType) => {
    setSelectedCard(marker.name);
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
          latitude: markers[0].coordinates.latitude,
          longitude: markers[0].coordinates.longitude,
          latitudeDelta: 0.05,
          longitudeDelta: 0.05,
        }}
      >
        {markers.map((marker, index) => (
          <Marker key={index} title={marker.name} coordinate={marker.coordinates} />
        ))}

        {polylineCoords.length > 0 && (
          <Polyline coordinates={polylineCoords} strokeWidth={4} strokeColor="#4285F4" />
        )}
      </MapView>

      {/* Marker Listesi */}
      <View style={styles.markerListContainer}>
        <FlatList
          horizontal
          data={markers}
          keyExtractor={(item) => item.name}
          renderItem={({ item: marker }) => (
            <Pressable
              onPress={() => handleMarkerPress(marker)}
              style={marker.name === selectedCard ? styles.activeMarkerButton : styles.markerButton}
            >
              <Image source={{ uri: marker.image }} style={styles.markerImage} />
              <View style={styles.markerInfo}>
                <Text style={styles.markerName}>{marker.name}</Text>
                <Text style={styles.markerDescription}>{marker.description}</Text>
              </View>
            </Pressable>
          )}
          showsHorizontalScrollIndicator={false}
        />
      </View>

      {/* Rota oluşturma butonu */}
      <Pressable style={styles.routeButton} onPress={generateRoute}>
        <Text style={styles.routeButtonText}>Generate Route</Text>
      </Pressable>
    </View>
  );
};

// **Polyline çözme fonksiyonu**
const decodePolyline = (encoded: string) => {
  let index = 0,
    lat = 0,
    lng = 0,
    coordinates = [];
  while (index < encoded.length) {
    let shift = 0,
      result = 0,
      byte;
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
  markerListContainer: {
    position: "absolute",
    bottom: 80,
    left: 0,
    right: 0,
    paddingHorizontal: 10,
  },
  activeMarkerButton: { backgroundColor: "#E7E3AC", borderRadius: 10, padding: 10, marginHorizontal: 5, flexDirection: "row", alignItems: "center", elevation: 3, width: 250 },
  markerButton: { backgroundColor: "#fff", borderRadius: 10, padding: 10, marginHorizontal: 5, flexDirection: "row", alignItems: "center", elevation: 3, width: 250 },
  markerImage: { width: 55, height: 55, borderRadius: 10, marginRight: 10 },
  markerInfo: { flex: 1 },
  markerName: { fontSize: 16, fontWeight: "bold", color: "#333" },
  markerDescription: { fontSize: 12, color: "#666", marginTop: 5 },
  routeButton: { position: "absolute", bottom: 20, left: "50%", marginLeft: -75, backgroundColor: "#4285F4", padding: 10, borderRadius: 10, elevation: 3 },
  routeButtonText: { color: "#fff", fontSize: 16, fontWeight: "bold" },
});

export default HomeScreen;
