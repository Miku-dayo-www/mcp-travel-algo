import math
import datetime
from typing import List, Dict, Any
# 【核心修复】：MCP 2.x 中直接导入 MCPServer
from mcp.server.mcpserver import MCPServer

# 初始化 MCPServer，MCP 2.x 默认即为 stdio 传输
mcp = MCPServer("TravelAlgorithmMCP")

CITY_POIS = {
    "南京": [
        {"id": "nj_01", "name": "南京博物院", "type": "indoor", "cost": 0.0, "lat": 32.0415, "lng": 118.8235,
         "duration_hr": 3.0, "score": 9.8},
        {"id": "nj_02", "name": "钟山风景区(中山陵)", "type": "outdoor", "cost": 70.0, "lat": 32.0612, "lng": 118.8541,
         "duration_hr": 3.5, "score": 9.6},
        {"id": "nj_03", "name": "总统府景区", "type": "indoor", "cost": 35.0, "lat": 32.0463, "lng": 118.7972,
         "duration_hr": 2.5, "score": 9.4},
        {"id": "nj_04", "name": "牛首山文化旅游区", "type": "outdoor", "cost": 160.0, "lat": 31.9165, "lng": 118.7452,
         "duration_hr": 3.5, "score": 9.5},
        {"id": "nj_05", "name": "大报恩寺遗址博物馆", "type": "indoor", "cost": 90.0, "lat": 32.0118, "lng": 118.7845,
         "duration_hr": 2.5, "score": 9.3},
        {"id": "nj_06", "name": "玄武湖公园", "type": "outdoor", "cost": 0.0, "lat": 32.0752, "lng": 118.7981,
         "duration_hr": 2.5, "score": 9.5},
        {"id": "nj_07", "name": "六朝博物馆", "type": "indoor", "cost": 30.0, "lat": 32.0442, "lng": 118.7995,
         "duration_hr": 2.0, "score": 9.2},
        {"id": "nj_08", "name": "金陵美术馆(老门东)", "type": "indoor", "cost": 0.0, "lat": 32.0140, "lng": 118.7892,
         "duration_hr": 2.0, "score": 9.0},
    ],
    "weather": [
        {"day": 1, "weather": "晴转多云 16~23℃", "is_rainy": False},
        {"day": 2, "weather": "中雨转大雨 12~16℃", "is_rainy": True},
        {"day": 3, "weather": "多云 15~21℃", "is_rainy": False},
    ]
}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


@mcp.tool()
def plan_optimal_route_tsp(city: str, days: int = 2, daily_hotel_budget: float = 200.0) -> Dict[str, Any]:
    pois = [p.copy() for p in CITY_POIS.get("南京", [])]
    weather_list = CITY_POIS["weather"]
    unvisited = sorted(pois, key=lambda x: x["score"], reverse=True)
    days_plan = []

    for d in range(1, days + 1):
        w_info = weather_list[(d - 1) % len(weather_list)]
        day_timeline = []
        curr_hour = 9.0

        if not unvisited:
            break

        curr_poi = unvisited.pop(0)
        day_pois = [curr_poi]

        while len(day_pois) < 2 and unvisited:
            nearest_poi = min(
                unvisited,
                key=lambda p: haversine_km(curr_poi["lat"], curr_poi["lng"], p["lat"], p["lng"])
            )
            unvisited.remove(nearest_poi)
            day_pois.append(nearest_poi)
            curr_poi = nearest_poi

        daily_cost = daily_hotel_budget + 100.0
        for idx, p in enumerate(day_pois):
            start_h = int(curr_hour)
            start_m = int((curr_hour - start_h) * 60)
            end_hour = curr_hour + p["duration_hr"]
            end_h = int(end_hour)
            end_m = int((end_hour - end_h) * 60)

            if idx + 1 < len(day_pois):
                nxt = day_pois[idx + 1]
                dist = haversine_km(p["lat"], p["lng"], nxt["lat"], nxt["lng"])
                commute_min = max(15, int((dist / 20.0) * 60))
                transport_str = f"相距 {dist} km，地铁/打车约 {commute_min} 分钟"
                curr_hour = end_hour + (commute_min / 60.0) + 1.0
            else:
                transport_str = "结束游览"
                curr_hour = end_hour

            daily_cost += p["cost"]
            day_timeline.append({
                "poi_id": p["id"],
                "name": p["name"],
                "type": p["type"],
                "start_time": f"{start_h:02d}:{start_m:02d}",
                "end_time": f"{end_h:02d}:{end_m:02d}",
                "ticket_cost": p["cost"],
                "transport": transport_str
            })

        days_plan.append({
            "day_index": d,
            "weather": w_info["weather"],
            "is_rainy": w_info["is_rainy"],
            "daily_total_cost": round(daily_cost, 1),
            "timeline": day_timeline
        })

    return {
        "city": city,
        "estimated_total_cost": sum(d["daily_total_cost"] for d in days_plan),
        "days": days_plan
    }


@mcp.tool()
def verify_hard_constraints(days_plan: List[Dict[str, Any]], max_budget: float, max_daily_hours: float = 8.0) -> Dict[
    str, Any]:
    violations = []
    total_cost = 0.0

    for day in days_plan:
        d_idx = day.get("day_index", 1)
        weather = day.get("weather", "")
        is_rainy = day.get("is_rainy", False) or ("雨" in weather)
        total_cost += float(day.get("daily_total_cost", 0.0))

        daily_hours = 0.0
        for item in day.get("timeline", []):
            if is_rainy and item.get("type") == "outdoor":
                violations.append(f"[天气冲突] 第{d_idx}天预报有雨，排布了户外景点【{item['name']}】，请替换。")
            try:
                t1 = datetime.datetime.strptime(item["start_time"], "%H:%M")
                t2 = datetime.datetime.strptime(item["end_time"], "%H:%M")
                daily_hours += (t2 - t1).seconds / 3600.0
            except:
                pass

        if daily_hours > max_daily_hours:
            violations.append(f"[超负荷] 第{d_idx}天耗时超 {max_daily_hours} 小时。")

    if total_cost > max_budget:
        violations.append(f"[超支] 方案花费 {total_cost} 超出预算上限 {max_budget}。")

    return {
        "constraint_passed": len(violations) == 0,
        "total_cost": round(total_cost, 1),
        "violations": violations
    }


@mcp.tool()
def dynamic_replan_local_search(current_poi_name: str, max_ticket_price: float = 50.0, require_indoor: bool = True) -> \
Dict[str, Any]:
    pois = CITY_POIS["南京"]
    origin = next((p for p in pois if p["name"] in current_poi_name or current_poi_name in p["name"]), pois[1])

    candidates = []
    for p in pois:
        if p["id"] == origin["id"] or (require_indoor and p["type"] != "indoor") or p["cost"] > max_ticket_price:
            continue
        dist = haversine_km(origin["lat"], origin["lng"], p["lat"], p["lng"])
        candidates.append({
            "replacement_poi": p["name"],
            "ticket_cost": p["cost"],
            "distance_km": dist,
            "score": p["score"] * 10 - dist * 2.5 - p["cost"] * 0.2
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return {"original": origin["name"], "best_replacement": candidates[0] if candidates else None}


def main():
    mcp.run()

if __name__ == "__main__":
    main()