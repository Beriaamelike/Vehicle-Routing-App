package com.example.mapboxmapapp

import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.example.mapboxmapapp.api.MarkerApi
import com.example.mapboxmapapp.models.Route
import com.example.mapboxmapapp.models.RoutesResponse
import com.mapbox.geojson.Point
import com.mapbox.maps.extension.compose.MapboxMap
import com.mapbox.maps.extension.compose.animation.viewport.rememberMapViewportState
import com.mapbox.maps.extension.compose.annotation.generated.PointAnnotation
import com.mapbox.maps.extension.compose.annotation.rememberIconImage
import retrofit2.*
import retrofit2.converter.gson.GsonConverterFactory

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val routeListState = mutableStateListOf<Route>()

        val retrofit = Retrofit.Builder()
            .baseUrl("http://10.0.2.2:8000/") // fiziksel cihazdaysan burayı IP ile değiştir
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        val api = retrofit.create(MarkerApi::class.java)

        api.getRoutes().enqueue(object : Callback<RoutesResponse> {
            override fun onResponse(call: Call<RoutesResponse>, response: Response<RoutesResponse>) {
                if (response.isSuccessful) {
                    val routes = response.body()?.routes ?: emptyList()
                    Log.d("API_RESPONSE", "Gelen route sayısı: ${routes.size}")
                    routes.forEach {
                        Log.d("API_RESPONSE", "Müşteri ${it.customer_id} → (${it.customer_lat}, ${it.customer_lon})")
                    }
                    routeListState.addAll(routes)
                } else {
                    Toast.makeText(applicationContext, "Veri alınamadı", Toast.LENGTH_SHORT).show()
                    Log.e("API_RESPONSE", "Yanıt başarısız: ${response.code()} ${response.message()}")
                }
            }

            override fun onFailure(call: Call<RoutesResponse>, t: Throwable) {
                Toast.makeText(applicationContext, "Hata: ${t.message}", Toast.LENGTH_SHORT).show()
                Log.e("API_RESPONSE", "Hata: ${t.message}")
            }
        })

        setContent {
            MapScreen(routeList = routeListState)
        }
    }
}

@Composable
fun MapScreen(routeList: List<Route>) {
    val mapViewportState = rememberMapViewportState {
        setCameraOptions {
            zoom(10.0)
            center(Point.fromLngLat(32.8597, 39.9334)) // Ankara
        }
    }

    val defaultMarkerIcon = rememberIconImage(resourceId = R.drawable.red_marker)
    val depotMarkerIcon = rememberIconImage(resourceId = R.drawable.blue_marker) // Yeni ikon

    LaunchedEffect(routeList) {
        Log.d("MAP_MARKERS", "Haritaya eklenecek marker sayısı: ${routeList.size}")
    }

    Column(modifier = Modifier.fillMaxSize()) {

        // Harita
        MapboxMap(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            mapViewportState = mapViewportState
        ) {
            routeList.forEach { route ->
                val point = Point.fromLngLat(route.customer_lon, route.customer_lat)
                val selectedIcon = if (route.customer_name == "Depot") depotMarkerIcon else defaultMarkerIcon

                PointAnnotation(point = point) {
                    iconImage = selectedIcon
                }
            }
        }

        // Alt kartlar
        LazyColumn(
            modifier = Modifier
                .weight(0.4f)
                .fillMaxWidth()
                .padding(horizontal = 8.dp)
        ) {
            if (routeList.isEmpty()) {
                item {
                    Text(
                        text = "Veri bekleniyor...",
                        modifier = Modifier.padding(16.dp)
                    )
                }
            } else {
                items(routeList) { route ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                    ) {
                        Text(
                            text = "${route.customer_name} → (${route.customer_lat}, ${route.customer_lon})",
                            color = Color.Black,
                            modifier = Modifier.padding(16.dp)
                        )
                    }
                }
            }
        }
    }
}
