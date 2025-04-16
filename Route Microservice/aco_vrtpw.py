import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
from create_tables import Aco, Route, SessionLocal
from database import get_db
from database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI()

OSRM_API_URL = "http://router.project-osrm.org/table/v1/driving"

class VehicleRoutingProblem:
    def __init__(self, nodes, depot, vehicle_capacity, num_vehicles, cost_per_km, cost_per_time):
        self.depot = depot
        self.nodes = [depot] + nodes
        self.vehicle_capacity = vehicle_capacity
        self.num_vehicles = num_vehicles
        self.distance_matrix = self.calculate_distance_matrix()
        self.demands = [node.get("demand", 0) for node in self.nodes]
        self.cost_per_km = cost_per_km  # Araç başına km maliyeti
        self.cost_per_time = cost_per_time  # Araç başına zaman maliyeti

    def calculate_distance_matrix(self):
        locations = ";".join([f"{node['yc']},{node['xc']}" for node in self.nodes])
        response = requests.get(f"{OSRM_API_URL}/{locations}?annotations=distance")

        if response.status_code != 200:
            raise Exception("OSRM API request failed!")

        data = response.json()
        matrix = np.array(data["distances"]) / 1000  # Km cinsinden mesafeyi al
        matrix = np.nan_to_num(matrix, nan=0.0)
        return matrix

def calculate_cost(distance, time, cost_per_km, cost_per_time):
    """
    Bu fonksiyon, mesafeye ve zamana bağlı maliyet hesaplar.
    cost_per_km: Araç başına kilometre maliyeti
    cost_per_time: Araç başına zaman maliyeti
    """
    return (cost_per_km * distance) + (cost_per_time * time)

def construct_solution(problem, pheromone_matrix, alpha, beta):
    print("Çözüm yapılıyor...")
    n = len(problem.nodes)
    remaining_nodes = set(range(1, n))
    routes = []  # Bu, her aracın rotasını tutacak
    route_distances = []  # Her rota için mesafe
    route_times = []  # Her rota için zaman
    route_costs = []  # Her rota için maliyet

    while remaining_nodes:
        print(f"Remaining nodes: {len(remaining_nodes)}")
        route = [0]  # Her rotanın başlangıç noktası depo (index 0)
        capacity = 0
        current_node = 0
        route_distance = 0  # Rotadaki mesafeyi tutacak
        route_time = 0  # Rotadaki zamanı tutacak

        while remaining_nodes:
            probabilities = []
            possible_nodes = []

            for next_node in remaining_nodes:
                distance = problem.distance_matrix[current_node][next_node]

                # Kapasite kısıtlamasını geçici olarak kaldırdık
                possible_nodes.append(next_node)
                tau = pheromone_matrix[current_node][next_node] ** alpha
                eta = (1 / max(distance, 1e-6)) ** beta  # Mesafe ağırlıklı etki
                probabilities.append(tau * eta)

            if not possible_nodes:
                break

            probabilities = np.array(probabilities)
            probabilities /= np.sum(probabilities)
            next_node = np.random.choice(possible_nodes, p=probabilities)

            route.append(next_node)
            current_node = next_node
            route_distance += problem.distance_matrix[route[-2]][route[-1]]  # Mesafeyi ekle
            route_time += (problem.distance_matrix[route[-2]][route[-1]] / 40)  # Hızı 40 km/saat kabul ediyoruz
            remaining_nodes.remove(next_node)

        route.append(0)  # Her rotanın bitiş noktası depo (index 0)
        routes.append(route)  # Yeni rota eklenir
        route_distances.append(route_distance)
        route_times.append(route_time)

        route_cost = calculate_cost(route_distance, route_time, problem.cost_per_km, problem.cost_per_time)
        route_costs.append(route_cost)

    print("Çözüm tamamlandı.")
    return routes, route_distances, route_times, route_costs



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
    print("ACO algoritması başladı.")
    np.random.seed(42)
    pheromone_matrix = np.ones(problem.distance_matrix.shape)
    best_distance = float('inf')
    best_routes = []
    best_cost = float('inf')

    for iteration in range(iterations):
        print(f"Iterasyon: {iteration+1}/{iterations}")
        routes, route_distances, route_times, route_costs = construct_solution(
            problem, pheromone_matrix, alpha, beta
        )

        total_distance = sum(route_distances)
        total_cost = sum(route_costs)

        print(f"Toplam mesafe: {total_distance}, Toplam maliyet: {total_cost}")

        # Eğer toplam maliyet iyileşmişse, en iyi sonucu güncelle
        if total_cost < best_cost:
            best_cost = total_cost
            best_routes = routes

        # Pheromone güncelleme
        pheromone_matrix *= (1 - rho)
        for route, route_distance in zip(routes, route_distances):
            pheromone_amount = 1 / (route_distance + 1e-6)
            for i in range(len(route)-1):
                pheromone_matrix[route[i]][route[i+1]] += pheromone_amount

    print("ACO algoritması tamamlandı.")
    return best_routes, best_cost



@app.post("/optimize_routes")
async def optimize_routes(
    alpha: float = 1.0,
    beta: float = 2.0,
    rho: float = 0.5,
    iterations: int = 100,
    db: Session = Depends(get_db)
):
    print("Optimize routes API çağrıldı.")  # API'nin çağrıldığını görmek için
    routes = db.query(Route).all()
    
    # Eğer rotalar yoksa, API'den dönen mesajı kontrol edelim
    if not routes:
        print("Veritabanında rota bulunamadı.")
        return {"message": "No routes found in the database"}

    print(f"{len(routes)} rota bulundu.")  # Veritabanındaki rotaların sayısını yazdıralım
    
    # Depot bilgilerini al
    depot = {
        "customer": "Depot",
        "xc": routes[0].customer_lat,  # Depo koordinatları
        "yc": routes[0].customer_lon,
        "demand": 0
    }

    # Müşteri düğümleri verisini veritabanından al
    customer_nodes = []
    for route in routes:
        customer_nodes.append({
            "customer": route.customer_name,
            "xc": route.customer_lat,
            "yc": route.customer_lon,
            "demand": route.demand
        })

    print("Müşteri verileri alındı.")  # Verilerin başarıyla alındığını doğrulama
    
    # VehicleRoutingProblem nesnesi oluştur
    vehicle_capacity = 10  # Örnek kapasite
    num_vehicles = 3  # Araç sayısı
    cost_per_km = 0.5  # km başına maliyet
    cost_per_time = 10  # zaman başına maliyet

    problem = VehicleRoutingProblem(
        nodes=customer_nodes,
        depot=depot,
        vehicle_capacity=vehicle_capacity,
        num_vehicles=num_vehicles,
        cost_per_km=cost_per_km,
        cost_per_time=cost_per_time
    )

    # Ant Colony Optimization (ACO) ile çözümle
    best_routes, best_cost = solve_aco(problem, alpha, beta, rho, iterations)

    # Yeni optimize edilmiş rotaları 'Aco' tablosuna ekleyelim
    route_number = db.query(Aco.route_number).order_by(Aco.route_number.desc()).first()
    route_number = route_number[0] + 1 if route_number else 1  # Yeni rota numarasını al

    print("Optimize edilmiş rotalar hesaplandı.")  # Optimizasyon işlemi tamamlandı

    for route in best_routes:
        route_order = 1
        for node_idx in route:
            customer_info = problem.nodes[node_idx]
            aco_entry = Aco(
                route_number=route_number,
                route_order=route_order,
                customer_id=node_idx,
                customer_name=customer_info.get("customer", f"Node {node_idx}"),
                customer_lat=customer_info["xc"],
                customer_lon=customer_info["yc"],
                demand=customer_info.get("demand", 0)
            )
            db.add(aco_entry)
            route_order += 1  # Rotadaki her müşteri için sıralama artacak
        route_number += 1  # Yeni rota için numara artırılır
    db.commit()  # Veritabanına kaydetme işlemi

    print("Yeni rotalar veritabanına kaydedildi.")  # Kaydetme işlemi tamamlandı

    return {
        "best_routes": [[int(node) for node in route] for route in best_routes],
        "best_cost": float(best_cost),
    }


@app.get("/get_aco_routes")
async def get_aco_routes(db: Session = Depends(get_db)):
    # Veritabanındaki Aco tablosundaki rotaları çek
    aco_routes = db.query(Aco).all()

    route_data = []
    for route in aco_routes:
        route_data.append({
            "route_number": route.route_number,
            "route_order": route.route_order,
            "customer_id": route.customer_id,
            "customer_name": route.customer_name,
            "customer_lat": route.customer_lat,
            "customer_lon": route.customer_lon,
            "demand": route.demand
        })

    return {"aco_routes": route_data}


@app.get("/get_routes")
async def get_routes(db: Session = Depends(get_db)):
    # Veritabanından rotaları çek
    routes = db.query(Route).all()

    # Rotaları kullanıcı dostu formatta hazırlama
    route_data = {}
    for route in routes:
        route_number = route.route_number
        if route_number not in route_data:
            route_data[route_number] = []

        route_data[route_number].append({
            "route_number": route.route_number,
            "route_order": route.route_order,
            "customer_id": route.customer_id,
            "customer_name": route.customer_name,
            "coordinates": {"lat": route.customer_lat, "lon": route.customer_lon},
            "demand": route.demand
        })

    # Harita üzerinde kullanılabilir formata dönüştürme
    route_customers = []
    for route_number, customers in route_data.items():
        route_customers.append(customers)

    return {"route_customers": route_customers}



@app.post("/upload_csv_without_route")
async def upload_csv_without_route(
    nodes_csv: UploadFile = File(...),
    vehicle_info_csv: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # CSV dosyasını oku ve pandas DataFrame'e çevir
    nodes_df = pd.read_csv(nodes_csv.file)
    nodes_df.columns = nodes_df.columns.str.lower()  # Kolon isimlerini küçük harfe çevir

    vehicle_info_df = pd.read_csv(vehicle_info_csv.file)

    # Depot bilgilerini al
    depot = {
        "customer": "Depot",
        "xc": vehicle_info_df['fleet_start_x_coord'][0],
        "yc": vehicle_info_df['fleet_start_y_coord'][0],
        "demand": 0
    }

    # Müşteri düğümleri verisini CSV'den al
    customer_nodes = nodes_df.to_dict(orient="records")

    # Depoyu veritabanına kaydet
    route_entry = Route(
        customer_id=0,  # Depot'un müşteri ID'si yok
        customer_name="Depot",
        customer_lat=depot["xc"],
        customer_lon=depot["yc"],
        demand=depot["demand"]
    )
    db.add(route_entry)

    # Müşteri bilgilerini veritabanına kaydet
    for node_idx, customer_info in enumerate(customer_nodes, start=1):  # Başlangıçta depo ekledik
        route_entry = Route(
            customer_id=node_idx,
            customer_name=customer_info.get("customer", f"Node {node_idx}"),
            customer_lat=customer_info["xc"],
            customer_lon=customer_info["yc"],
            demand=customer_info.get("demand", 0)
        )
        db.add(route_entry)

    db.commit()  # Değişiklikleri veritabanına kaydet

    return {"message": "CSV verileri başarıyla veritabanına kaydedildi"}


@app.get("/get_all_routes")
async def get_all_routes(db: Session = Depends(get_db)):
    # Veritabanındaki tüm rotaları çek
    routes = db.query(Route).all()

    # Rotaları kullanıcı dostu formatta hazırlama
    route_data = []
    for route in routes:
        route_data.append({
            "id": route.id,
            "customer_id": route.customer_id,
            "customer_name": route.customer_name,
            "customer_lat": route.customer_lat,
            "customer_lon": route.customer_lon,
            "demand": route.demand
        })

    # Tüm rotaları döndür
    return {"routes": route_data} 