package com.example.mapboxmapapp.api

import com.example.mapboxmapapp.models.RoutesResponse
import retrofit2.Call
import retrofit2.http.GET

interface MarkerApi {
    @GET("get_all_routes")  // API endpoint
    fun getRoutes(): Call<RoutesResponse>
}
