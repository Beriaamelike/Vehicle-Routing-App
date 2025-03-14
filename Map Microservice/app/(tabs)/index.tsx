import React, { useEffect, useRef, useState } from "react";
import { Alert, StyleSheet, Text, View, FlatList, Pressable, ActivityIndicator } from "react-native";
import MapView, { Marker, Polyline } from "react-native-maps";

const API_BASE_URL = "http://10.0.2.2:8000/nodes"; // FastAPI URL'si (Android Emulator için)
const GOOGLE_MAPS_APIKEY = ""; // 🔥 API KEYİNİ BURAYA EKLE!
const ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes";

interface MarkerType {
  id: number;
  customer: number;
  coordinates: { latitude: number; longitude: number };
}

const HomeScreen = () => {
  const mapRef = useRef<MapView | null>(null);
  const [markers, setMarkers] = useState<MarkerType[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMarker, setSelectedMarker] = useState<number | null>(null);
  const [polylineCoords, setPolylineCoords] = useState<{ latitude: number; longitude: number }[]>([]);

  // **📌 API'den Markers Verisini Çek**
  const fetchMarkers = async () => {
    try {
      const response = await fetch(API_BASE_URL);
      const data = await response.json();
  
      if (data.nodes && data.nodes.length > 0) {
        const formattedMarkers = data.nodes.map((node: any) => ({
          id: node.id,
          customer: node.customer,
          coordinates: { latitude: node.xc, longitude: node.yc }
        }));

        console.log("📍 API'den Gelen Marker Verisi:", formattedMarkers);
        setMarkers(formattedMarkers);
      } else {
        Alert.alert("API Hatası", "Markers verisi boş geldi.");
        console.error("Markers verisi boş geldi:", data);
      }
    } catch (error) {
      Alert.alert("Bağlantı Hatası", "API'ye bağlanırken hata oluştu.");
      console.error("Error fetching markers:", error);
    } finally {
      setLoading(false);
    }
  };

  // **📌 İlk Açılışta API'den Markerları Çek**
  useEffect(() => {
    fetchMarkers();
  }, []);

  // **📌 Rota oluşturma fonksiyonu**
  const generateRoute = async () => {
    if (markers.length === 0) {
      console.error("Teslimat noktaları eksik.");
      return;
    }

    const origin = markers[0].coordinates;
    const destination = markers[markers.length - 1].coordinates;

    const waypoints = markers.slice(1, -1).map(marker => ({
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

  return (
    <View style={styles.container}>
      {loading ? (
        <ActivityIndicator size="large" color="#4285F4" style={styles.loading} />
      ) : (
        <>
          <MapView
            style={styles.map}
            ref={mapRef}
            initialRegion={{
              latitude: markers[0]?.coordinates.latitude || 39.9208, // Ankara'daki default konum
              longitude: markers[0]?.coordinates.longitude || 32.8541,
              latitudeDelta: 0.05,
              longitudeDelta: 0.05,
            }}
          >
            {markers.map((marker) => (
              <Marker 
                key={marker.id} 
                title={`Müşteri ${marker.customer}`} 
                coordinate={marker.coordinates} 
                pinColor="red"
                onPress={() => setSelectedMarker(marker.id)}
              />
            ))}

            {polylineCoords.length > 0 && (
              <Polyline coordinates={polylineCoords} strokeWidth={4} strokeColor="#4285F4" />
            )}
          </MapView>

          <Pressable style={styles.routeButton} onPress={generateRoute}>
            <Text style={styles.routeButtonText}>Rota Oluştur</Text>
          </Pressable>
        </>
      )}
    </View>
  );
};

// **Polyline Çözümleme**
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
  routeButton: { position: "absolute", bottom: 20, left: "50%", marginLeft: -75, backgroundColor: "#4285F4", padding: 10, borderRadius: 10 },
  routeButtonText: { color: "#fff", fontSize: 16, fontWeight: "bold" },
  loading: { flex: 1, justifyContent: "center", alignItems: "center" }
});

export default HomeScreen;
