package com.example.mapboxmapapp.models

data class RoutesResponse(
    val routes: List<Route>
)

data class Route(
    val id: Int,
    val customer_id: Int,
    val customer_name: String,
    val customer_lat: Double,
    val customer_lon: Double,
    val demand: Double
)

