import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
from database import get_db
from create_tables import Node, Route
from database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI()

OSRM_API_URL = "http://router.project-osrm.org/table/v1/driving"

class VehicleRoutingProblem:
    def __init__(self, nodes, depot, vehicle_capacity, num_vehicles):
        self.depot = depot
        self.nodes = [depot] + nodes
        self.vehicle_capacity = vehicle_capacity
        self.num_vehicles = num_vehicles
        self.distance_matrix = self.calculate_distance_matrix()
        self.demands = [node.get("demand", 0) for node in self.nodes]

    def calculate_distance_matrix(self):
        locations = ";".join([f"{node['yc']},{node['xc']}" for node in self.nodes])
        response = requests.get(f"{OSRM_API_URL}/{locations}?annotations=distance")

        if response.status_code != 200:
            raise Exception("OSRM API request failed!")

        data = response.json()
        matrix = np.array(data["distances"]) / 1000
        matrix = np.nan_to_num(matrix, nan=0.0)
        return matrix

def construct_solution(problem, pheromone_matrix, alpha, beta):
    n = len(problem.nodes)
    remaining_nodes = set(range(1, n))
    routes = []

    while remaining_nodes:
        route = [0]  # Her rotanın başlangıç noktası depo (index 0)
        capacity = 0
        current_node = 0

        while remaining_nodes:
            probabilities = []
            possible_nodes = []

            for next_node in remaining_nodes:
                distance = problem.distance_matrix[current_node][next_node]

                if capacity + problem.demands[next_node] <= problem.vehicle_capacity:
                    possible_nodes.append(next_node)
                    tau = pheromone_matrix[current_node][next_node] ** alpha
                    eta = (1 / max(distance, 1e-6)) ** beta
                    probabilities.append(tau * eta)

            if not possible_nodes:
                break

            probabilities = np.array(probabilities)
            probabilities /= np.sum(probabilities)
            next_node = np.random.choice(possible_nodes, p=probabilities)

            route.append(next_node)
            current_node = next_node
            capacity += problem.demands[next_node]
            remaining_nodes.remove(next_node)

        route.append(0)  # Her rotanın bitiş noktası depo (index 0)
        routes.append(route)

    return routes

def calculate_route_distances(problem, routes):
    return [sum(problem.distance_matrix[route[i]][route[i+1]] for i in range(len(route)-1)) for route in routes]

def get_route_customers(problem, routes):
    route_customers = []
    for route in routes:
        customer_info = []
        for node_idx in route:
            customer_info.append({
                "customer": problem.nodes[node_idx].get("customer", f"Node {node_idx}"),
                "coordinates": {"lat": problem.nodes[node_idx]["xc"], "lon": problem.nodes[node_idx]["yc"]},
                "demand": problem.nodes[node_idx].get("demand", 0)
            })
        route_customers.append(customer_info)
    return route_customers

def solve_aco(problem, alpha, beta, rho, iterations):
    np.random.seed(42)
    pheromone_matrix = np.ones(problem.distance_matrix.shape)
    best_distance = float('inf')
    best_routes = []

    for _ in range(iterations):
        routes = construct_solution(problem, pheromone_matrix, alpha, beta)
        route_distances = calculate_route_distances(problem, routes)
        distance = sum(route_distances)

        if distance < best_distance:
            best_distance = distance
            best_routes = routes

        pheromone_matrix *= (1 - rho)
        for route, route_distance in zip(routes, route_distances):
            pheromone_amount = 1 / (route_distance + 1e-6)
            for i in range(len(route)-1):
                pheromone_matrix[route[i]][route[i+1]] += pheromone_amount

    return best_routes, best_distance

@app.post("/optimize_routes")
async def optimize_routes(
    nodes_csv: UploadFile = File(...),
    vehicle_info_csv: UploadFile = File(...),
    alpha: float = 1.0,
    beta: float = 2.0,
    rho: float = 0.5,
    iterations: int = 100,
    db: Session = Depends(get_db)
):
    nodes_df = pd.read_csv(nodes_csv.file)
    nodes_df.columns = nodes_df.columns.str.lower()

    vehicle_info_df = pd.read_csv(vehicle_info_csv.file)
    vehicle_capacity = int(vehicle_info_df['fleet_capacity'][0])
    num_vehicles = int(vehicle_info_df['fleet_size'][0])

    depot = {
        "customer": "Depot",
        "xc": vehicle_info_df['fleet_start_x_coord'][0],
        "yc": vehicle_info_df['fleet_start_y_coord'][0],
        "demand": 0
    }

    customer_nodes = nodes_df.to_dict(orient="records")

    problem = VehicleRoutingProblem(
        nodes=customer_nodes,
        depot=depot,
        vehicle_capacity=vehicle_capacity,
        num_vehicles=num_vehicles
    )

    best_routes, best_distance = solve_aco(problem, alpha, beta, rho, iterations)
    route_distances = calculate_route_distances(problem, best_routes)
    route_customers = get_route_customers(problem, best_routes)

    db.query(Route).delete()
    db.commit()

    for route_id, route in enumerate(route_customers):
        for idx, customer in enumerate(route):
            node_distance = route_distances[route_id] if idx == len(route) - 1 else 0
            db.add(Route(
                route_id=route_id,
                customer=customer["customer"],
                latitude=customer["coordinates"]["lat"],
                longitude=customer["coordinates"]["lon"],
                demand=customer["demand"],
                distance=node_distance
            ))

    db.commit()

    return {
    "best_routes": [[int(node) for node in route] for route in best_routes],
    "best_distance": float(best_distance),
    "route_distances": [float(dist) for dist in route_distances],
    "route_customers": route_customers  
}

