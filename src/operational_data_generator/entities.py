"""Deterministic entity factories for the approved operational model."""

from __future__ import annotations

from datetime import datetime, timedelta
from random import Random
from typing import Any

from .config import RANDOM_SEED, TARGET_COUNTS, WEATHER_LOCATIONS

Row = dict[str, Any]


def _code(prefix: str, number: int, width: int = 3) -> str:
    return f"{prefix}-{number:0{width}d}"


def generate_regions() -> list[Row]:
    names = ("North Texas", "Central Texas", "Gulf Coast", "West Texas")
    return [{"region_id": i, "region_code": _code("REG", i), "region_name": name,
             "region_description": f"{name} operating region"}
            for i, name in enumerate(names, 1)]


def generate_offices(regions: list[Row]) -> list[Row]:
    cities = ("Dallas", "Fort Worth", "Plano", "Austin", "Round Rock", "Waco",
              "Houston", "Baytown", "Galveston", "Midland", "Odessa", "Abilene")
    return [{"office_id": i, "office_code": _code("OFF", i),
             "office_name": f"{city} Office", "region_id": regions[(i - 1) % len(regions)]["region_id"],
             "office_description": f"Field operations office in {city}"}
            for i, city in enumerate(cities, 1)]


def generate_employees(offices: list[Row]) -> list[Row]:
    roles = ("Crew Lead", "Project Manager", "Field Manager", "Technician", "Safety Coordinator")
    return [{"employee_id": i, "employee_number": _code("EMP", i, 4),
             "employee_name": f"Employee {i:04d}",
             "home_office_id": offices[(i - 1) % len(offices)]["office_id"],
             "employment_status": "Active", "termination_date": "",
             "employee_role_code": roles[(i - 1) % len(roles)].upper().replace(" ", "_")}
            for i in range(1, TARGET_COUNTS["employees"] + 1)]


def generate_activities() -> list[Row]:
    names = ("General Site Work", "Crane Operations", "Roofing", "Concrete Pour",
             "Excavation", "Electrical Installation", "Welding", "Scaffolding",
             "Material Handling", "Surveying", "Pipeline Work", "Roadwork",
             "Demolition", "Inspection", "Utility Installation", "Steel Erection",
             "Painting", "Landscaping", "Equipment Maintenance", "Safety Review")
    return [{"activity_id": i, "activity_code": _code("ACT", i), "activity_name": name,
             "activity_description": f"Controlled activity: {name}",
             "activity_category": "High Exposure" if i in (2, 3, 8, 16) else "Standard"}
            for i, name in enumerate(names, 1)]


def generate_equipment_types() -> list[Row]:
    names = ("Mobile Crane", "Generator", "Scaffolding", "Excavator", "Forklift",
             "Aerial Lift", "Welder", "Compressor", "Concrete Pump", "Light Tower")
    return [{"equipment_type_id": i, "equipment_type_code": _code("ET", i),
             "equipment_type_name": name, "equipment_type_description": f"{name} assets",
             "equipment_category": "High Exposure" if i in (1, 3, 6, 9) else "Standard"}
            for i, name in enumerate(names, 1)]


def generate_safety_thresholds(activities: list[Row], equipment_types: list[Row]) -> list[Row]:
    metrics = (("WIND_GUST_MPH", ">=", "mph", "35", "HIGH", "DELAY_WORK", False),
               ("HEAT_INDEX_F", ">=", "F", "105", "HIGH", "HEAT_PROTOCOL", False),
               ("PRECIPITATION_IN", ">=", "inch", "0.50", "HIGH", "SHELTER_EQUIPMENT", False),
               ("WEATHER_CODE", "IN", "wmo_code", "95|96|99", "CRITICAL", "SHUTDOWN", True))
    rows: list[Row] = []
    for i in range(1, TARGET_COUNTS["safety_thresholds"] + 1):
        metric, operator, unit, value, severity, action, override = metrics[(i - 1) % 4]
        rows.append({"threshold_id": i, "activity_id": activities[(i - 1) % len(activities)]["activity_id"],
                     "equipment_type_id": equipment_types[(i - 1) % len(equipment_types)]["equipment_type_id"] if i <= 20 else "",
                     "metric_code": metric, "comparison_operator": operator, "unit": unit,
                     "threshold_value_or_code_set": value,
                     "threshold_value": value if metric != "WEATHER_CODE" else "",
                     "weather_code_set": value if metric == "WEATHER_CODE" else "",
                     "severity": severity, "recommended_action_code": action,
                     "effective_start_date": "2026-01-01", "effective_end_date": "",
                     "is_active": True, "override_flag": override})
    return rows


def generate_projects(offices: list[Row], employees: list[Row]) -> list[Row]:
    rows = []
    for i in range(1, TARGET_COUNTS["projects"] + 1):
        office = offices[(i - 1) % len(offices)]
        office_employees = [e for e in employees if e["home_office_id"] == office["office_id"]]
        start = datetime(2026, 1, 1) + timedelta(days=(i * 3) % 180)
        rows.append({"project_id": i, "project_code": _code("PRJ", i),
                     "project_name": f"Field Project {i:03d}", "office_id": office["office_id"],
                     "project_manager_employee_id": office_employees[1 % len(office_employees)]["employee_id"],
                     "field_manager_employee_id": office_employees[2 % len(office_employees)]["employee_id"],
                     "status": "Active" if i % 8 else "Planned",
                     "project_start_date": start.date().isoformat(),
                     "project_end_date": (start + timedelta(days=150)).date().isoformat(),
                     "priority_code": ("High", "Medium", "Low")[(i - 1) % 3],
                     "project_description": f"Synthetic operational project {i:03d}",
                     "parent_project_code": ""})
    return rows


def generate_job_sites(projects: list[Row]) -> list[Row]:
    return [{"job_site_id": i, "job_site_code": _code("SITE", i),
             "job_site_name": f"Job Site {i:03d}",
             "project_id": projects[(i - 1) % len(projects)]["project_id"],
             "weather_location_code": WEATHER_LOCATIONS[(i - 1) % len(WEATHER_LOCATIONS)],
             "job_site_description": f"Operational work site {i:03d}"}
            for i in range(1, TARGET_COUNTS["job_sites"] + 1)]


def generate_crews(offices: list[Row], employees: list[Row]) -> list[Row]:
    rows = []
    for i in range(1, TARGET_COUNTS["crews"] + 1):
        office = offices[(i - 1) % len(offices)]
        lead = next(e for e in employees if e["home_office_id"] == office["office_id"] and e["employee_role_code"] == "CREW_LEAD")
        rows.append({"crew_id": i, "crew_code": _code("CREW", i), "home_office_id": office["office_id"],
                     "crew_lead_employee_id": lead["employee_id"], "crew_status": "Active",
                     "crew_description": f"Active field crew {i:03d}"})
    return rows


def generate_equipment(equipment_types: list[Row]) -> list[Row]:
    return [{"equipment_id": i, "equipment_code": _code("EQ", i),
             "equipment_type_id": equipment_types[(i - 1) % len(equipment_types)]["equipment_type_id"],
             "equipment_status": "Available" if i % 3 else "In Use",
             "serial_number": f"SN2026{i:05d}", "asset_tag": f"ASSET-{i:04d}",
             "equipment_description": f"Synthetic equipment asset {i:03d}"}
            for i in range(1, TARGET_COUNTS["equipment"] + 1)]


SCENARIOS = ("normal_operations", "moderate_weather", "high_wind_equipment",
             "extreme_heat", "heavy_precipitation", "lightning_override",
             "crew_reschedule", "equipment_relocation", "multiple_project_conflict")


def generate_field_schedules(projects: list[Row], sites: list[Row], crews: list[Row], activities: list[Row]) -> list[Row]:
    """Generate weighted schedules plus reserved conflict and lineage scenarios."""
    rng = Random(RANDOM_SEED)
    rows: list[Row] = []

    # Guarantee broad reference coverage, then use weighted selections. The weights
    # intentionally create high-, normal-, and light-utilization crew groups and a
    # realistic activity mix without sacrificing deterministic output.
    site_pool = sites.copy()
    rng.shuffle(site_pool)
    site_choices = site_pool + rng.choices(sites, weights=[4 if s["project_id"] <= 15 else 2 if s["project_id"] <= 50 else 1 for s in sites], k=121)
    crew_pool = crews.copy()
    rng.shuffle(crew_pool)
    crew_weights = [5 if c["crew_id"] <= 8 else 2 if c["crew_id"] <= 35 else 0.5 for c in crews]
    crew_choices = crew_pool + rng.choices(crews, weights=crew_weights, k=201)
    activity_pool = activities.copy()
    rng.shuffle(activity_pool)
    activity_weights = [12, 10, 9, 8, 8, 7, 7, 6, 6, 5, 5, 4, 4, 4, 3, 3, 2, 2, 2, 1]
    activity_choices = activity_pool + rng.choices(activities, weights=activity_weights, k=221)

    # 241 base occurrences leave nine existing IDs for five reschedule chains.
    for i in range(1, 242):
        site = site_choices[i - 1]
        start = datetime(2026, 2, 1, 7) + timedelta(days=(i - 1) % 300, hours=((i - 1) % 3) * 2)
        scenario = "normal_operations"
        if i == 6:
            scenario = "moderate_weather"
        elif i == 7:
            scenario = "high_wind_equipment"
        elif i == 8:
            scenario = "extreme_heat"
        elif i == 9:
            scenario = "heavy_precipitation"
        elif i == 22:
            scenario = "lightning_override"
        elif i == 23:
            scenario = "equipment_relocation"
        crew_id = crew_choices[i - 1]["crew_id"]
        activity_id = activity_choices[i - 1]["activity_id"]
        status = "Completed" if i % 5 == 0 else "Scheduled"
        hours, size = 8, 4 + rng.randrange(4)
        rows.append({"field_schedule_id": i, "project_id": site["project_id"], "job_site_id": site["job_site_id"],
                     "crew_id": crew_id, "activity_id": activity_id,
                     "scheduled_start_timestamp": start.isoformat(timespec="seconds"),
                     "scheduled_end_timestamp": (start + timedelta(hours=hours)).isoformat(timespec="seconds"),
                     "scheduled_date": start.date().isoformat(), "planned_crew_hours": hours,
                     "planned_crew_size": size, "planned_labor_hours": hours * size,
                     "status": status, "rescheduled_from_schedule_id": "", "scenario_id": scenario})

    # Five roots span distinct projects, sites, crews, activities, and dates.
    roots = ((1, 1, 1, 1, datetime(2026, 1, 5, 7)),
             (2, 2, 2, 2, datetime(2026, 1, 8, 7)),
             (3, 3, 3, 3, datetime(2026, 1, 11, 7)),
             (4, 4, 4, 4, datetime(2026, 1, 14, 7)),
             (5, 5, 5, 5, datetime(2026, 1, 17, 7)))
    for schedule_id, site_id, crew_id, activity_id, start in roots:
        site = sites[site_id - 1]
        rows[schedule_id - 1].update({"project_id": site["project_id"], "job_site_id": site_id,
                                      "crew_id": crew_id, "activity_id": activity_id,
                                      "scheduled_start_timestamp": start.isoformat(timespec="seconds"),
                                      "scheduled_end_timestamp": (start + timedelta(hours=8)).isoformat(timespec="seconds"),
                                      "scheduled_date": start.date().isoformat(), "status": "Rescheduled",
                                      "scenario_id": "crew_reschedule"})

    chain_successors = {1: (242,), 2: (243,), 3: (244, 245),
                        4: (246, 247), 5: (248, 249, 250)}
    successor_day = 0
    for root_id, successor_ids in chain_successors.items():
        predecessor = root_id
        for position, successor_id in enumerate(successor_ids):
            successor_day += 1
            base = rows[root_id - 1].copy()
            start = datetime(2026, 12, 1, 7) + timedelta(days=successor_day)
            base.update({"field_schedule_id": successor_id,
                         "scheduled_start_timestamp": start.isoformat(timespec="seconds"),
                         "scheduled_end_timestamp": (start + timedelta(hours=8)).isoformat(timespec="seconds"),
                         "scheduled_date": start.date().isoformat(),
                         "status": "Scheduled" if position == len(successor_ids) - 1 else "Rescheduled",
                         "rescheduled_from_schedule_id": predecessor,
                         "scenario_id": "crew_reschedule"})
            rows.append(base)
            predecessor = successor_id

    # Three cross-project overlaps and three exact back-to-back pairs. These use
    # multiple crews and sites and replace ordinary rows without changing count.
    conflicts = ((10, 11, 10, 10, 11, datetime(2026, 10, 5, 7), datetime(2026, 10, 5, 11)),
                 (12, 13, 11, 12, 13, datetime(2026, 10, 8, 7), datetime(2026, 10, 8, 11)),
                 (14, 15, 12, 14, 15, datetime(2026, 10, 11, 7), datetime(2026, 10, 11, 11)),
                 (16, 17, 13, 16, 17, datetime(2026, 10, 14, 7), datetime(2026, 10, 14, 15)),
                 (18, 19, 14, 18, 19, datetime(2026, 10, 17, 7), datetime(2026, 10, 17, 15)),
                 (20, 21, 15, 20, 21, datetime(2026, 10, 20, 7), datetime(2026, 10, 20, 15)))
    for first_id, second_id, crew_id, first_site_id, second_site_id, first_start, second_start in conflicts:
        for schedule_id, site_id, start in ((first_id, first_site_id, first_start), (second_id, second_site_id, second_start)):
            site = sites[site_id - 1]
            rows[schedule_id - 1].update({"project_id": site["project_id"], "job_site_id": site_id,
                                          "crew_id": crew_id,
                                          "scheduled_start_timestamp": start.isoformat(timespec="seconds"),
                                          "scheduled_end_timestamp": (start + timedelta(hours=8)).isoformat(timespec="seconds"),
                                          "scheduled_date": start.date().isoformat(), "status": "Scheduled",
                                          "scenario_id": "multiple_project_conflict"})

    # Scenario overrides can displace a reference's sole base occurrence. Repair
    # coverage deterministically using ordinary rows, without touching scenarios.
    normal_rows = [row for row in rows if row["scenario_id"] == "normal_operations"]
    used_site_ids = {row["job_site_id"] for row in rows}
    site_counts = {site_id: sum(row["job_site_id"] == site_id for row in rows) for site_id in used_site_ids}
    donor_rows = [row for row in normal_rows if site_counts[row["job_site_id"]] > 1]
    for row, missing_site in zip(donor_rows, [site for site in sites if site["job_site_id"] not in used_site_ids]):
        site_counts[row["job_site_id"]] -= 1
        row["job_site_id"] = missing_site["job_site_id"]
        row["project_id"] = missing_site["project_id"]
    used_crew_ids = {row["crew_id"] for row in rows}
    for row, missing_crew in zip(reversed(normal_rows), [crew for crew in crews if crew["crew_id"] not in used_crew_ids]):
        row["crew_id"] = missing_crew["crew_id"]
    rows.sort(key=lambda row: row["field_schedule_id"])
    return rows


def generate_equipment_assignments(equipment: list[Row], sites: list[Row]) -> list[Row]:
    """Generate deterministic nonsequential first-use and reassignment choices."""
    rng = Random(RANDOM_SEED + 1)
    rows = []
    first_sites = sites.copy()
    rng.shuffle(first_sites)
    first_sites = first_sites[:len(equipment)]
    second_sites: list[Row] = []
    shuffled_sites = sites.copy()
    rng.shuffle(shuffled_sites)
    cursor = 0
    for first_site in first_sites[:40]:
        while shuffled_sites[cursor % len(shuffled_sites)]["job_site_id"] == first_site["job_site_id"]:
            cursor += 1
        second_sites.append(shuffled_sites[cursor % len(shuffled_sites)])
        cursor += 1
    for i in range(1, TARGET_COUNTS["equipment_assignments"] + 1):
        if i <= len(equipment):
            asset = equipment[i - 1]
            site = first_sites[i - 1]
            start = datetime(2026, 2, 1, 6) + timedelta(days=i - 1)
        else:
            asset = equipment[i - len(equipment) - 1]
            site = second_sites[i - len(equipment) - 1]
            first_start = datetime.fromisoformat(rows[asset["equipment_id"] - 1]["assignment_start_timestamp"])
            start = first_start + timedelta(days=120 + rng.randrange(45))
        if i == 1:
            start = datetime(2026, 2, 7, 6)
        rows.append({"assignment_id": i, "equipment_id": asset["equipment_id"],
                     "job_site_id": site["job_site_id"], "project_id": site["project_id"],
                     "assignment_start_timestamp": start.isoformat(timespec="seconds"),
                     "assignment_end_timestamp": (start + timedelta(hours=10)).isoformat(timespec="seconds"),
                     "assignment_note": "High-risk relocation review" if i == 1 else "Planned assignment",
                     "scenario_id": "equipment_relocation" if i == 1 else "normal_operations"})
    return rows
