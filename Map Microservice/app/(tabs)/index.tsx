import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';

// API URL'si
const API_URL = "http://localhost:8000/get_routes"; // Backend API URL'nizi buraya yazın

// Rotalar için renkler
const routeColors = [
  "red", "blue", "green", "purple", "orange", "brown", "yellow", "pink", "cyan"
];

// Müşteri tipi
interface Customer {
  customer_name: string;
  demand: number;
  coordinates: {
    lat: number;
    lon: number;
  };
}

// Rota tipi
interface Route {
  customers: Customer[];
}

const MapScreen = () => {
  const [routes, setRoutes] = useState<Customer[][] | null>(null);  // routes verisi, birden fazla rota içerecek
  const [isLoading, setIsLoading] = useState(true);

  // Başlangıç noktası olan depo koordinatları
  const depotCoordinates = {
    latitude: 39.9336,
    longitude: 32.7056
  };

  // API'den veri çekme
  useEffect(() => {
    fetch(API_URL)
      .then((response) => response.json())
      .then((data) => {
        setRoutes(data.route_customers);  // API'den gelen veriyi setRoutes ile ayarlıyoruz
        setIsLoading(false);
      })
      .catch((error) => {
        console.error('Rotalar çekilirken hata oluştu:', error);
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0000ff" />
        <Text>Yükleniyor...</Text>
      </View>
    );
  }

  if (!routes) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Rota bulunamadı</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        provider="google"
        initialRegion={{
          latitude: depotCoordinates.latitude,
          longitude: depotCoordinates.longitude,
          latitudeDelta: 0.05,
          longitudeDelta: 0.05,
        }}
      >
        {/* Her bir rotayı render et */}
        {routes.map((route, index) => {
          const coordinates = route.map((customer) => ({
            latitude: customer.coordinates.lat,
            longitude: customer.coordinates.lon,
          }));

          return (
            <React.Fragment key={index}>
              {/* Rota için polyline, farklı renkler */}
              <Polyline
                coordinates={coordinates}
                strokeColor={routeColors[index % routeColors.length]} // Her rota için farklı renk
                strokeWidth={4}
              />

              {/* Müşteriler için marker (işaretçi) */}
              {route.map((customer, i) => (
                <Marker
                  key={i}
                  coordinate={{
                    latitude: customer.coordinates.lat,
                    longitude: customer.coordinates.lon,
                  }}
                  title={customer.customer_name}
                  description={`Talep: ${customer.demand}`}
                />
              ))}
            </React.Fragment>
          );
        })}
      </MapView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default MapScreen;
