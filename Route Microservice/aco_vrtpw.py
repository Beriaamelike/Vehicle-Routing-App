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

# ✅ OSRM API URL
OSRM_API_URL = "http://router.project-osrm.org/table/v1/driving"

class VehicleRoutingProblem:
    def __init__(self, nodes, vehicle_capacity, num_vehicles):
        print("✅ VehicleRoutingProblem başlatıldı!")
        self.nodes = nodes
        self.vehicle_capacity = vehicle_capacity
        self.num_vehicles = num_vehicles
        self.distance_matrix = self.calculate_distance_matrix()
        self.demands = [node.get("demand", 0) for node in nodes]
        self.ready_times = [node.get("readytime", 0) for node in nodes]
        self.due_times = [node.get("duetime", float('inf')) for node in nodes]
        self.service_times = [node.get("servicetime", 0) for node in nodes]

    def calculate_distance_matrix(self):
        print("🔄 OSRM ile mesafe matrisi hesaplanıyor...")

        locations = ";".join([f"{node['yc']},{node['xc']}" for node in self.nodes])

        url = f"{OSRM_API_URL}/{locations}?annotations=distance"
        print(f"🌍 OSRM API URL: {url}")

        response = requests.get(url)

        try:
            data = response.json()
            print(f"✅ API Yanıtı: {data}")
        except requests.exceptions.JSONDecodeError:
            print("🚨 OSRM API Yanıtı Boş veya Hatalı!")
            raise Exception("OSRM API Yanıtı boş veya hatalı!")

        if "distances" not in data or not data["distances"]:
            raise Exception(f"🚨 OSRM API Hatası: {data}")

        matrix = np.array(data["distances"]) / 1000  
        matrix = np.nan_to_num(matrix, nan=0.0)

        print(f"✅ OSRM Mesafe Matrisi (KM):\n{matrix}")
        return matrix

def construct_solution(problem, pheromone_matrix, alpha, beta):
    n = len(problem.nodes)
    remaining_nodes = set(range(1, n))
    routes = []
    total_distance = 0  

    while remaining_nodes:
        route = [0]
        capacity = 0
        current_node = 0
        current_time = 0

        while remaining_nodes:
            probabilities = []
            possible_nodes = []

            for next_node in remaining_nodes:
                distance = problem.distance_matrix[current_node][next_node]

                arrival_time = current_time + distance

                if (capacity + problem.demands[next_node] <= problem.vehicle_capacity and
                    arrival_time <= problem.due_times[next_node]):
                    possible_nodes.append(next_node)
                    tau = pheromone_matrix[current_node][next_node] ** alpha
                    eta = (1 / max(distance, 1e-6)) ** beta
                    probabilities.append(tau * eta)

            if not possible_nodes:
                break  

            probabilities = np.array(probabilities)
            
            if np.isnan(probabilities).any() or np.sum(probabilities) == 0:
                probabilities = np.ones(len(possible_nodes)) / len(possible_nodes)

            probabilities /= np.sum(probabilities)
            next_node = np.random.choice(possible_nodes, p=probabilities)

            total_distance += problem.distance_matrix[current_node][next_node]

            route.append(next_node)
            current_node = next_node
            capacity += problem.demands[next_node]
            remaining_nodes.remove(next_node)

        total_distance += problem.distance_matrix[current_node][0]
        route.append(0)
        routes.append(route)

    return routes, total_distance

def calculate_route_distances(problem, routes):
    route_distances = []
    for route in routes:
        total_distance = 0
        for i in range(len(route) - 1):
            total_distance += problem.distance_matrix[route[i]][route[i+1]]
        route_distances.append(total_distance)
    return route_distances  

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
        routes, distance = construct_solution(problem, pheromone_matrix, alpha, beta)
        if distance < best_distance:
            best_distance = distance
            best_routes = routes

        pheromone_matrix *= (1 - rho)
        for route in routes:
            for i in range(len(route)-1):
                pheromone_matrix[route[i]][route[i+1]] += 1 / (distance + 1e-6)

    return best_routes, best_distance

@app.post("/optimize_routes")
async def optimize_routes(
    nodes_csv: UploadFile = File(...),
    vehicle_info_csv: UploadFile = File(...),
    alpha: float = 1.0,
    beta: float = 2.0,
    rho: float = 0.5,
    iterations: int = 100,
    db: Session = Depends(get_db)  # ✅ Veritabanı bağlantısı
):
    nodes_df = pd.read_csv(nodes_csv.file)
    nodes_df.columns = nodes_df.columns.str.lower()

    vehicle_info_df = pd.read_csv(vehicle_info_csv.file)
    vehicle_capacity = int(vehicle_info_df['fleet_capacity'][0])
    num_vehicles = int(vehicle_info_df['fleet_size'][0])

    # ✅ Yeni problem tanımı
    problem = VehicleRoutingProblem(
        nodes=nodes_df.to_dict(orient="records"),
        vehicle_capacity=vehicle_capacity,
        num_vehicles=num_vehicles
    )

    best_routes, best_distance = solve_aco(problem, alpha, beta, rho, iterations)
    route_distances = calculate_route_distances(problem, best_routes)
    route_customers = get_route_customers(problem, best_routes)

    # ✅ Eski rotaları temizle (opsiyonel)
    db.query(Route).delete()
    db.commit()

    # ✅ Yeni rotaları veritabanına ekle
    for route_id, route in enumerate(route_customers):
        total_distance = 0
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
       "route_distances": route_distances,
       "route_customers": route_customers  
    }


@app.post("/upload-csv")
async def upload_csv(nodes_csv: UploadFile = File(...), db: Session = Depends(get_db)):
    df = pd.read_csv(nodes_csv.file)
    df.columns = df.columns.str.lower()  

    for _, row in df.iterrows():
        node = Node(customer=row["customer"], xc=row["xc"], yc=row["yc"])
        db.add(node)

    db.commit()
    return {"message": "CSV verileri başarıyla MySQL veritabanına eklendi!"}

@app.get("/nodes")
def get_nodes(db: Session = Depends(get_db)):
    nodes = db.query(Node).all()
    return {"nodes": nodes}

@app.get("/routes")
def get_routes(db: Session = Depends(get_db)):
    routes = db.query(Route).all()
    return {"routes": routes}
